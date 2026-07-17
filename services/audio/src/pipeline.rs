//! Audio Pipeline Stages
//!
//! Implements the composable pipeline: chunk → synthesize → merge → normalize → encode

use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

use anyhow::{Context, Result};
use indicatif::{ProgressBar, ProgressStyle};
use tokio::sync::Semaphore;
use tracing::{debug, info, warn};

use crate::engine::{TTSEngine, TTSRequest, TTSResponse, create_engine, EngineConfig};
use crate::normalize::{normalize_ebu_r128, NormalizationConfig};

/// Pipeline configuration
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PipelineConfig {
    /// Text chunk size in characters
    pub chunk_size: usize,

    /// Overlap between chunks in characters
    pub chunk_overlap: usize,

    /// Language for text splitting
    pub language: String,

    /// Enable parallel synthesis
    pub parallel_synthesis: bool,

    /// Maximum concurrent synthesis tasks
    pub max_concurrent: usize,

    /// Skip chunks that already have audio (for resume)
    pub skip_existing: bool,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        Self {
            chunk_size: 500,
            chunk_overlap: 0,
            language: "spanish".to_string(),
            parallel_synthesis: true,
            max_concurrent: 4,
            skip_existing: true,
        }
    }
}

/// Pipeline stage trait
#[async_trait::async_trait]
pub trait PipelineStage: Send + Sync {
    fn name(&self) -> &str;

    async fn execute(&self, ctx: &mut PipelineContext) -> Result<()>;

    fn should_run(&self, ctx: &PipelineContext) -> bool {
        true
    }
}

/// Pipeline execution context
#[derive(Debug, Default)]
pub struct PipelineContext {
    pub input_text: String,
    pub text_chunks: Vec<TextChunk>,
    pub audio_chunks: Vec<AudioChunk>,
    pub merged_audio: Option<Vec<u8>>,
    pub normalized_audio: Option<Vec<u8>>,
    pub final_audio: Option<Vec<u8>>,
    pub output_path: Option<PathBuf>,
    pub config: PipelineConfig,
    pub engine_config: EngineConfig,
    pub normalization_config: NormalizationConfig,
    pub output_config: OutputConfig,
    pub progress: Option<ProgressBar>,
    pub stats: PipelineStats,
}

/// Text chunk with metadata
#[derive(Debug, Clone)]
pub struct TextChunk {
    pub index: usize,
    pub text: String,
    pub start_char: usize,
    pub end_char: usize,
}

/// Audio chunk with metadata
#[derive(Debug, Clone)]
pub struct AudioChunk {
    pub index: usize,
    pub data: Vec<u8>,
    pub format: String,
    pub sample_rate: u32,
    pub channels: u8,
    pub duration_ms: u64,
}

/// Output configuration
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct OutputConfig {
    pub format: String,
    pub sample_rate: u32,
    pub bitrate: String,
    pub channels: u8,
}

impl Default for OutputConfig {
    fn default() -> Self {
        Self {
            format: "m4a".to_string(),
            sample_rate: 24000,
            bitrate: "48k".to_string(),
            channels: 1,
        }
    }
}

/// Pipeline statistics
#[derive(Debug, Default, Clone, serde::Serialize)]
pub struct PipelineStats {
    pub chunk_count: usize,
    pub synthesis_time_ms: u64,
    pub merge_time_ms: u64,
    pub normalize_time_ms: u64,
    pub encode_time_ms: u64,
    pub total_time_ms: u64,
    pub total_chars: usize,
    pub total_audio_bytes: usize,
}

/// Main audio pipeline
pub struct AudioPipeline {
    stages: Vec<Box<dyn PipelineStage>>,
}

impl AudioPipeline {
    pub fn new() -> Self {
        Self {
            stages: vec![
                Box::new(ChunkStage),
                Box::new(SynthesizeStage),
                Box::new(MergeStage),
                Box::new(NormalizeStage),
                Box::new(EncodeStage),
            ],
        }
    }

    pub fn with_stages(stages: Vec<Box<dyn PipelineStage>>) -> Self {
        Self { stages }
    }

    pub async fn execute(&self, mut ctx: PipelineContext) -> Result<PipelineContext> {
        let total_start = Instant::now();

        // Setup progress bar
        if ctx.config.chunk_size > 0 && ctx.progress.is_none() {
            let pb = ProgressBar::new(ctx.stages_estimate() as u64);
            pb.set_style(
                ProgressStyle::default_bar()
                    .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} {msg}")
                    .unwrap()
                    .progress_chars("#>-"),
            );
            ctx.progress = Some(pb);
        }

        for stage in &self.stages {
            if stage.should_run(&ctx) {
                let stage_start = Instant::now();
                debug!("Running stage: {}", stage.name());

                if let Some(pb) = &ctx.progress {
                    pb.set_message(format!("Stage: {}", stage.name()));
                }

                stage.execute(&mut ctx).await
                    .with_context(|| format!("Stage '{}' failed", stage.name()))?;

                let elapsed = stage_start.elapsed().as_millis() as u64;
                match stage.name() {
                    "chunk" => ctx.stats.chunk_count = ctx.text_chunks.len(),
                    "synthesize" => ctx.stats.synthesis_time_ms = elapsed,
                    "merge" => ctx.stats.merge_time_ms = elapsed,
                    "normalize" => ctx.stats.normalize_time_ms = elapsed,
                    "encode" => ctx.stats.encode_time_ms = elapsed,
                    _ => {}
                }

                if let Some(pb) = &ctx.progress {
                    pb.inc(1);
                }
            }
        }

        ctx.stats.total_time_ms = total_start.elapsed().as_millis() as u64;
        ctx.stats.total_chars = ctx.input_text.len();
        ctx.stats.total_audio_bytes = ctx.final_audio.as_ref().map(|a| a.len()).unwrap_or(0);

        if let Some(pb) = &ctx.progress {
            pb.finish_with_message("Pipeline complete");
        }

        info!("Pipeline completed in {}ms", ctx.stats.total_time_ms);
        info!("Stats: {:?}", ctx.stats);

        Ok(ctx)
    }
}

impl PipelineContext {
    fn stages_estimate(&self) -> usize {
        5 // chunk + synthesize + merge + normalize + encode
    }
}

/// Stage 1: Chunk text into synthesis units
pub struct ChunkStage;

#[async_trait::async_trait]
impl PipelineStage for ChunkStage {
    fn name(&self) -> &str {
        "chunk"
    }

    async fn execute(&self, ctx: &mut PipelineContext) -> Result<()> {
        info!("Chunking text ({} chars, chunk_size={})", ctx.input_text.len(), ctx.config.chunk_size);

        let chunks = chunk_text(
            &ctx.input_text,
            ctx.config.chunk_size,
            ctx.config.chunk_overlap,
        );

        info!("Created {} text chunks", chunks.len());
        ctx.text_chunks = chunks;

        Ok(())
    }
}

/// Stage 2: Synthesize each text chunk to audio
pub struct SynthesizeStage;

#[async_trait::async_trait]
impl PipelineStage for SynthesizeStage {
    fn name(&self) -> &str {
        "synthesize"
    }

    async fn execute(&self, ctx: &mut PipelineContext) -> Result<()> {
        let engine = Arc::new(create_engine(&ctx.engine_config)
            .context("Failed to create TTS engine")?);

        if !engine.is_available() {
            anyhow::bail!("TTS engine '{}' is not available", engine.engine_id());
        }

        info!("Synthesizing {} chunks with {}", ctx.text_chunks.len(), engine.engine_name());

        // Check for existing chunks if skip_existing
        let mut to_synthesize = ctx.text_chunks.clone();
        if ctx.config.skip_existing && ctx.output_path.is_some() {
            // TODO: Check for existing chunk files
        }

        let semaphore = Arc::new(Semaphore::new(ctx.config.max_concurrent));
        let mut handles = Vec::new();

        if ctx.config.parallel_synthesis && ctx.text_chunks.len() > 1 {
            // Parallel synthesis
            for chunk in to_synthesize {
                let permit = semaphore.clone().acquire_owned().await?;
                let engine = engine.clone();
                let voice = ctx.engine_config.voice.clone();
                let sample_rate = ctx.output_config.sample_rate;
                let format = ctx.output_config.format.clone();

                let handle = tokio::spawn(async move {
                    let _permit = permit;
                    let request = TTSRequest {
                        text: chunk.text.clone(),
                        voice: voice.clone(),
                        sample_rate: Some(sample_rate),
                        speed: None,
                        pitch: None,
                        format: Some(format.clone()),
                        options: std::collections::HashMap::new(),
                    };

                    engine.synthesize(request).await
                        .map(|resp| AudioChunk {
                            index: chunk.index,
                            data: resp.audio_data,
                            format: resp.format,
                            sample_rate: resp.sample_rate,
                            channels: resp.channels,
                            duration_ms: resp.duration_ms,
                        })
                });
                handles.push(handle);
            }

            // Collect results in order
            let mut results = Vec::with_capacity(handles.len());
            for handle in handles {
                let chunk = handle.await??;
                results.push(chunk);
            }

            results.sort_by_key(|c| c.index);
            ctx.audio_chunks = results;
        } else {
            // Sequential synthesis
            let mut audio_chunks = Vec::with_capacity(to_synthesize.len());
            for chunk in to_synthesize {
                let request = TTSRequest {
                    text: chunk.text.clone(),
                    voice: ctx.engine_config.voice.clone(),
                    sample_rate: Some(ctx.output_config.sample_rate),
                    speed: None,
                    pitch: None,
                    format: Some(ctx.output_config.format.clone()),
                    options: std::collections::HashMap::new(),
                };

                let resp = engine.synthesize(request).await?;
                audio_chunks.push(AudioChunk {
                    index: chunk.index,
                    data: resp.audio_data,
                    format: resp.format,
                    sample_rate: resp.sample_rate,
                    channels: resp.channels,
                    duration_ms: resp.duration_ms,
                });
            }
            ctx.audio_chunks = audio_chunks;
        }

        info!("Synthesized {} audio chunks", ctx.audio_chunks.len());
        Ok(())
    }
}

/// Stage 3: Merge audio chunks into single file
pub struct MergeStage;

#[async_trait::async_trait]
impl PipelineStage for MergeStage {
    fn name(&self) -> &str {
        "merge"
    }

    fn should_run(&self, ctx: &PipelineContext) -> bool {
        !ctx.audio_chunks.is_empty()
    }

    async fn execute(&self, ctx: &mut PipelineContext) -> Result<()> {
        if ctx.audio_chunks.is_empty() {
            anyhow::bail!("No audio chunks to merge");
        }

        if ctx.audio_chunks.len() == 1 {
            ctx.merged_audio = Some(ctx.audio_chunks[0].data.clone());
            return Ok(());
        }

        info!("Merging {} audio chunks", ctx.audio_chunks.len());

        // Use ffmpeg to concatenate
        let merged = merge_audio_chunks(&ctx.audio_chunks, &ctx.output_config).await?;
        ctx.merged_audio = Some(merged);

        Ok(())
    }
}

/// Stage 4: EBU R128 loudness normalization
pub struct NormalizeStage;

#[async_trait::async_trait]
impl PipelineStage for NormalizeStage {
    fn name(&self) -> &str {
        "normalize"
    }

    fn should_run(&self, ctx: &PipelineContext) -> bool {
        ctx.normalization_config.enabled && ctx.merged_audio.is_some()
    }

    async fn execute(&self, ctx: &mut PipelineContext) -> Result<()> {
        let audio = ctx.merged_audio.as_ref().unwrap();
        info!("Normalizing audio (EBU R128, target: {} LUFS)", ctx.normalization_config.target_loudness);

        let normalized = normalize_ebu_r128(audio, &ctx.normalization_config).await?;
        ctx.normalized_audio = Some(normalized);

        Ok(())
    }
}

/// Stage 5: Encode to final output format
pub struct EncodeStage;

#[async_trait::async_trait]
impl PipelineStage for EncodeStage {
    fn name(&self) -> &str {
        "encode"
    }

    async fn execute(&self, ctx: &mut PipelineContext) -> Result<()> {
        let audio = ctx.normalized_audio
            .as_ref()
            .or(ctx.merged_audio.as_ref())
            .context("No audio to encode")?;

        info!("Encoding to {} ({}Hz, {})", ctx.output_config.format, ctx.output_config.sample_rate, ctx.output_config.bitrate);

        let encoded = encode_audio(audio, &ctx.output_config).await?;
        ctx.final_audio = Some(encoded);

        // Write to output file if specified
        if let Some(path) = &ctx.output_path {
            tokio::fs::write(path, ctx.final_audio.as_ref().unwrap()).await
                .context("Failed to write output file")?;
            info!("Audio saved to: {:?}", path);
        }

        Ok(())
    }
}

/// Chunk text into synthesis units
fn chunk_text(text: &str, chunk_size: usize, overlap: usize) -> Vec<TextChunk> {
    // Convert to chars for proper Unicode handling
    let chars: Vec<char> = text.chars().collect();
    if chars.len() <= chunk_size {
        return vec![TextChunk {
            index: 0,
            text: text.to_string(),
            start_char: 0,
            end_char: text.len(),
        }];
    }

    let mut chunks = Vec::new();
    let mut start = 0;
    let mut index = 0;

    while start < chars.len() {
        let end = std::cmp::min(start + chunk_size, chars.len());

        // Try to break at sentence boundary
        let mut chunk_end = end;
        if end < chars.len() {
            // Look for sentence endings within search range
            let search_end = std::cmp::min(end + 100, chars.len());
            let search_slice: String = chars[start..search_end].iter().collect();
            if let Some(pos) = search_slice.rfind(|c| ".!?".contains(c)) {
                chunk_end = start + pos + 1;
            }
        }

        // Convert char slice back to string
        let chunk_text: String = chars[start..chunk_end].iter().collect();
        let trimmed = chunk_text.trim();
        if !trimmed.is_empty() {
            // Calculate byte offsets for metadata
            let start_byte = text.char_indices().nth(start).map(|(i, _)| i).unwrap_or(0);
            let end_byte = if chunk_end < chars.len() {
                text.char_indices().nth(chunk_end).map(|(i, _)| i).unwrap_or(text.len())
            } else {
                text.len()
            };

            chunks.push(TextChunk {
                index,
                text: trimmed.to_string(),
                start_char: start_byte,
                end_char: end_byte,
            });
            index += 1;
        }

        start = chunk_end.saturating_sub(overlap);
    }

    chunks
}

/// Merge audio chunks using ffmpeg
async fn merge_audio_chunks(chunks: &[AudioChunk], output_config: &OutputConfig) -> Result<Vec<u8>> {
    use std::io::Write;
    use tempfile::NamedTempFile;

    // Create temp files for each chunk
    let mut chunk_files = Vec::new();
    for chunk in chunks {
        let mut file = NamedTempFile::with_suffix(&format!(".{}", chunk.format))?;
        file.write_all(&chunk.data)?;
        file.flush()?;
        chunk_files.push(file);
    }

    // Create file list for ffmpeg concat
    let mut list_file = NamedTempFile::with_suffix(".txt")?;
    for f in &chunk_files {
        writeln!(list_file, "file '{}'", f.path().display())?;
    }
    list_file.flush()?;

    // Output file
    let output_file = NamedTempFile::with_suffix(&format!(".{}", output_config.format))?;

    // Build ffmpeg command
    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.arg("-y")
        .arg("-f").arg("concat")
        .arg("-safe").arg("0")
        .arg("-i").arg(list_file.path())
        .arg("-c:a").arg(match output_config.format.as_str() {
            "m4a" | "aac" => "aac",
            "mp3" => "libmp3lame",
            "ogg" => "libvorbis",
            "flac" => "flac",
            "wav" => "pcm_s16le",
            _ => "aac",
        })
        .arg("-b:a").arg(&output_config.bitrate)
        .arg("-ar").arg(output_config.sample_rate.to_string())
        .arg("-ac").arg(output_config.channels.to_string())
        .arg(output_file.path());

    let output = cmd.output().await.context("ffmpeg merge failed")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg merge failed: {}", stderr);
    }

    let merged = tokio::fs::read(output_file.path()).await?;
    Ok(merged)
}

/// Encode audio to final format
async fn encode_audio(data: &[u8], output_config: &OutputConfig) -> Result<Vec<u8>> {
    use std::io::Write;
    use tempfile::NamedTempFile;

    // Input file
    let mut input_file = NamedTempFile::with_suffix(".wav")?;
    input_file.write_all(data)?;
    input_file.flush()?;

    // Output file
    let output_file = NamedTempFile::with_suffix(&format!(".{}", output_config.format))?;

    let mut cmd = tokio::process::Command::new("ffmpeg");
    cmd.arg("-y")
        .arg("-i").arg(input_file.path())
        .arg("-c:a").arg(match output_config.format.as_str() {
            "m4a" | "aac" => "aac",
            "mp3" => "libmp3lame",
            "ogg" => "libvorbis",
            "flac" => "flac",
            "wav" => "pcm_s16le",
            _ => "aac",
        })
        .arg("-b:a").arg(&output_config.bitrate)
        .arg("-ar").arg(output_config.sample_rate.to_string())
        .arg("-ac").arg(output_config.channels.to_string())
        .arg(output_file.path());

    let output = cmd.output().await.context("ffmpeg encode failed")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg encode failed: {}", stderr);
    }

    let encoded = tokio::fs::read(output_file.path()).await?;
    Ok(encoded)
}
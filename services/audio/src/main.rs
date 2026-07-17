//! Audio Generation Service for PDFTranslator
//!
//! This crate provides a Rust-based TTS pipeline with pluggable engines and
//! stages: chunk → synthesize → merge → normalize (EBU R128) → encode.
//!
//! CUPID Principles:
//! - Composable: TTSEngine trait allows pluggable backends
//! - Unix Philosophy: Stdin/stdout pipeline, each stage does one thing
//! - Predictable: Deterministic EBU R128 normalization, explicit error types
//! - Idiomatic: Rust traits, async/await, proper error handling
//! - Domain-Focused: Models audiobook generation workflow

use std::collections::HashMap;
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use indicatif::{ProgressBar, ProgressStyle};
use serde::{Deserialize, Serialize};
use tokio::fs;
use tracing::{debug, info, warn};

mod engine;
mod pipeline;
mod normalize;

pub use engine::{TTSEngine, MacOSSayEngine, TTSRequest, TTSResponse, EngineConfig, create_engine};
pub use pipeline::{AudioPipeline, PipelineConfig, PipelineStage, PipelineContext, OutputConfig};
pub use normalize::{normalize_ebu_r128, NormalizationConfig};

/// Main CLI entry point
#[derive(Parser)]
#[command(
    name = "pdftranslator-audio",
    version,
    about = "Audio generation service with pluggable TTS engines",
    long_about = "Generates audiobooks from text using a composable pipeline:
  chunk → synthesize → merge → normalize (EBU R128) → encode

Supports multiple TTS backends via the TTSEngine trait.
Standard input/output for Unix pipeline composition."
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Voice to use (engine-specific)
    #[arg(short, long, default_value = "Samantha")]
    voice: String,

    /// Output format
    #[arg(short, long, default_value = "m4a", value_parser = ["m4a", "mp3", "wav", "ogg", "flac"])]
    format: String,

    /// Sample rate in Hz
    #[arg(short, long, default_value = "24000")]
    sample_rate: u32,

    /// Audio bitrate (e.g., 48k, 64k, 128k)
    #[arg(short, long, default_value = "48k")]
    bitrate: String,

    /// Enable EBU R128 loudness normalization
    #[arg(long, default_value = "true")]
    normalize: bool,

    /// Target loudness in LUFS (EBU R128 default: -16)
    #[arg(long, default_value = "-16.0")]
    target_loudness: f32,

    /// Suppress progress output
    #[arg(short, long)]
    quiet: bool,

    /// Configuration file path
    #[arg(short, long)]
    config: Option<PathBuf>,
}

#[derive(Subcommand)]
enum Commands {
    /// Generate audio from text (reads from stdin, writes to stdout)
    Generate {
        /// Input text file (default: stdin)
        #[arg(short, long)]
        input: Option<PathBuf>,

        /// Output audio file (default: stdout)
        #[arg(short, long)]
        output: Option<PathBuf>,

        /// Engine to use
        #[arg(short, long, default_value = "macos-say", value_parser = ["macos-say", "piper", "coqui"])]
        engine: String,

        /// Text content directly (alternative to stdin/file)
        #[arg(long)]
        text: Option<String>,
    },

    /// List available voices for the selected engine
    Voices {
        /// Engine to query
        #[arg(short, long, default_value = "macos-say")]
        engine: String,
    },

    /// Show engine information
    Info {
        /// Engine to inspect
        #[arg(short, long, default_value = "macos-say")]
        engine: String,
    },

    /// Validate audio pipeline configuration
    Validate {
        #[arg(short, long)]
        config: PathBuf,
    },
}

/// Configuration for the audio service
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AudioConfig {
    engine: EngineConfig,
    pipeline: PipelineConfig,
    normalization: NormalizationConfig,
    output: OutputConfig,
}

impl Default for AudioConfig {
    fn default() -> Self {
        Self {
            engine: EngineConfig {
                engine_type: "macos-say".to_string(),
                voice: "Samantha".to_string(),
                options: HashMap::new(),
            },
            pipeline: PipelineConfig {
                chunk_size: 500,
                chunk_overlap: 0,
                language: "spanish".to_string(),
                parallel_synthesis: true,
                max_concurrent: 4,
                skip_existing: true,
            },
            normalization: NormalizationConfig {
                enabled: true,
                target_loudness: -16.0,
                true_peak: -1.5,
                loudness_range: 11.0,
                fast_mode: false,
            },
            output: OutputConfig {
                format: "m4a".to_string(),
                sample_rate: 24000,
                bitrate: "48k".to_string(),
                channels: 1,
            },
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize tracing
    let filter = if cli.quiet {
        "warn"
    } else {
        "info"
    };
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .init();

    // Load config if provided
    let mut config = if let Some(config_path) = &cli.config {
        load_config(config_path).await?
    } else {
        AudioConfig::default()
    };

    // Override config with CLI args
    config.engine.voice = cli.voice;
    config.output.format = cli.format;
    config.output.sample_rate = cli.sample_rate;
    config.output.bitrate = cli.bitrate;
    config.normalization.enabled = cli.normalize;
    config.normalization.target_loudness = cli.target_loudness;

    match cli.command {
        Commands::Generate {
            input,
            output,
            engine,
            text,
        } => {
            let engine_impl = create_engine(&config.engine)?;
            let pipeline = AudioPipeline::new();

            let text_content = if let Some(text) = text {
                text
            } else if let Some(input_path) = input {
                tokio::fs::read_to_string(input_path).await?
            } else {
                // Read from stdin
                let mut buffer = String::new();
                io::stdin().read_to_string(&mut buffer)?;
                buffer
            };

            if text_content.trim().is_empty() {
                anyhow::bail!("No input text provided");
            }

            let progress = if !cli.quiet {
                Some(create_progress_bar())
            } else {
                None
            };

            // Build pipeline context
            let mut ctx = PipelineContext {
                input_text: text_content,
                config: config.pipeline,
                engine_config: config.engine,
                normalization_config: config.normalization,
                output_config: config.output,
                progress,
                output_path: output.clone(),
                ..Default::default()
            };

            let ctx = pipeline.execute(ctx).await?;

            // Write output
            if let Some(output_path) = output {
                if let Some(audio) = ctx.final_audio {
                    tokio::fs::write(output_path, audio).await?;
                    info!("Audio written to file");
                }
            } else {
                // Write to stdout for piping
                if let Some(audio) = ctx.final_audio {
                    io::stdout().write_all(&audio)?;
                }
            }
        }
        Commands::Voices { engine } => {
            let engine_impl = create_engine(&config.engine)?;
            let voices = engine_impl.list_voices().await?;
            for voice in voices {
                println!("{}", voice.id);
            }
        }
        Commands::Info { engine } => {
            let engine_impl = create_engine(&config.engine)?;
            println!("Engine: {}", engine_impl.engine_id());
            println!("Name: {}", engine_impl.engine_name());
            println!("Available: {}", engine_impl.is_available());
        }
        Commands::Validate { config: config_path } => {
            let config = load_config(&config_path).await?;
            validate_config(&config)?;
            println!("Configuration is valid");
        }
    }

    Ok(())
}

fn create_progress_bar() -> ProgressBar {
    let pb = ProgressBar::new_spinner();
    pb.set_style(
        ProgressStyle::default_spinner()
            .template("{spinner:.green} {msg}")
            .unwrap(),
    );
    pb
}

async fn load_config(path: &Path) -> Result<AudioConfig> {
    let content = tokio::fs::read_to_string(path).await?;
    let config: AudioConfig = serde_json::from_str(&content)?;
    Ok(config)
}

fn validate_config(config: &AudioConfig) -> Result<()> {
    if config.pipeline.chunk_size == 0 {
        anyhow::bail!("chunk_size must be > 0");
    }
    if config.output.sample_rate == 0 {
        anyhow::bail!("sample_rate must be > 0");
    }
    if config.pipeline.max_concurrent == 0 {
        anyhow::bail!("max_concurrent must be > 0");
    }
    Ok(())
}
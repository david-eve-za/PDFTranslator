//! TTS Engine implementations

use std::collections::HashMap;
use anyhow::{Context, Result};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::process::Command;
use tracing::{debug, info, warn};
use uuid;

/// TTS Engine trait for pluggable backends
#[async_trait]
pub trait TTSEngine: Send + Sync {
    /// Get engine identifier
    fn engine_id(&self) -> &str;

    /// Get engine display name
    fn engine_name(&self) -> &str;

    /// List available voices
    async fn list_voices(&self) -> Result<Vec<VoiceInfo>>;

    /// Synthesize speech from text
    async fn synthesize(&self, request: TTSRequest) -> Result<TTSResponse>;

    /// Get engine configuration
    fn config(&self) -> EngineConfig;

    /// Check if engine is available on this system
    fn is_available(&self) -> bool;
}

/// Voice information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceInfo {
    pub id: String,
    pub name: String,
    pub language: String,
    pub gender: Option<String>,
    pub quality: Option<String>, // "standard", "premium", "neural"
    pub sample_rate: Option<u32>,
}

/// TTS Request
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TTSRequest {
    pub text: String,
    pub voice: String,
    pub sample_rate: Option<u32>,
    pub speed: Option<f32>,
    pub pitch: Option<f32>,
    pub format: Option<String>,
    pub options: HashMap<String, serde_json::Value>,
}

/// TTS Response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TTSResponse {
    pub audio_data: Vec<u8>,
    pub format: String,
    pub sample_rate: u32,
    pub channels: u8,
    pub duration_ms: u64,
    pub voice_used: String,
}

/// Engine configuration
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct EngineConfig {
    pub engine_type: String,
    pub voice: String,
    pub options: HashMap<String, serde_json::Value>,
}

/// macOS `say` command TTS Engine
pub struct MacOSSayEngine {
    voice: String,
    config: EngineConfig,
}

impl MacOSSayEngine {
    pub fn new(voice: String) -> Result<Self> {
        // Verify `say` is available
        if !Self::is_available_static() {
            anyhow::bail!("macOS 'say' command not found");
        }

        let config = EngineConfig {
            engine_type: "macos-say".to_string(),
            voice: voice.clone(),
            options: HashMap::new(),
        };

        Ok(Self { voice, config })
    }

    fn is_available_static() -> bool {
        Command::new("which")
            .arg("say")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    fn get_voice_info(&self, voice_name: &str) -> VoiceInfo {
        VoiceInfo {
            id: voice_name.to_string(),
            name: voice_name.to_string(),
            language: self.detect_language(voice_name),
            gender: None,
            quality: Some("system".to_string()),
            sample_rate: Some(22050),
        }
    }

    fn detect_language(&self, voice: &str) -> String {
        // macOS voice naming conventions
        let voice_lower = voice.to_lowercase();

        // Spanish voices
        if voice_lower.contains("paulina") || voice_lower.contains("monica") ||
           voice_lower.contains("jorge") || voice_lower.contains("diego") {
            return "es-ES".to_string();
        }
        // Mexican Spanish
        if voice_lower.contains("juan") || voice_lower.contains("maria") {
            return "es-MX".to_string();
        }
        // English voices
        if voice_lower.contains("samantha") || voice_lower.contains("alex") ||
           voice_lower.contains("victoria") || voice_lower.contains("fred") ||
           voice_lower.contains("susan") || voice_lower.contains("karen") {
            return "en-US".to_string();
        }
        // British English
        if voice_lower.contains("daniel") || voice_lower.contains("emily") {
            return "en-GB".to_string();
        }
        // French
        if voice_lower.contains("thomas") || voice_lower.contains("amélie") ||
           voice_lower.contains("audrey") {
            return "fr-FR".to_string();
        }
        // German
        if voice_lower.contains("anna") || voice_lower.contains("markus") ||
           voice_lower.contains("petr a") {
            return "de-DE".to_string();
        }
        // Italian
        if voice_lower.contains("alice") || voice_lower.contains("luca") {
            return "it-IT".to_string();
        }
        // Japanese
        if voice_lower.contains("kyoko") || voice_lower.contains("otoya") {
            return "ja-JP".to_string();
        }
        // Chinese
        if voice_lower.contains("ting-ting") || voice_lower.contains("sin-ji") {
            return "zh-CN".to_string();
        }
        // Korean
        if voice_lower.contains("yuna") {
            return "ko-KR".to_string();
        }

        "en-US".to_string()
    }
}

#[async_trait]
impl TTSEngine for MacOSSayEngine {
    fn engine_id(&self) -> &str {
        "macos-say"
    }

    fn engine_name(&self) -> &str {
        "macOS say"
    }

    async fn list_voices(&self) -> Result<Vec<VoiceInfo>> {
        let output = Command::new("say")
            .arg("-v")
            .arg("?")
            .output()
            .context("Failed to execute 'say -v ?'")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("'say -v ?' failed: {}", stderr);
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let mut voices = Vec::new();

        for line in stdout.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            // Format: "VoiceName    language    # description"
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.is_empty() {
                continue;
            }
            let voice_name = parts[0];
            let language = parts.get(1).unwrap_or(&"en-US").to_string();

            voices.push(VoiceInfo {
                id: voice_name.to_string(),
                name: voice_name.to_string(),
                language,
                gender: None,
                quality: Some("system".to_string()),
                sample_rate: Some(22050),
            });
        }

        debug!("Found {} macOS voices", voices.len());
        Ok(voices)
    }

    async fn synthesize(&self, request: TTSRequest) -> Result<TTSResponse> {
        let voice = if request.voice.is_empty() {
            &self.voice
        } else {
            &request.voice
        };

        let sample_rate = request.sample_rate.unwrap_or(22050);
        let format = request.format.as_deref().unwrap_or("aiff");

        // Create temporary file for output - always use AIFF for 'say' output
        let temp_dir = std::env::temp_dir();
        let output_file = temp_dir.join(format!("tts_{}.aiff", uuid::Uuid::new_v4()));

        // Write text to temp file
        let text_file = temp_dir.join(format!("tts_{}.txt", uuid::Uuid::new_v4()));
        std::fs::write(&text_file, &request.text)
            .context("Failed to write text file")?;

        // Build say command
        let mut cmd = Command::new("say");
        cmd.arg("-v").arg(voice)
            .arg("-o").arg(&output_file)
            .arg("-f").arg(&text_file);

        // Add rate if specified
        if let Some(speed) = request.speed {
            // say uses words per minute, default ~175
            let wpm = (175.0 * speed).round() as u32;
            cmd.arg("-r").arg(wpm.to_string());
        }

        info!("Synthesizing with voice '{}': {} chars", voice, request.text.len());
        let output = cmd.output().context("Failed to execute 'say'")?;

        // Cleanup text file
        let _ = std::fs::remove_file(&text_file);

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("'say' synthesis failed: {}", stderr);
        }

        // Read generated audio
        let audio_data = std::fs::read(&output_file)
            .context("Failed to read generated audio file")?;

        // Cleanup audio file
        let _ = std::fs::remove_file(&output_file);

        // Convert to requested format if needed (using afconvert)
        let final_audio = if format != "aiff" {
            self.convert_audio(&audio_data, "aiff", format)?
        } else {
            audio_data
        };

        // Estimate duration
        let duration_ms = estimate_duration(&final_audio, format, sample_rate);

        Ok(TTSResponse {
            audio_data: final_audio,
            format: format.to_string(),
            sample_rate,
            channels: 1,
            duration_ms,
            voice_used: voice.to_string(),
        })
    }

    fn config(&self) -> EngineConfig {
        self.config.clone()
    }

    fn is_available(&self) -> bool {
        Self::is_available_static()
    }
}

impl MacOSSayEngine {
    fn convert_audio(&self, data: &[u8], from_fmt: &str, to_fmt: &str) -> Result<Vec<u8>> {
        use std::io::Write;
        use tempfile::NamedTempFile;

        let mut input_file = NamedTempFile::with_suffix(&format!(".{}", from_fmt))?;
        input_file.write_all(data)?;
        input_file.flush()?;

        let output_file = NamedTempFile::with_suffix(&format!(".{}", to_fmt))?;

        let output = Command::new("afconvert")
            .arg("-f")
            .arg(match to_fmt {
                "m4a" | "aac" => "m4af",
                "mp3" => "MPG3",
                "wav" => "WAVE",
                "aiff" => "AIFF",
                _ => anyhow::bail!("Unsupported output format: {}", to_fmt),
            })
            .arg("-d")
            .arg(match to_fmt {
                "m4a" | "aac" => "aac",
                "mp3" => ".mp3",
                "wav" => "LEI16",
                "aiff" => "BEI16",
                _ => "aac",
            })
            .arg(input_file.path())
            .arg(output_file.path())
            .output()?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            anyhow::bail!("afconvert failed: {}", stderr);
        }

        let converted = std::fs::read(output_file.path())?;
        Ok(converted)
    }
}

/// Estimate audio duration from raw data
fn estimate_duration(data: &[u8], format: &str, sample_rate: u32) -> u64 {
    // Rough estimation based on format and bitrate
    match format {
        "m4a" | "aac" => {
            // AAC ~48kbps mono
            (data.len() as f64 * 8.0 / 48000.0 * 1000.0) as u64
        }
        "mp3" => {
            // MP3 ~64kbps mono
            (data.len() as f64 * 8.0 / 64000.0 * 1000.0) as u64
        }
        "wav" | "aiff" => {
            // Uncompressed 16-bit mono
            (data.len() as f64 / (sample_rate as f64 * 2.0) * 1000.0) as u64
        }
        _ => {
            // Default: assume ~48kbps
            (data.len() as f64 * 8.0 / 48000.0 * 1000.0) as u64
        }
    }
}

/// Create engine from configuration
pub fn create_engine(config: &EngineConfig) -> Result<Box<dyn TTSEngine>> {
    match config.engine_type.as_str() {
        "macos-say" => {
            let voice = config.voice.clone();
            Ok(Box::new(MacOSSayEngine::new(voice)?))
        }
        "piper" => {
            // TODO: Implement Piper TTS engine
            anyhow::bail!("Piper engine not yet implemented")
        }
        "coqui" => {
            // TODO: Implement Coqui TTS engine
            anyhow::bail!("Coqui engine not yet implemented")
        }
        _ => anyhow::bail!("Unknown engine type: {}", config.engine_type),
    }
}
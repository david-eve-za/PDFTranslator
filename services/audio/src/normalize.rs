//! EBU R128 Loudness Normalization
//!
//! Implements ITU-R BS.1770 / EBU R128 loudness normalization for consistent
//!
//! CUPID: Predictable - Deterministic normalization with explicit parameters

use anyhow::{Context, Result};
use std::io::Write;
use tempfile::NamedTempFile;
use tokio::process::Command;

/// Deserialize f32 from string (ffmpeg loudnorm outputs values as strings)
fn deserialize_f32_from_str<'de, D>(deserializer: D) -> std::result::Result<f32, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let s = <String as serde::Deserialize<'de>>::deserialize(deserializer)?;
    s.parse::<f32>().map_err(serde::de::Error::custom)
}

/// EBU R128 normalization configuration
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct NormalizationConfig {
    /// Enable normalization
    pub enabled: bool,

    /// Target integrated loudness in LUFS (EBU R128 default: -16 LUFS for streaming)
    pub target_loudness: f32, // -16.0 for EBU R128, -14 for podcasts, -23 for broadcast

    /// Target true peak in dBTP (EBU R128: -1 dBTP)
    pub true_peak: f32,

    /// Target loudness range in LU (EBU R128: 11 LU typical)
    pub loudness_range: f32,

    /// Use experimental mode for faster processing
    #[serde(default)]
    pub fast_mode: bool,
}

impl Default for NormalizationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            target_loudness: -16.0,
            true_peak: -1.5,
            loudness_range: 11.0,
            fast_mode: false,
        }
    }
}

/// Audio loudness measurement
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct LoudnessInfo {
    /// Integrated loudness (LUFS) - from ffmpeg's input_i
    #[serde(rename = "input_i", deserialize_with = "deserialize_f32_from_str")]
    pub integrated_loudness: f32,

    /// True peak (dBTP) - from ffmpeg's input_tp
    #[serde(rename = "input_tp", deserialize_with = "deserialize_f32_from_str")]
    pub true_peak: f32,

    /// Loudness range (LU) - from ffmpeg's input_lra
    #[serde(rename = "input_lra", deserialize_with = "deserialize_f32_from_str")]
    pub loudness_range: f32,

    /// Threshold loudness (LUFS) - from ffmpeg's input_thresh
    #[serde(rename = "input_thresh", deserialize_with = "deserialize_f32_from_str")]
    pub threshold: f32,
}

/// Normalize audio to EBU R128 target loudness using ffmpeg loudnorm filter
pub async fn normalize_ebu_r128(input_data: &[u8], config: &NormalizationConfig) -> Result<Vec<u8>> {
    if !config.enabled {
        return Ok(input_data.to_vec());
    }

    // First pass: measure loudness
    let loudness_info = measure_loudness(input_data).await?;

    // Log measured values
    tracing::info!(
        "Measured loudness: I={:.1} LUFS, TP={:.1} dBTP, LRA={:.1} LU",
        loudness_info.integrated_loudness,
        loudness_info.true_peak,
        loudness_info.loudness_range
    );

    // Calculate needed gain
    let gain = config.target_loudness - loudness_info.integrated_loudness;

    // Determine if normalization is needed (within tolerance)
    const LOUDNESS_TOLERANCE: f32 = 0.5;
    if gain.abs() < LOUDNESS_TOLERANCE && loudness_info.true_peak <= config.true_peak {
        tracing::info!("Audio already within tolerance, skipping normalization");
        return Ok(input_data.to_vec());
    }

    // Second pass: apply normalization
    let normalized = apply_loudnorm(input_data, &loudness_info, config).await?;

    Ok(normalized)
}

/// Measure loudness using ffmpeg loudnorm filter (first pass)
async fn measure_loudness(input_data: &[u8]) -> Result<LoudnessInfo> {
    use std::io::Write;

    let mut input_file = NamedTempFile::with_suffix(".wav")?;
    input_file.write_all(input_data)?;
    input_file.flush()?;

    let mut output_file = NamedTempFile::with_suffix(".wav")?;

    // First pass: print_format=json for measurement
    let mut cmd = Command::new("ffmpeg");
    cmd.arg("-y")
        .arg("-i").arg(input_file.path())
        .arg("-af").arg("loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json")
        .arg("-f").arg("null")
        .arg("-");

    let output = cmd.output().await
        .context("ffmpeg loudnorm measurement failed")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg loudnorm failed: {}", stderr);
    }

    // Parse JSON output from stderr
    let stderr = String::from_utf8_lossy(&output.stderr);
    let json_start = stderr.find('{')
        .context("No JSON output in ffmpeg loudnorm")?;
    // Find the matching closing brace
    let json_str = extract_json_object(&stderr[json_start..]);
    let mut loudness_info: LoudnessInfo = serde_json::from_str(&json_str)
        .context("Failed to parse loudnorm JSON")?;

    // Adjust threshold based on measured values
    loudness_info.threshold = loudness_info.integrated_loudness - 10.0;

    Ok(loudness_info)
}

/// Apply loudness normalization (second pass)
async fn apply_loudnorm(
    input_data: &[u8],
    measured: &LoudnessInfo,
    config: &NormalizationConfig,
) -> Result<Vec<u8>> {
    use std::io::Write;

    let mut input_file = NamedTempFile::with_suffix(".wav")?;
    input_file.write_all(input_data)?;
    input_file.flush()?;

    let mut output_file = NamedTempFile::with_suffix(".wav")?;

    // Build loudnorm filter with measured values
    let filter = format!(
        "loudnorm=I={}:TP={}:LRA={}:measured_I={}:measured_TP={}:measured_LRA={}:measured_thresh={}:offset={}:linear=true:print_format=summary",
        config.target_loudness,
        config.true_peak,
        config.loudness_range,
        measured.integrated_loudness,
        measured.true_peak,
        measured.loudness_range,
        measured.threshold,
        config.target_loudness - measured.integrated_loudness,
    );

    let mut cmd = Command::new("ffmpeg");
    cmd.arg("-y")
        .arg("-i").arg(input_file.path())
        .arg("-af").arg(&filter)
        .arg("-ar").arg("24000")
        .arg("-ac").arg("1")
        .arg("-sample_fmt").arg("s16")
        .arg(output_file.path());

    let output = cmd.output().await
        .context("ffmpeg loudnorm apply failed")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg loudnorm apply failed: {}", stderr);
    }

    let normalized = tokio::fs::read(output_file.path()).await
        .context("Failed to read normalized audio")?;

    Ok(normalized)
}

/// Two-pass normalization with temporary files (for large files)
pub async fn normalize_ebu_r128_file(
    input_path: &std::path::Path,
    output_path: &std::path::Path,
    config: &NormalizationConfig,
) -> Result<()> {
    let input_data = tokio::fs::read(input_path).await?;
    let normalized = normalize_ebu_r128(&input_data, config).await?;
    tokio::fs::write(output_path, normalized).await?;
    Ok(())
}

/// Quick normalization using single-pass mode (less accurate, faster)
pub async fn quick_normalize(input_data: &[u8], target_loudness: f32) -> Result<Vec<u8>> {
    let mut input_file = NamedTempFile::with_suffix(".wav")?;
    input_file.write_all(input_data)?;
    input_file.flush()?;

    let mut output_file = NamedTempFile::with_suffix(".wav")?;

    let filter = format!("loudnorm=I={}:TP=-1.5:LRA=11:dual_mono=true", target_loudness);

    let mut cmd = Command::new("ffmpeg");
    cmd.arg("-y")
        .arg("-i").arg(input_file.path())
        .arg("-af").arg(&filter)
        .arg("-ar").arg("24000")
        .arg("-ac").arg("1")
        .arg(output_file.path());

    let output = cmd.output().await
        .context("ffmpeg quick normalize failed")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("ffmpeg quick normalize failed: {}", stderr);
    }

    let normalized = tokio::fs::read(output_file.path()).await?;
    Ok(normalized)
}

/// Extract a single JSON object from a string starting with '{'
fn extract_json_object(s: &str) -> String {
    let mut depth = 0;
    let mut in_string = false;
    let mut escape = false;
    let mut end = 0;

    for (i, c) in s.char_indices() {
        if escape {
            escape = false;
            continue;
        }
        if c == '\\' {
            escape = true;
            continue;
        }
        if c == '"' && !escape {
            in_string = !in_string;
        }
        if !in_string {
            match c {
                '{' => depth += 1,
                '}' => {
                    depth -= 1;
                    if depth == 0 {
                        end = i + 1;
                        break;
                    }
                }
                _ => {}
            }
        }
    }

    if end == 0 {
        s.to_string()
    } else {
        s[..end].to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_defaults() {
        let config = NormalizationConfig::default();
        assert!(config.enabled);
        assert_eq!(config.target_loudness, -16.0);
        assert_eq!(config.true_peak, -1.5);
        assert_eq!(config.loudness_range, 11.0);
    }

    #[tokio::test]
    async fn test_measure_loudness() {
        // This test requires ffmpeg and would need test audio
        // Skipped in CI, manual testing only
    }
}
# Design: Generate Audio CLI Command

**Date:** 2026-04-20
**Author:** AI Assistant
**Status:** Approved

## Overview

Add a new CLI command `generate-audio` to convert translated text from database chapters/volumes into audio files using the existing `AudioGenerator` tool.

## Requirements

- Generate audio for a single chapter (by ID) or all chapters in a volume (by ID)
- Use translated text from database (`chapter.translated_text`)
- Output to configurable audiobooks directory with automatic naming
- Support voice selection via CLI flag
- Show progress during audio generation

## CLI Interface

```bash
# Single chapter
python PDFAgent.py generate-audio --chapter-id 123

# Entire volume
python PDFAgent.py generate-audio --volume-id 5

# With custom voice
python PDFAgent.py generate-audio --volume-id 5 --voice "Paulina"
```

### Arguments

| Argument | Short | Type | Required | Description |
|----------|-------|------|----------|-------------|
| `--chapter-id` | `-c` | int | Conditional | Chapter ID to generate audio for |
| `--volume-id` | `-v` | int | Conditional | Volume ID to generate audio for all chapters |
| `--voice` | | str | No | TTS voice (default: `processing.voice`) |

**Validation:** Only one of `--chapter-id` or `--volume-id` can be specified.

## Output Structure

**Directory:** `audiobooks/{work_title}/{volume_number}/`

**Filename:** `{work_title}_Vol{volume_number}_Ch{chapter_number:03d}.m4a`

**Example:** `audiobooks/MyLightNovel/Vol1/MyLightNovel_Vol1_Ch003.m4a`

## Data Flow

```
CLI Arguments
    ↓
Validate flags (chapter-id XOR volume-id)
    ↓
Query database (ChapterRepository/VolumeRepository)
    ↓
Verify translated_text exists
    ↓
Build output path
    ↓
AudioGenerator.process_texts()
    ↓
Success/Error message
```

## Implementation Details

### New File

`src/pdftranslator/cli/commands/generate_audio.py`

### Components

1. **Command function** (`generate_audio`) - Typer command with mutual exclusion validation
2. **Helper function** (`_generate_chapter_audio`) - Generate audio for single chapter
3. **Helper function** (`_generate_volume_audio`) - Generate audio for all chapters in volume

### Dependencies

- `AudioGenerator` from `pdftranslator.tools.AudioGenerator`
- `ChapterRepository` from `pdftranslator.database.repositories.chapter_repository`
- `VolumeRepository` from `pdftranslator.database.repositories.volume_repository`
- `WorkRepository` from `pdftranslator.database.repositories.work_repository`
- `Settings` from `pdftranslator.core.config.settings`

### Integration Points

1. Register in `src/pdftranslator/cli/commands/__init__.py`
2. Import in `src/pdftranslator/cli/app.py`

## Error Handling

| Error | Message |
|-------|---------|
| Both flags specified | "Specify only one: --chapter-id or --volume-id" |
| No flag specified | "Must specify --chapter-id or --volume-id" |
| Chapter not found | "Chapter with ID {id} not found" |
| Volume not found | "Volume with ID {id} not found" |
| No translated text | "Chapter {id} has no translated text" |
| Audio generation failed | Log error, continue (volume) or return (chapter) |
| File already exists | "Audio file already exists: {path}. Skipping." |

## Success Criteria

- [ ] Command generates audio for single chapter by ID
- [ ] Command generates audio for all chapters in volume
- [ ] Progress bar shown during generation
- [ ] Automatic output directory and filename
- [ ] Voice configurable via flag
- [ ] Clear error messages for all failure cases
- [ ] Files skip if already exist

## Testing Strategy

1. Unit tests for helper functions
2. Integration tests with mock database
3. Manual testing with real chapters/volumes

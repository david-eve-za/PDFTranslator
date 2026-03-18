# Design: Eliminate config.json Dependency

**Date:** 2026-03-17
**Status:** Approved

## Overview

Remove the dependency on `config.json` file from the application execution. The configuration should be sourced solely from `GlobalConfig.py` defaults and command-line arguments.

## Architecture

**Simplified architecture:**
- GlobalConfig singleton with default values in code
- PDFAgent.py sources configuration from: defaults → CLI args
- Eliminate all references to config.json
- No load/save methods in the execution flow

**Configuration flow:**
1. PDFAgent.py initializes GlobalConfig (uses defaults from `__init__`)
2. CLI args parser reads user arguments
3. `config.update_from_args(args)` updates any provided values
4. Rest of program uses `GlobalConfig()` singleton directly

## Components and Changes

### Changes in PDFAgent.py

1. **Remove constant** (line 24):
   ```python
   - CONFIG_FILE_NAME = "config.json"
   ```

2. **Remove load block** (lines 263-270):
   ```python
   - try:
   -     config.load(CONFIG_FILE_NAME)
   -     logging.info(f"Loaded configuration from {CONFIG_FILE_NAME}")
   - except FileNotFoundError:
   -     logging.info(f"{CONFIG_FILE_NAME} not found. Using default settings and command-line arguments.")
   - except ValueError as e:
   -     logging.error(f"Error loading {CONFIG_FILE_NAME}: {e}. Please check the file format.")
   -     return
   ```

3. **Remove save block** (lines 280-282):
   ```python
   - # --- Save final config ---
   - config.save(CONFIG_FILE_NAME)
   - logging.info(f"Final configuration saved to {CONFIG_FILE_NAME}")
   ```

4. **Update error message** (line 276):
   ```python
   - logging.error("Input path is not specified in config.json or as a command-line argument. Exiting.")
   + logging.error("Input path is not specified as a command-line argument. Exiting.")
   ```

### GlobalConfig.py (No changes)

- Keep `load()` and `save()` methods available (do not delete)
- Simply do not use them in the main flow

## Data Flow

**Simplified data flow:**

```
User executes PDFAgent.py
         ↓
argparse parses CLI args
         ↓
GlobalConfig() singleton initialized with defaults
         ↓
config.update_from_args(args) - applies CLI args overrides
         ↓
Rest of program uses GlobalConfig() directly
         ↓
Process files, generate audio/video
```

**Example with args:**
```bash
python PDFAgent.py ./docs -sl en-US -tl es-MX --agent ollama
```
- Defaults: source_lang="en-US", target_lang="es-MX", agent="gemini"
- CLI args override: agent="ollama" (rest matches defaults)

## Error Handling

1. **Missing input_path:**
   - `argparse` already handles this (optional `nargs='?'`)
   - Explicit check on line 275 keeps error + help
   - Message simplified to "command-line argument" without mentioning config.json

2. **Args validation:**
   - `argparse` validates types and restrictions (choices, etc.)
   - `update_from_args()` already verifies attribute exists before setting

3. **No changes to error handling:**
   - Current flow already handles errors well
   - Just update error messages to not mention config.json

## Testing

1. **Test without input_path:**
   - Run `python PDFAgent.py` without arguments
   - Verify: error + help without mentioning config.json

2. **Test with CLI args:**
   - Run `python PDFAgent.py ./docs -sl en-US -tl es-MX --agent nvidia` (new value)
   - Verify: program correctly uses args + defaults

3. **Test behavior without config.json:**
   - Ensure config.json file is not created after execution
   - Ensure config.json is not searched for or read

4. **Test regression:**
   - Verify existing functionality still works
   - Audio/video generation not affected

## Benefits

- Simpler configuration model
- Less code to maintain
- Predictable behavior (always uses defaults + CLI args)
- No confusion about configuration source
- Easier to understand and debug

## Trade-offs

- Users must specify all non-default values via CLI args
- No way to persist configuration between runs
- Less flexible for users who want to customize many settings permanently

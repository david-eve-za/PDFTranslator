"""Settings management routes."""

from pathlib import Path

from fastapi import APIRouter

from pdftranslator.backend.api.models.schemas import (
    SettingsResponse,
    SettingsUpdateRequest,
)
from pdftranslator.core.config.settings import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/", response_model=SettingsResponse)
async def get_settings_api():
    """Get current settings (secrets masked)."""
    settings = get_settings()
    return _settings_to_response(settings)


@router.put("/")
async def update_settings(data: SettingsUpdateRequest):
    """Update settings and write to .env file."""
    env_updates = {}

    if data.llm:
        env_updates.update(_flatten_llm_settings(data.llm))
    if data.database:
        env_updates.update(_flatten_db_settings(data.database))
    if data.document:
        env_updates.update(_flatten_doc_settings(data.document))
    if data.nlp:
        env_updates.update(_flatten_nlp_settings(data.nlp))
    if data.paths:
        env_updates.update(_flatten_path_settings(data.paths))

    if env_updates:
        _update_env_file(env_updates)

    return {
        "message": "Settings updated. Restart backend to apply changes.",
        "restart_required": True,
    }


@router.post("/restart")
async def restart_backend():
    """Request backend restart (informational - actual restart handled externally)."""
    return {
        "message": "Restart signal sent. Please restart the backend manually or via orchestrator."
    }


def _settings_to_response(settings) -> dict:
    """Convert settings to response dict, masking secrets."""
    return {
        "llm": {
            "agent": settings.llm.agent.value,
            "nvidia": {
                "model_name": settings.llm.nvidia.model_name,
                "temperature": settings.llm.nvidia.temperature,
                "top_p": settings.llm.nvidia.top_p,
                "max_output_tokens": settings.llm.nvidia.max_output_tokens,
            },
            "gemini": {
                "model_names": settings.llm.gemini.model_names,
                "temperature": settings.llm.gemini.temperature,
                "top_p": settings.llm.gemini.top_p,
            },
            "ollama": {
                "model_name": settings.llm.ollama.model_name,
                "temperature": settings.llm.ollama.temperature,
            },
            "nvidia_api_key": "***" if settings.llm.nvidia_api_key else "",
            "google_api_key": "***" if settings.llm.google_api_key else "",
        },
        "database": {
            "host": settings.database.host,
            "port": settings.database.port,
            "name": settings.database.name,
            "user": settings.database.user,
            "password": "***",
            "min_connections": settings.database.min_connections,
            "max_connections": settings.database.max_connections,
        },
        "document": {
            "enable_ocr": settings.document.enable_ocr,
            "ocr_languages": settings.document.ocr_languages,
            "accelerator_device": settings.document.accelerator_device,
            "do_table_structure": settings.document.do_table_structure,
            "generate_page_images": settings.document.generate_page_images,
        },
        "nlp": {
            "ner_model": settings.nlp.ner_model,
            "entity_types": settings.nlp.entity_types,
            "min_entity_length": settings.nlp.min_entity_length,
            "max_entity_length": settings.nlp.max_entity_length,
            "confidence_threshold": settings.nlp.confidence_threshold,
        },
        "paths": {
            "translation_prompt_path": str(settings.paths.translation_prompt_path),
            "audiobooks_dir": str(settings.paths.audiobooks_dir),
            "videos_dir": str(settings.paths.videos_dir),
        },
    }


def _flatten_llm_settings(data: dict) -> dict:
    """Flatten LLM settings to env variable names."""
    result = {}
    if "agent" in data:
        result["LLM__AGENT"] = data["agent"]
    if "nvidia" in data:
        for key, value in data["nvidia"].items():
            result[f"LLM__NVIDIA__{key.upper()}"] = str(value)
    if "gemini" in data:
        for key, value in data["gemini"].items():
            result[f"LLM__GEMINI__{key.upper()}"] = str(value)
    if "ollama" in data:
        for key, value in data["ollama"].items():
            result[f"LLM__OLLAMA__{key.upper()}"] = str(value)
    if "nvidia_api_key" in data and data["nvidia_api_key"] != "***":
        result["NVIDIA_API_KEY"] = data["nvidia_api_key"]
    if "google_api_key" in data and data["google_api_key"] != "***":
        result["GOOGLE_API_KEY"] = data["google_api_key"]
    return result


def _flatten_db_settings(data: dict) -> dict:
    """Flatten database settings to env variable names."""
    result = {}
    mapping = {
        "host": "DB_HOST",
        "port": "DB_PORT",
        "name": "DB_NAME",
        "user": "DB_USER",
        "password": "DB_PASSWORD",
        "min_connections": "DB_MIN_CONNECTIONS",
        "max_connections": "DB_MAX_CONNECTIONS",
    }
    for key, env_key in mapping.items():
        if key in data and (key != "password" or data[key] != "***"):
            result[env_key] = str(data[key])
    return result


def _flatten_doc_settings(data: dict) -> dict:
    """Flatten document settings to env variable names."""
    result = {}
    for key, value in data.items():
        result[f"DOCUMENT__{key.upper()}"] = str(value)
    return result


def _flatten_nlp_settings(data: dict) -> dict:
    """Flatten NLP settings to env variable names."""
    result = {}
    for key, value in data.items():
        result[f"NLP__{key.upper()}"] = str(value)
    return result


def _flatten_path_settings(data: dict) -> dict:
    """Flatten path settings to env variable names."""
    result = {}
    for key, value in data.items():
        result[f"PATHS__{key.upper()}"] = str(value)
    return result


def _update_env_file(updates: dict) -> None:
    """Update .env file with new values."""
    env_path = Path(".env")

    existing_lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            existing_lines = f.readlines()

    existing_keys = {}
    for i, line in enumerate(existing_lines):
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=")[0].strip()
            existing_keys[key] = i

    for key, value in updates.items():
        line = f"{key}={value}\n"
        if key in existing_keys:
            existing_lines[existing_keys[key]] = line
        else:
            existing_lines.append(line)

    with open(env_path, "w") as f:
        f.writelines(existing_lines)

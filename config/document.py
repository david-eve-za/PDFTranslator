"""Document processing configuration."""

from pydantic import BaseModel, Field, field_validator


class DoclingConfig(BaseModel):
    """Configuration for Docling document extraction."""

    enable_ocr: bool = Field(
        default=False, description="Enable OCR for scanned PDF documents"
    )
    ocr_languages: list[str] = Field(
        default=["en", "es"], description="Languages for OCR recognition"
    )
    do_table_structure: bool = Field(
        default=False, description="Extract table structure (not needed for novels)"
    )
    generate_page_images: bool = Field(
        default=False, description="Generate page images during extraction"
    )
    accelerator_device: str = Field(
        default="mps", description="Hardware accelerator: auto, cpu, cuda, mps"
    )

    @field_validator("accelerator_device")
    @classmethod
    def validate_accelerator_device(cls, v: str) -> str:
        """Validate accelerator device is one of allowed values."""
        allowed = {"auto", "cpu", "cuda", "mps"}
        if v not in allowed:
            raise ValueError(f"accelerator_device must be one of {allowed}, got {v}")
        return v

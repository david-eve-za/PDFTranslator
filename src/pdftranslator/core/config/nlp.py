"""NLP configuration models."""

from pydantic import BaseModel, Field


class NLPSettings(BaseModel):
    """NLP and entity extraction settings."""

    ner_model: str = Field(default="en_core_web_sm")
    entity_types: list[str] = Field(
        default_factory=lambda: [
            "PERSON",
            "ORG",
            "GPE",
            "LOC",
            "NORP",
            "FAC",
            "PRODUCT",
            "EVENT",
            "WORK_OF_ART",
            "LAW",
        ],
        description="spaCy entity types to extract",
    )
    min_entity_length: int = Field(default=2, ge=1)
    max_entity_length: int = Field(default=100, ge=1)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

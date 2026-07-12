#!/usr/bin/env python3
"""
Generate Python clients from Avro schemas + CloudEvents envelope.

Usage:
    python generate_clients.py
    python generate_clients.py --language python
    python generate_clients.py --language go
    python generate_clients.py --language typescript
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List

SCHEMA_DIR = Path(__file__).parent.parent / "schemas" / "avro"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "shared" / "events"

LANGUAGES = {
    "python": {
        "output": OUTPUT_DIR / "python",
        "generator": "avro-python",
        "package": "pdftranslator.events",
    },
    "go": {
        "output": OUTPUT_DIR / "go",
        "generator": "avro-go",
        "package": "github.com/pdftranslator/events",
    },
    "typescript": {
        "output": OUTPUT_DIR / "typescript",
        "generator": "avro-typescript",
        "package": "@pdftranslator/events",
    },
}

def find_schemas() -> List[Path]:
    """Find all Avro schema files."""
    return sorted(SCHEMA_DIR.glob("*.avsc"))

def generate_python(schemas: List[Path]) -> bool:
    """Generate Python classes from Avro schemas using avrogen."""
    output_dir = LANGUAGES["python"]["output"]
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py
    init_file = output_dir / "__init__.py"
    init_file.write_text('"""PDFTranslator Event Models (Generated from Avro schemas)"""\\n')

    for schema_path in schemas:
        try:
            # Use avrogen to generate Python code
            result = subprocess.run([
                "avrogen",
                "-o", str(output_dir),
                str(schema_path)
            ], capture_output=True, text=True, check=True)
            print(f"✅ Generated Python for {schema_path.name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate Python for {schema_path.name}: {e.stderr}")
            return False
        except FileNotFoundError:
            print("⚠️  avrogen not installed. Install with: pip install avrogen")
            return False

    # Generate CloudEvents envelope classes
    generate_cloudevents_python(output_dir)
    return True

def generate_cloudevents_python(output_dir: Path):
    """Generate CloudEvents envelope base classes."""
    envelope_code = '''"""
CloudEvents Envelope Classes for PDFTranslator.

Generated automatically - do not edit manually.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime
import uuid


@dataclass
class CloudEvent:
    """CloudEvents 1.0 envelope."""
    specversion: str = "1.0"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    source: str = ""
    datacontenttype: str = "application/avro"
    data: Any = None
    subject: Optional[str] = None
    time: Optional[str] = None  # RFC3339
    traceparent: Optional[str] = None
    tracestate: Optional[str] = None
    extensions: dict = field(default_factory=dict)

    def to_http_headers(self) -> dict[str, str]:
        """Convert to HTTP headers for CloudEvents HTTP binding."""
        headers = {
            "ce-specversion": self.specversion,
            "ce-id": self.id,
            "ce-type": self.type,
            "ce-source": self.source,
            "ce-datacontenttype": self.datacontenttype,
        }
        if self.subject:
            headers["ce-subject"] = self.subject
        if self.time:
            headers["ce-time"] = self.time
        if self.traceparent:
            headers["traceparent"] = self.traceparent
        if self.tracestate:
            headers["tracestate"] = self.tracestate
        for k, v in self.extensions.items():
            headers[f"ce-{k}"] = str(v)
        return headers

    @classmethod
    def from_http_headers(cls, headers: dict[str, str], data: Any) -> "CloudEvent":
        """Create CloudEvent from HTTP headers."""
        ce = cls(data=data)
        for k, v in headers.items():
            if k.lower().startswith("ce-"):
                attr = k[3:].replace("-", "_")
                if hasattr(ce, attr):
                    setattr(ce, attr, v)
        return ce


@dataclass
class EventMetadata:
    """Common metadata for all PDFTranslator events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    event_version: int = 1
    timestamp: int = field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
    source: str = ""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    def to_cloudevent(self, payload: Any, subject: str, time: datetime) -> CloudEvent:
        return CloudEvent(
            id=self.event_id,
            type=self.event_type,
            source=self.source,
            data=payload,
            subject=subject,
            time=time.isoformat() + "Z",
            traceparent=f"00-{self.trace_id or '0'*32}-{self.span_id or '0'*16}-01" if self.trace_id else None,
            extensions={
                "eventversion": self.event_version,
            }
        )


# Event Type Constants
class EventTypes:
    # Catalog Service
    WORK_CREATED = "com.pdftranslator.catalog.work.created"
    VOLUME_CREATED = "com.pdftranslator.catalog.volume.created"
    CHAPTER_CREATED = "com.pdftranslator.catalog.chapter.created"

    # Document Service
    DOCUMENT_EXTRACTED = "com.pdftranslator.document.extracted"
    DOCUMENT_EXTRACTION_FAILED = "com.pdftranslator.document.extraction.failed"

    # Glossary Service
    GLOSSARY_BUILT = "com.pdftranslator.glossary.built"
    GLOSSARY_UPDATED = "com.pdftranslator.glossary.updated"
    GLOSSARY_VALIDATED = "com.pdftranslator.glossary.validated"

    # Translation Service
    JOB_QUEUED = "com.pdftranslator.translation.job.queued"
    JOB_STARTED = "com.pdftranslator.translation.job.started"
    JOB_COMPLETED = "com.pdftranslator.translation.job.completed"
    JOB_FAILED = "com.pdftranslator.translation.job.failed"
    JOB_STATUS_CHANGED = "com.pdftranslator.job.status.changed"

    # Job Orchestrator
    WORKFLOW_STARTED = "com.pdftranslator.job.workflow.started"
    WORKFLOW_COMPLETED = "com.pdftranslator.job.workflow.completed"
    WORKFLOW_FAILED = "com.pdftranslator.job.workflow.failed"

    # Audio Service
    AUDIO_GENERATED = "com.pdftranslator.audio.generated"
    AUDIO_GENERATION_FAILED = "com.pdftranslator.audio.generation.failed"


# Source Service Identifiers
class EventSources:
    CATALOG = "/pdftranslator/catalog-service"
    DOCUMENT = "/pdftranslator/document-service"
    GLOSSARY = "/pdftranslator/glossary-service"
    TRANSLATION = "/pdftranslator/translation-service"
    JOB_ORCHESTRATOR = "/pdftranslator/job-orchestrator"
    AUDIO = "/pdftranslator/audio-service"


def create_event(
    event_type: str,
    source: str,
    payload: Any,
    subject: str,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    event_version: int = 1,
) -> CloudEvent:
    """Factory function to create a properly formatted CloudEvent."""
    metadata = EventMetadata(
        event_type=event_type,
        source=source,
        trace_id=trace_id,
        span_id=span_id,
        event_version=event_version,
    )
    return metadata.to_cloudevent(payload, subject, datetime.utcnow())
'''

    (output_dir / "cloudevents.py").write_text(envelope_code)
    print("✅ Generated cloudevents.py")

def generate_go(schemas: List[Path]) -> bool:
    """Generate Go code from Avro schemas."""
    print("⚠️  Go generation not yet implemented. Use 'goavro' library.")
    return True

def generate_typescript(schemas: List[Path]) -> bool:
    """Generate TypeScript types from Avro schemas."""
    print("⚠️  TypeScript generation not yet implemented. Use 'avro-typescript' package.")
    return True

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate event clients from Avro schemas")
    parser.add_argument("--language", choices=list(LANGUAGES.keys()), default="all")
    args = parser.parse_args()

    schemas = find_schemas()
    if not schemas:
        print(f"❌ No schemas found in {SCHEMA_DIR}")
        return 1

    print(f"📋 Found {len(schemas)} schema(s): {[s.name for s in schemas]}")

    languages = [args.language] if args.language != "all" else list(LANGUAGES.keys())

    success = True
    for lang in languages:
        print(f"\\n🔧 Generating {lang} client...")
        if lang == "python":
            success &= generate_python(schemas)
        elif lang == "go":
            success &= generate_go(schemas)
        elif lang == "typescript":
            success &= generate_typescript(schemas)

    if success:
        print("\\n✅ All clients generated successfully!")
        return 0
    else:
        print("\\n❌ Some generations failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
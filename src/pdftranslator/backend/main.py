"""FastAPI backend application for PDFTranslator."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pdftranslator.backend.api.routes import (
    chapters,
    files,
    glossary,
    settings,
    split,
    substitution_rules,
    translation,
    volumes,
    works,
)

app = FastAPI(
    title="PDFTranslator API",
    version="1.0.0",
    description="API for document translation and processing",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint returning API info."""
    return {"message": "PDFTranslator API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


app.include_router(files.router)
app.include_router(glossary.router)
app.include_router(translation.router)
app.include_router(works.router)
app.include_router(volumes.router)
app.include_router(chapters.router)
app.include_router(split.router)
app.include_router(settings.router)
app.include_router(substitution_rules.router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

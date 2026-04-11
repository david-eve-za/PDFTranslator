-- database/schemas/010_uploaded_files.sql
CREATE TABLE IF NOT EXISTS uploaded_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(500) NOT NULL,
    file_path TEXT,
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    mime_type VARCHAR(100),
    work_id INTEGER REFERENCES works(id) ON DELETE SET NULL,
    volume_id INTEGER REFERENCES volumes(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'uploaded',
    error_message TEXT,
    source_lang VARCHAR(10) DEFAULT 'en',
    target_lang VARCHAR(10) DEFAULT 'es',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_uploaded_files_status ON uploaded_files(status);
CREATE INDEX idx_uploaded_files_work_id ON uploaded_files(work_id);

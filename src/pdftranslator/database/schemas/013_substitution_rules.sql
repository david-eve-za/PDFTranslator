-- database/schemas/013_substitution_rules.sql
CREATE TABLE IF NOT EXISTS text_substitution_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    pattern VARCHAR(500) NOT NULL,
    replacement VARCHAR(500) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    apply_on_extract BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_substitution_rules_active ON text_substitution_rules(is_active);
CREATE INDEX idx_substitution_rules_apply ON text_substitution_rules(apply_on_extract);

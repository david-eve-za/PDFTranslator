-- database/schemas/008_entity_blacklist.sql
-- Tabla para términos que nunca deben tratarse como entidades

CREATE TABLE IF NOT EXISTS entity_blacklist (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Valores iniciales: stopwords en inglés y español, metadatos
INSERT INTO entity_blacklist (term, reason) VALUES
-- Stopwords inglés
('the', 'stopword'),
('and', 'stopword'),
('or', 'stopword'),
('but', 'stopword'),
('in', 'stopword'),
('on', 'stopword'),
('at', 'stopword'),
('to', 'stopword'),
('for', 'stopword'),
('of', 'stopword'),
('a', 'stopword'),
('an', 'stopword'),
('is', 'stopword'),
('was', 'stopword'),
('be', 'stopword'),
('been', 'stopword'),
('have', 'stopword'),
('had', 'stopword'),
('do', 'stopword'),
('did', 'stopword'),
-- Verbos comunes de diálogo
('said', 'stopword'),
('asked', 'stopword'),
('replied', 'stopword'),
('thought', 'stopword'),
('felt', 'stopword'),
('knew', 'stopword'),
('saw', 'stopword'),
-- Metadatos de documento
('chapter', 'metadata'),
('volume', 'metadata'),
('part', 'metadata'),
('book', 'metadata'),
('story', 'metadata'),
('novel', 'metadata'),
-- Stopwords español
('el', 'stopword'),
('la', 'stopword'),
('los', 'stopword'),
('las', 'stopword'),
('un', 'stopword'),
('una', 'stopword'),
('de', 'stopword'),
('del', 'stopword'),
('al', 'stopword'),
-- Pronombres
('he', 'stopword'),
('she', 'stopword'),
('it', 'stopword'),
('they', 'stopword'),
('we', 'stopword'),
('i', 'stopword'),
('you', 'stopword'),
('him', 'stopword'),
('her', 'stopword'),
('them', 'stopword'),
('me', 'stopword'),
('us', 'stopword')
ON CONFLICT (term) DO NOTHING;

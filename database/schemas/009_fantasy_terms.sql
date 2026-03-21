-- database/schemas/009_fantasy_terms.sql
-- Tabla para términos de fantasía que son palabras comunes pero nombres propios en contexto

CREATE TABLE IF NOT EXISTS fantasy_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    entity_type VARCHAR(50) NOT NULL,
    do_not_translate BOOLEAN DEFAULT FALSE,
    context_hint VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Términos base de fantasía
INSERT INTO fantasy_terms (term, entity_type, do_not_translate, context_hint) VALUES
-- Razas de fantasía
('slime', 'race', TRUE, 'criatura gelatinosa'),
('goblin', 'race', TRUE, 'criatura pequeña maligna'),
('orc', 'race', TRUE, 'criatura humanoide agresiva'),
('elf', 'race', TRUE, 'criatura mágica longeva'),
('dwarf', 'race', TRUE, 'criatura pequeña forjadora'),
('dragon', 'race', FALSE, 'bestia alada colosal'),
('demon', 'race', FALSE, 'criatura infernal'),
('undead', 'race', TRUE, 'criatura no-muerta'),
('vampire', 'race', TRUE, 'no-muerto sangriento'),
('werewolf', 'race', TRUE, 'hombre lobo'),
-- Organizaciones
('guild', 'organization', FALSE, 'asociación de aventureros'),
('sect', 'organization', FALSE, 'escuela de artes marciales'),
-- Lugares
('dungeon', 'place', FALSE, 'laberinto con monstruos'),
('labyrinth', 'place', FALSE, 'laberinto subterráneo'),
-- Habilidades/Conceptos
('mana', 'skill', FALSE, 'energía mágica'),
('spell', 'spell', FALSE, 'magia activa'),
('qi', 'skill', TRUE, 'energía vital china'),
('cultivation', 'skill', FALSE, 'práctica espiritual'),
-- Títulos
('adventurer', 'title', FALSE, 'profesión de explorador'),
('hero', 'title', FALSE, 'protagonista elegido'),
('sage', 'title', FALSE, 'mago anciano')
ON CONFLICT (term) DO NOTHING;

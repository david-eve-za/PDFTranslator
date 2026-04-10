-- database/schemas/009_fantasy_terms.sql
-- Table for fantasy terms that are common words but proper nouns in context

CREATE TABLE IF NOT EXISTS fantasy_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    entity_type VARCHAR(50) NOT NULL,
    do_not_translate BOOLEAN DEFAULT FALSE,
    context_hint VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Base fantasy terms
INSERT INTO fantasy_terms (term, entity_type, do_not_translate, context_hint) VALUES
-- Fantasy races
('slime', 'race', TRUE, 'gelatinous creature'),
('goblin', 'race', TRUE, 'small malignant creature'),
('orc', 'race', TRUE, 'aggressive humanoid creature'),
('elf', 'race', TRUE, 'long-lived magical creature'),
('dwarf', 'race', TRUE, 'small forging creature'),
('dragon', 'race', FALSE, 'colossal winged beast'),
('demon', 'race', FALSE, 'infernal creature'),
('undead', 'race', TRUE, 'undead creature'),
('vampire', 'race', TRUE, 'blood-drinking undead'),
('werewolf', 'race', TRUE, 'wolf-man'),
-- Organizations
('guild', 'organization', FALSE, 'adventurer association'),
('sect', 'organization', FALSE, 'martial arts school'),
-- Places
('dungeon', 'place', FALSE, 'labyrinth with monsters'),
('labyrinth', 'place', FALSE, 'underground maze'),
-- Skills/Concepts
('mana', 'skill', FALSE, 'magical energy'),
('spell', 'spell', FALSE, 'active magic'),
('qi', 'skill', TRUE, 'Chinese vital energy'),
('cultivation', 'skill', FALSE, 'spiritual practice'),
-- Titles
('adventurer', 'title', FALSE, 'explorer profession'),
('hero', 'title', FALSE, 'chosen protagonist'),
('sage', 'title', FALSE, 'ancient mage')
ON CONFLICT (term) DO NOTHING;

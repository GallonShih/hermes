-- Create replacement_wordlists table for post-tokenization word replacement
-- Used by word cloud to merge similar words after tokenization

CREATE TABLE IF NOT EXISTS replacement_wordlists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    replacements JSONB NOT NULL DEFAULT '[]',  -- [{"source": "酥", "target": "方塊酥"}, ...]
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Add comment for documentation
COMMENT ON TABLE replacement_wordlists IS 'Post-tokenization replacement word lists for word cloud';
COMMENT ON COLUMN replacement_wordlists.replacements IS 'JSON array of {source, target} replacement pairs';

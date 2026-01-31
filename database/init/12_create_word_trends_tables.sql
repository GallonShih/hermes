-- Word Trend Groups table for storing user-defined word groups for trend analysis
-- Each group contains multiple words and displays as a separate line chart

CREATE TABLE IF NOT EXISTS word_trend_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    words JSON NOT NULL,  -- Array of strings: ["holo", "cover", "星街"]
    color VARCHAR(20) DEFAULT '#5470C6',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups by name
CREATE INDEX IF NOT EXISTS idx_word_trend_groups_name ON word_trend_groups(name);

-- Comment for documentation
COMMENT ON TABLE word_trend_groups IS 'Stores user-defined word groups for trend analysis. Each group tracks hourly message counts containing any of the specified words.';
COMMENT ON COLUMN word_trend_groups.words IS 'JSON array of strings to match against chat messages using ILIKE contains logic';
COMMENT ON COLUMN word_trend_groups.color IS 'Hex color code for the line chart, e.g. #5470C6';

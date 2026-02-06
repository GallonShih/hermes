-- Live streams metadata table
-- Stores YouTube video metadata fetched when admin sets a new URL
-- Migration: Run this on existing databases

CREATE TABLE IF NOT EXISTS live_streams (
    video_id VARCHAR(20) PRIMARY KEY,
    title TEXT,
    channel_id VARCHAR(255),
    channel_title VARCHAR(255),
    description TEXT,
    thumbnail_url TEXT,
    tags JSONB,
    category_id VARCHAR(10),
    published_at TIMESTAMP WITH TIME ZONE,
    scheduled_start_time TIMESTAMP WITH TIME ZONE,
    actual_start_time TIMESTAMP WITH TIME ZONE,
    live_broadcast_content VARCHAR(20),
    default_language VARCHAR(10),
    topic_categories JSONB,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

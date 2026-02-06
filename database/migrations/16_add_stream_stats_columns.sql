-- Migration: Add video statistics columns to stream_stats table
-- Description: Add view_count, like_count, favorite_count, comment_count
--              from YouTube Data API statistics part
-- Date: 2026-02-07
--
-- Execute in pgAdmin: right-click database → Query Tool → paste & run

ALTER TABLE stream_stats ADD COLUMN IF NOT EXISTS view_count BIGINT;
ALTER TABLE stream_stats ADD COLUMN IF NOT EXISTS like_count INTEGER;
ALTER TABLE stream_stats ADD COLUMN IF NOT EXISTS favorite_count INTEGER;
ALTER TABLE stream_stats ADD COLUMN IF NOT EXISTS comment_count INTEGER;

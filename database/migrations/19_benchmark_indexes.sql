-- ============================================================
-- Index Optimization Benchmark Script
-- ============================================================
-- 使用方式：
--   1. 在執行 19_optimize_indexes.sql 之前，先跑一次本腳本，記錄結果
--   2. 執行 migration
--   3. 再跑一次本腳本，比較 Execution Time 差異
--
-- 關注指標：
--   - "Execution Time" (毫秒) — 實際執行耗時
--   - "Seq Scan" vs "Index Scan" / "Bitmap Index Scan" — 有無用到索引
--   - "Rows Removed by Filter" — 過濾掉多少無用行（越少越好）
--
-- 注意：請替換下方的 :video_id 為你實際的 live_stream_id
--       可先執行以下查詢取得：
--       SELECT DISTINCT live_stream_id FROM chat_messages LIMIT 5;
-- ============================================================


-- ============================================================
-- 0. 查看當前資料量（掌握基準規模）
-- ============================================================

SELECT 'chat_messages' AS table_name, COUNT(*) AS row_count FROM chat_messages
UNION ALL
SELECT 'processed_chat_messages', COUNT(*) FROM processed_chat_messages
UNION ALL
SELECT 'etl_execution_log', COUNT(*) FROM etl_execution_log;


-- ============================================================
-- 1. Wordcloud 查詢 (processed_chat_messages)
--    受益索引: idx_processed_chat_stream_published
--    預期改善: Bitmap AND → 單一 Index Scan
-- ============================================================
-- 替換 'YOUR_VIDEO_ID' 為實際的 live_stream_id

EXPLAIN ANALYZE
SELECT DISTINCT message_id, unnest(tokens) AS word
FROM processed_chat_messages
WHERE live_stream_id = 'YOUR_VIDEO_ID'
  AND published_at >= NOW() - INTERVAL '24 hours'
  AND published_at <= NOW();

-- 對比：只用 published_at（保留的獨立索引，行為應不變）
EXPLAIN ANALYZE
SELECT DISTINCT message_id, unnest(tokens) AS word
FROM processed_chat_messages
WHERE published_at >= NOW() - INTERVAL '24 hours'
  AND published_at <= NOW();


-- ============================================================
-- 2. Playback Wordcloud 查詢 (processed_chat_messages)
--    受益索引: idx_processed_chat_stream_published
--    模擬 1 小時滑動窗口
-- ============================================================

EXPLAIN ANALYZE
SELECT DISTINCT message_id, unnest(tokens) AS word
FROM processed_chat_messages
WHERE live_stream_id = 'YOUR_VIDEO_ID'
  AND published_at >= NOW() - INTERVAL '2 hours'
  AND published_at < NOW() - INTERVAL '1 hour';


-- ============================================================
-- 3. Super Chat 金額統計 (chat_messages)
--    受益索引: idx_chat_messages_paid (partial index)
--    預期改善: Seq Scan → Index Scan (只掃描 paid_message 行)
-- ============================================================

EXPLAIN ANALYZE
SELECT *
FROM chat_messages
WHERE message_type = 'paid_message'
  AND live_stream_id = 'YOUR_VIDEO_ID'
  AND published_at >= NOW() - INTERVAL '7 days'
  AND published_at <= NOW();

-- 對比：不帶 live_stream_id 的查詢（partial index 仍應生效）
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM chat_messages
WHERE message_type = 'paid_message'
  AND published_at >= NOW() - INTERVAL '7 days';


-- ============================================================
-- 4. ETL 執行記錄查詢 (etl_execution_log)
--    受益索引: idx_etl_log_job_started(job_id, started_at DESC)
--    預期改善: Sort 消除 + 精確 seek
-- ============================================================

EXPLAIN ANALYZE
SELECT id, job_id, job_name, status, trigger_type, started_at,
       completed_at, duration_seconds, records_processed, error_message
FROM etl_execution_log
WHERE job_id = 'process_chat_messages'
ORDER BY started_at DESC
LIMIT 50;

-- 對比：不帶 job_id 過濾（應使用 idx_etl_execution_log_started）
EXPLAIN ANALYZE
SELECT id, job_id, job_name, status, started_at
FROM etl_execution_log
ORDER BY started_at DESC
LIMIT 50;


-- ============================================================
-- 5. 冗餘索引刪除驗證
--    確認 UNIQUE 約束的隱式索引仍然生效
-- ============================================================

-- replace_words: 應使用 UNIQUE 隱式索引，不應 Seq Scan
EXPLAIN ANALYZE
SELECT * FROM replace_words WHERE source_word = '測試詞';

-- special_words: 同上
EXPLAIN ANALYZE
SELECT * FROM special_words WHERE word = '測試詞';

-- meaningless_words: 同上
EXPLAIN ANALYZE
SELECT * FROM meaningless_words WHERE word = '測試詞';


-- ============================================================
-- 6. 索引大小對比（migration 前後各跑一次）
--    確認刪除冗餘索引後磁碟空間有減少
-- ============================================================

SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_indexes
JOIN pg_class ON pg_class.relname = pg_indexes.indexname
JOIN pg_index ON pg_index.indexrelid = pg_class.oid
WHERE tablename IN (
    'processed_chat_messages', 'chat_messages', 'etl_execution_log',
    'meaningless_words', 'replace_words', 'special_words',
    'word_trend_groups', 'prompt_templates'
)
ORDER BY pg_relation_size(indexrelid) DESC;


-- ============================================================
-- 7. 確認無 INVALID 索引
-- ============================================================

-- SELECT indexrelid::regclass AS index_name, indisvalid
-- FROM pg_index
-- WHERE NOT indisvalid;

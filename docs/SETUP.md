# YouTube Live Chat Analyzer Setup Guide

Detailed setup instructions for first-time installation.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [ETL Configuration](#etl-configuration)
- [Initial Setup](#initial-setup)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker | 20.10+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| YouTube Data API Key | - | [Get API Key](https://console.cloud.google.com/apis/library/youtube.googleapis.com) |
| Gemini API Key | - | [Get API Key](https://aistudio.google.com/app/apikey) (for AI word discovery) |

---

## Environment Variables

Copy the example file and configure:

```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | `AIzaSy...` |
| `YOUTUBE_URL` | Target live stream URL | `https://www.youtube.com/watch?v=xxxxx` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL` | `60` | Stats polling interval (seconds) |
| `CHAT_WATCHDOG_TIMEOUT` | `1800` | Restart chat collector if hung (seconds) |
| `POSTGRES_PASSWORD` | `hermes` | Database password |
| `ENABLE_ETL_SCHEDULER` | `true` | Enable built-in ETL scheduler |

---

## ETL Configuration

ETL tasks are managed through the Dashboard Admin panel. No external configuration required.

### Access ETL Management

1. Open Dashboard: http://localhost:3000
2. Navigate to **Admin** (top navigation)
3. Click **ETL Jobs** tab

### Available ETL Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `import_dicts` | Manual | Import base dictionaries from `text_analysis/` folder |
| `process_chat_messages` | Hourly | ETL pipeline (word replacement → emoji extraction → tokenization) |
| `discover_new_words` | Every 3h | AI-powered word discovery using Gemini API |

### ETL Settings

Via **Admin > ETL Jobs > Settings**, you can configure:

| Setting | Description |
|---------|-------------|
| `PROCESS_CHAT_START_TIME` | Start processing from this timestamp |
| `PROCESS_CHAT_BATCH_SIZE` | Number of messages per batch |
| `DISCOVER_NEW_WORDS_ENABLED` | Enable/disable AI discovery |
| `DISCOVER_NEW_WORDS_MIN_CONFIDENCE` | Minimum confidence score for discoveries |

---

## Initial Setup

### Step 1: Start Services

```bash
# Start all services
docker-compose up -d

# Verify all containers are running
docker-compose ps
```

### Step 2: Import Dictionaries (First Time Only)

1. Open Dashboard: http://localhost:3000/admin
2. Go to **ETL Jobs** tab
3. Find `import_dicts` task
4. Click **Trigger** button

This imports base dictionaries from `text_analysis/` folder:
- `special_words.json` → `special_words` table
- `replace_words.json` → `replace_words` table
- `meaningless_words.json` → `meaningless_words` table

### Step 3: Verify ETL is Running

Check the ETL scheduler status:

```bash
curl http://localhost:8000/api/admin/etl/status
```

Expected response:
```json
{
  "scheduler_running": true,
  "jobs_count": 3
}
```

### Step 4: Start Collecting Data

The collector service starts automatically with `docker-compose up`. Verify it's working:

```bash
docker-compose logs -f collector
```

You should see log messages about chat collection starting.

---

## Troubleshooting

### ETL Tasks Not Running

**Solution:** Check if scheduler is enabled:

```bash
# Check scheduler status
curl http://localhost:8000/api/admin/etl/status

# Check environment variable
echo $ENABLE_ETL_SCHEDULER
```

Ensure `ENABLE_ETL_SCHEDULER=true` in your `.env` file.

### AI Discovery Not Working

**Solution:** Verify Gemini API key is set:

1. Check `.env` file has `GEMINI_API_KEY`
2. Restart backend: `docker-compose restart dashboard-backend`

### PostgreSQL Connection Failed

**Solution:** Ensure PostgreSQL container is healthy:

```bash
docker-compose ps postgres
docker-compose logs postgres
```

### View ETL Execution Logs

Via Dashboard:
1. Go to **Admin > ETL Jobs**
2. Click **Logs** tab

Via API:
```bash
curl http://localhost:8000/api/admin/etl/logs
```

---

## Service URLs Summary

| Service | URL | Description |
|---------|-----|-------------|
| Dashboard | http://localhost:3000 | Main UI |
| API Docs (Swagger) | http://localhost:8000/docs | REST API documentation |
| pgAdmin | http://localhost:5050 | Database administration |

---

## Next Steps

1. ✅ Start collecting chat messages (automatic via `collector` service)
2. ✅ Process messages with ETL (automatic via built-in scheduler)
3. 🎯 Review AI-discovered words in Dashboard Admin panel
4. 📊 Explore data in Dashboard or via API

For development commands, see [CLAUDE.md](../CLAUDE.md).

# [DEPRECATED] Airflow ETL Guide

> ⚠️ **This documentation is deprecated.** The project has migrated from Airflow to APScheduler built into the Dashboard Backend. See [MIGRATION_AIRFLOW_TO_APSCHEDULER.md](../MIGRATION_AIRFLOW_TO_APSCHEDULER.md) for details.

---

## Overview

This guide covers the original Airflow-based ETL system. The Airflow DAGs remain in the codebase for reference but are no longer actively used.

## Airflow Services (No Longer Active)

The following services were previously defined in `docker-compose.yml` but are now commented out:

| Service | Port | Description |
|---------|------|-------------|
| Redis | 6379 | Message broker for Celery |
| Airflow Webserver | 8080 | DAG management UI |
| Airflow Scheduler | - | Task scheduling |
| Airflow Worker | - | Celery task execution |
| Airflow Triggerer | - | Deferred task handling |

## DAGs Reference

Located in `airflow/dags/`:

### 1. import_text_analysis_dicts.py

**Purpose**: Load JSON dictionaries into database tables

**Schedule**: Manual only (`schedule_interval=None`)

**Imports**:
- `text_analysis/special_words.json` → `special_words` table
- `text_analysis/replace_words.json` → `replace_words` table
- `text_analysis/meaningless_words.json` → `meaningless_words` table

### 2. process_chat_messages.py

**Purpose**: ETL pipeline for chat messages

**Schedule**: Hourly (`0 * * * *`)

**Pipeline**:
1. Apply word replacements (typos → correct form)
2. Extract Unicode emojis and YouTube emotes
3. Tokenize Chinese text with Jieba

**Airflow Variables**:
- `PROCESS_CHAT_DAG_START_TIME`: ISO timestamp to start processing from
- `PROCESS_CHAT_DAG_RESET`: Set to `true` to reprocess all messages

### 3. discover_new_words.py

**Purpose**: AI-powered word discovery using Gemini API

**Schedule**: Every 3 hours (`0 */3 * * *`)

**Airflow Variables**:
- `GEMINI_API_KEY`: Required for API access
- `DISCOVER_NEW_WORDS_PROMPT`: Custom prompt template (optional)

## Airflow Variables Reference

Variables were set via **Admin → Variables** in the Airflow UI:

| Variable | Used By | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `discover_new_words` | Google Gemini API key |
| `PROCESS_CHAT_DAG_START_TIME` | `process_chat_messages` | Processing start timestamp |
| `DISCOVER_NEW_WORDS_PROMPT` | `discover_new_words` | Custom Gemini prompt |

## PostgreSQL Connection

The connection `postgres_chat_db` was auto-configured via environment variable:

```yaml
AIRFLOW_CONN_POSTGRES_CHAT_DB: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:${POSTGRES_PORT}/${POSTGRES_DB}
```

## Commands (Historical)

These commands are no longer applicable:

```bash
# Access Airflow UI (was at http://localhost:8080)
# Default credentials: airflow/airflow

# Trigger DAG manually
docker-compose exec airflow-scheduler airflow dags trigger <dag_id>

# List all DAGs
docker-compose exec airflow-scheduler airflow dags list

# View scheduler logs
docker-compose logs -f airflow-scheduler
```

---

## Migration to APScheduler

As of February 2026, ETL tasks have been migrated to APScheduler integrated within the Dashboard Backend.

### Benefits of Migration

- ✅ Reduced 3-4 containers (Redis, Webserver, Scheduler, Worker)
- ✅ Lower memory usage (~2-3GB savings)
- ✅ Simplified deployment
- ✅ Unified management via Dashboard UI

### New ETL Management

ETL tasks are now managed via:
- **Dashboard Admin Panel**: http://localhost:3000/admin → ETL Jobs
- **REST API**: `/api/admin/etl/*`

See [SETUP.md](../SETUP.md) for current setup instructions.

# Airflow 遷移至 APScheduler 計劃書

## 📋 專案概述

**目標**: 將現有的 Airflow ETL 遷移至 APScheduler + FastAPI + Dashboard UI 架構，降低資源消耗並簡化維護。

**預期效益**:
- ✅ 減少 3-4 個容器（從 5 個 Airflow 容器 → 0 個）
- ✅ 降低記憶體使用 2-3GB
- ✅ 簡化部署和維護
- ✅ 更好的整合到現有 Dashboard

---

## 🗺️ 遷移策略

### Phase 1: 準備階段（保留 Airflow）
建立新架構，與 Airflow 並行運行以驗證功能

### Phase 2: 測試階段
切換到新系統，Airflow 作為備援

### Phase 3: 完成遷移
移除 Airflow 相關服務

---

## 📦 任務清單

### Phase 1: 基礎建設

- [ ] **Task 1.1** - 建立 ETL Settings 資料表
- [ ] **Task 1.2** - 建立 ETL Scheduler 模組
- [ ] **Task 1.3** - 遷移 ETL 邏輯為獨立函數
- [ ] **Task 1.4** - 建立 FastAPI ETL Jobs Router
- [ ] **Task 1.5** - 建立 Dashboard ETL 管理頁面

### Phase 2: 整合與測試

- [ ] **Task 2.1** - 整合 Scheduler 到 Backend
- [ ] **Task 2.2** - 實作 Settings API 與 UI
- [ ] **Task 2.3** - 測試所有 ETL 任務
- [ ] **Task 2.4** - 並行運行驗證

### Phase 3: 遷移與清理

- [ ] **Task 3.1** - 停用 Airflow DAGs
- [ ] **Task 3.2** - 更新 docker-compose.yml
- [ ] **Task 3.3** - 更新文檔
- [ ] **Task 3.4** - 移除 Airflow 相關檔案

---

## 📝 詳細任務規格

### Task 1.1: 建立 ETL Settings 資料表

**檔案**: `database/migrations/014_create_etl_settings.sql`

**SQL Schema**:
```sql
CREATE TABLE etl_settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    value_type VARCHAR(20) DEFAULT 'string',
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    category VARCHAR(50),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100) DEFAULT 'system'
);

-- 插入預設值
INSERT INTO etl_settings (key, value, value_type, description, category, is_sensitive) VALUES
('GEMINI_API_KEY', '', 'string', 'Google Gemini API 金鑰', 'api', true),
('DISCOVER_NEW_WORDS_PROMPT', '預設提示詞...', 'text', 'AI 分析提示詞範本', 'ai', false),
('PROCESS_CHAT_START_TIME', '2025-01-01T00:00:00', 'datetime', '處理起始時間', 'etl', false),
('PROCESS_CHAT_RESET', 'false', 'boolean', '重置處理表', 'etl', false),
('TRUNCATE_REPLACE_WORDS', 'false', 'boolean', '清空替換詞表', 'import', false),
('TRUNCATE_SPECIAL_WORDS', 'false', 'boolean', '清空特殊詞表', 'import', false);

CREATE INDEX idx_etl_settings_category ON etl_settings(category);
```

**驗收標準**:
- ✅ 表格建立成功
- ✅ 所有預設值正確插入
- ✅ 可透過 pgAdmin 查看

---

### Task 1.2: 建立 ETL Scheduler 模組

**新檔案**: `dashboard/backend/app/etl/scheduler.py`

**核心功能**:
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

def init_scheduler(database_url: str):
    """初始化 APScheduler"""
    global scheduler
    
    jobstores = {
        'default': SQLAlchemyJobStore(url=database_url)
    }
    
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        job_defaults={
            'coalesce': False,
            'max_instances': 1
        }
    )
    
    # 註冊排程任務
    from app.etl.tasks import process_chat_messages, discover_new_words
    
    scheduler.add_job(
        process_chat_messages,
        'cron',
        hour='*',
        id='process_chat',
        name='Process Chat Messages',
        replace_existing=True
    )
    
    scheduler.add_job(
        discover_new_words,
        'cron',
        hour='*/3',
        id='discover_words',
        name='Discover New Words',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ ETL Scheduler started")

def get_scheduler():
    return scheduler

def shutdown_scheduler():
    if scheduler:
        scheduler.shutdown()
```

**注意事項**:
- ⚠️ 使用 BackgroundScheduler（非 BlockingScheduler）
- ⚠️ jobstore 使用 PostgreSQL 持久化（重啟不遺失）
- ⚠️ `max_instances=1` 確保同一任務不重複執行

**驗收標準**:
- ✅ Scheduler 可正常啟動
- ✅ 任務註冊成功
- ✅ 不阻塞 FastAPI 主執行緒

---

### Task 1.3: 遷移 ETL 邏輯為獨立函數

**新檔案結構**:
```
dashboard/backend/app/etl/
├── __init__.py
├── scheduler.py          # Scheduler 初始化
├── config.py            # ETL 設定讀取
├── tasks.py             # 任務入口函數
└── processors/
    ├── chat_processor.py      # 處理聊天訊息邏輯
    ├── word_discovery.py      # AI 發現詞彙邏輯
    └── dict_importer.py       # 字典匯入邏輯
```

**Task 1.3.1**: 建立 `config.py`

```python
import os
from sqlalchemy import create_engine, text
from typing import Any, Optional

class ETLConfig:
    """ETL 設定管理（從資料庫讀取，fallback 到環境變數）"""
    
    _engine = None
    
    @classmethod
    def init_engine(cls, database_url: str):
        cls._engine = create_engine(database_url)
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """讀取設定（DB → ENV → Default）"""
        # 1. 從資料庫讀取
        if cls._engine:
            with cls._engine.connect() as conn:
                result = conn.execute(
                    text("SELECT value, value_type FROM etl_settings WHERE key = :key"),
                    {"key": key}
                ).fetchone()
                
                if result:
                    value, value_type = result
                    return cls._convert_type(value, value_type)
        
        # 2. 從環境變數讀取
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # 3. 使用預設值
        return default
    
    @staticmethod
    def _convert_type(value: str, value_type: str) -> Any:
        """類型轉換"""
        if value_type == 'boolean':
            return value.lower() in ('true', '1', 'yes')
        elif value_type == 'integer':
            return int(value)
        elif value_type == 'float':
            return float(value)
        return value
```

**Task 1.3.2**: 提取核心邏輯到 `processors/`

從 Airflow DAG 提取邏輯，移除 Airflow 依賴：

```python
# processors/chat_processor.py
from app.etl.config import ETLConfig
from sqlalchemy import create_engine
import logging

logger = logging.getLogger(__name__)

def process_chat_messages():
    """處理聊天訊息（原 process_chat_messages.py DAG 邏輯）"""
    logger.info("🔄 Starting process_chat_messages...")
    
    # 從設定讀取
    reset_flag = ETLConfig.get('PROCESS_CHAT_RESET', 'false')
    start_time = ETLConfig.get('PROCESS_CHAT_START_TIME')
    
    # 原 DAG 邏輯...
    # TODO: 從 airflow/dags/process_chat_messages.py 遷移
    
    logger.info("✅ process_chat_messages completed")
```

**注意事項**:
- ⚠️ 移除所有 `from airflow import ...`
- ⚠️ 移除 `Variable.get()` → 改用 `ETLConfig.get()`
- ⚠️ 移除 `PostgresHook` → 改用 `sqlalchemy.create_engine`
- ⚠️ 移除 `context['task_instance'].xcom_push()` → 改用函數回傳值或日誌

**驗收標準**:
- ✅ 所有邏輯可獨立執行（不依賴 Airflow）
- ✅ 設定從 ETLConfig 讀取
- ✅ 單元測試通過

---

### Task 1.4: 建立 FastAPI ETL Jobs Router

**檔案**: `dashboard/backend/app/routers/etl_jobs.py`

**API 端點規格**:

```python
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.etl.scheduler import get_scheduler
from app.etl.tasks import TASK_REGISTRY
from datetime import datetime
from typing import List, Dict

router = APIRouter(prefix="/api/admin/etl", tags=["etl-jobs"])

# GET /api/admin/etl/jobs - 列出所有任務
@router.get("/jobs")
def list_jobs() -> Dict:
    """列出所有排程任務與手動任務"""
    scheduler = get_scheduler()
    
    scheduled_jobs = []
    for job in scheduler.get_jobs():
        scheduled_jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
            'is_paused': job.next_run_time is None
        })
    
    manual_jobs = [
        {'id': 'import_dicts', 'name': 'Import Dictionaries', 'type': 'manual'}
    ]
    
    return {
        'scheduled': scheduled_jobs,
        'manual': manual_jobs
    }

# POST /api/admin/etl/jobs/{job_name}/trigger - 手動觸發
@router.post("/jobs/{job_name}/trigger")
def trigger_job(job_name: str, background_tasks: BackgroundTasks):
    """手動觸發任務（背景執行）"""
    if job_name not in TASK_REGISTRY:
        raise HTTPException(404, f"Task '{job_name}' not found")
    
    task_func = TASK_REGISTRY[job_name]
    background_tasks.add_task(task_func)
    
    return {
        'status': 'triggered',
        'job': job_name,
        'triggered_at': datetime.now().isoformat()
    }

# POST /api/admin/etl/jobs/{job_id}/pause - 暫停
# POST /api/admin/etl/jobs/{job_id}/resume - 恢復
# ... (其他端點)
```

**驗收標準**:
- ✅ 所有端點正常運作
- ✅ Swagger 文檔正確
- ✅ 錯誤處理完善

---

### Task 1.5: 建立 Dashboard ETL 管理頁面

**檔案**: `dashboard/frontend/src/features/admin/ETLJobsPage.jsx`

**UI 規格**:

```
┌─────────────────────────────────────────────────────┐
│ ETL 任務管理                                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 📋 手動任務                                         │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 匯入字典                                        │ │
│ │ 將 text_analysis/ 字典檔匯入資料庫              │ │
│ │                              [🔄 執行任務]      │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ⏰ 排程任務                                         │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 處理聊天訊息          下次執行: 14:00          │ │
│ │ 每小時執行一次                                  │ │
│ │        [⚡立即執行] [⏸️暫停] [查看日誌]         │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ 發現新詞彙            下次執行: 15:00          │ │
│ │ 每 3 小時執行一次                               │ │
│ │        [⚡立即執行] [⏸️暫停] [查看日誌]         │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**核心功能**:
- 顯示所有排程任務與下次執行時間
- 一鍵手動觸發任務
- 暫停/恢復排程
- 即時更新狀態（每 5 秒輪詢）

**驗收標準**:
- ✅ UI 美觀直觀
- ✅ 所有按鈕功能正常
- ✅ 即時顯示任務狀態

---

## ⚠️ 重要注意事項

### 資料庫連線
- APScheduler 與 FastAPI 共用同一個資料庫
- 需要初始化兩個 engine（scheduler jobstore + ETLConfig）

### 錯誤處理
- 所有 ETL 任務需要 try-except 包裹
- 錯誤需記錄到日誌表（新增 `etl_execution_log`）

### 環境變數優先級
1. 資料庫 `etl_settings` (可透過 UI 修改)
2. `.env` 環境變數
3. 程式碼預設值

### 敏感資訊
- `GEMINI_API_KEY` 優先從 `.env` 讀取
- Dashboard UI 顯示時需遮蔽

---

## 📊 驗收檢查表

### Phase 1 完成標準
- [ ] 所有 5 個任務完成
- [ ] ETL 邏輯可獨立執行
- [ ] Dashboard 可手動觸發任務
- [ ] 設定可透過 UI 管理

### Phase 2 完成標準
- [ ] 新舊系統並行運行一週無誤
- [ ] 所有 ETL 任務產出一致
- [ ] 效能無明顯下降

### Phase 3 完成標準
- [ ] Airflow 容器已移除
- [ ] `docker-compose.yml` 已更新
- [ ] README 與 SETUP.md 已更新
- [ ] 舊 Airflow 檔案已歸檔

---

## 🔗 相關檔案

### 需要修改
- `dashboard/backend/app/main.py` - 整合 scheduler
- `docker-compose.yml` - 移除 Airflow 服務
- `README.md` - 更新架構說明

### 需要新增
- `database/migrations/014_create_etl_settings.sql`
- `dashboard/backend/app/etl/` - 整個目錄
- `dashboard/frontend/src/features/admin/ETLJobsPage.jsx`
- `dashboard/frontend/src/features/admin/ETLSettingsPage.jsx`

### 需要保留（參考用）
- `airflow/dags/` - 保留作為邏輯參考，標記為 deprecated

---

## 📅 預估時程

| Phase | 預估時間 | 備註 |
|-------|---------|------|
| Phase 1 | 3-4 天 | 建立新架構 |
| Phase 2 | 2-3 天 | 測試與驗證 |
| Phase 3 | 1 天 | 清理與文檔 |
| **總計** | **6-8 天** | 不含緩衝時間 |

---

## 🎯 成功指標

1. ✅ Docker 記憶體使用降低 > 2GB
2. ✅ 容器數量減少 3-4 個
3. ✅ ETL 任務執行成功率 = 100%
4. ✅ 所有功能與 Airflow 版本一致
5. ✅ 可透過 Dashboard 管理所有 ETL 設定

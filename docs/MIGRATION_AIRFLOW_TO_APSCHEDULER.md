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

- [x] **Task 1.1** - 建立 ETL Settings 資料表
  > ✅ 完成於 2026-02-03
  > 建立 `database/init/13_create_etl_settings.sql`（修正檔名為 13，因為 12 已存在）
  > 包含 `etl_settings` 和 `etl_execution_log` 兩個表

- [x] **Task 1.2** - 建立 ETL Scheduler 模組
  > ✅ 完成於 2026-02-03
  > 建立 `dashboard/backend/app/etl/scheduler.py`
  > 使用 BackgroundScheduler + SQLAlchemyJobStore

- [x] **Task 1.3** - 遷移 ETL 邏輯為獨立函數
  > ✅ 完成於 2026-02-03
  > 建立完整的 `dashboard/backend/app/etl/` 目錄結構：
  > - `__init__.py` - 模組匯出
  > - `config.py` - ETLConfig 設定管理類別
  > - `scheduler.py` - APScheduler 管理
  > - `tasks.py` - 任務入口和註冊表
  > - `processors/text_processor.py` - 文字處理邏輯
  > - `processors/chat_processor.py` - ChatProcessor 類別
  > - `processors/word_discovery.py` - WordDiscoveryProcessor 類別
  > - `processors/dict_importer.py` - DictImporter 類別

- [x] **Task 1.4** - 建立 FastAPI ETL Jobs Router
  > ✅ 完成於 2026-02-03
  > 建立 `dashboard/backend/app/routers/etl_jobs.py`
  > 包含：列出任務、觸發、暫停、恢復、執行記錄、設定管理等 API

- [x] **Task 1.5** - 建立 Dashboard ETL 管理頁面
  > ✅ 完成於 2026-02-03
  > 建立 `dashboard/frontend/src/features/admin/ETLJobsManager.jsx`
  > 建立 `dashboard/frontend/src/api/etl.js`
  > 修改 `AdminPanel.jsx` 加入 ETL Jobs 標籤頁

### Phase 2: 整合與測試

- [x] **Task 2.1** - 整合 Scheduler 到 Backend
  > ✅ 完成於 2026-02-03
  > 修改 `dashboard/backend/main.py`：
  > - 使用 FastAPI lifespan 處理啟動/關閉
  > - 加入 ETL scheduler 初始化
  > - 支援 `ENABLE_ETL_SCHEDULER` 環境變數控制

- [x] **Task 2.2** - 實作 Settings API 與 UI
  > ✅ 完成於 2026-02-03
  > ETL Settings API 已整合在 `etl_jobs.py` router 中
  > 修改 `docker-compose.yml` 加入環境變數和 text_analysis 掛載

- [ ] **Task 2.3** - 測試所有 ETL 任務
- [ ] **Task 2.4** - 並行運行驗證

### Phase 3: 遷移與清理

- [ ] **Task 3.1** - 停用 Airflow DAGs
- [ ] **Task 3.2** - 更新 docker-compose.yml
- [ ] **Task 3.3** - 更新文檔
- [ ] **Task 3.4** - 移除 Airflow 相關檔案

---

## 📝 實作摘要

### 已建立的檔案

#### 資料庫
- `database/init/13_create_etl_settings.sql` - ETL 設定表和執行日誌表

#### 後端 ETL 模組
```
dashboard/backend/app/etl/
├── __init__.py              # 模組匯出
├── config.py                # ETLConfig 設定管理（DB → ENV → Default）
├── scheduler.py             # APScheduler 管理
├── tasks.py                 # 任務入口函數和 TASK_REGISTRY
└── processors/
    ├── __init__.py
    ├── text_processor.py    # 文字處理（jieba 斷詞、emoji 提取等）
    ├── chat_processor.py    # ChatProcessor 類別（處理聊天訊息）
    ├── word_discovery.py    # WordDiscoveryProcessor 類別（AI 詞彙發現）
    └── dict_importer.py     # DictImporter 類別（字典匯入）
```

#### 後端 API
- `dashboard/backend/app/routers/etl_jobs.py` - ETL 任務管理 API

#### 前端
- `dashboard/frontend/src/api/etl.js` - ETL API 客戶端
- `dashboard/frontend/src/features/admin/ETLJobsManager.jsx` - ETL 管理頁面元件（含 Jobs/Settings 子標籤）
- `dashboard/frontend/src/features/admin/ETLSettingsManager.jsx` - ETL 設定管理元件

### 已修改的檔案

- `dashboard/backend/requirements.txt` - 加入 apscheduler, jieba, google-generativeai
- `dashboard/backend/main.py` - 整合 ETL scheduler 和新 router
- `dashboard/frontend/src/features/admin/AdminPanel.jsx` - 加入 ETL Jobs 標籤頁
- `docker-compose.yml` - 加入環境變數和 text_analysis 目錄掛載

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

### 新增的環境變數
```bash
# 在 .env 中加入（敏感資訊，不可在 Dashboard 設定）
ENABLE_ETL_SCHEDULER=true  # 是否啟用 ETL 排程器
GEMINI_API_KEY=xxx         # Gemini API 金鑰（用於 AI 詞彙發現）
```

### 設定優先級
| 設定類型 | 優先級 | 說明 |
|---------|--------|------|
| 敏感設定 (API Key) | ENV → DB → Default | 優先從 `.env` 讀取 |
| 一般設定 | DB → ENV → Default | 優先從 Dashboard UI 讀取 |

### Dashboard 可調整的設定
訪問 **Admin > ETL Jobs > Settings** 可以調整：
- `PROCESS_CHAT_START_TIME` - 處理起始時間
- `PROCESS_CHAT_BATCH_SIZE` - 批次大小
- `PROCESS_CHAT_RESET` - 重置處理表
- `DISCOVER_NEW_WORDS_ENABLED` - 啟用 AI 發現
- `DISCOVER_NEW_WORDS_MIN_CONFIDENCE` - 最低信心分數
- `DISCOVER_NEW_WORDS_BATCH_SIZE` - AI 分析批次大小
- `TRUNCATE_*` - 字典匯入時的清空選項

---

## 📊 驗收檢查表

### Phase 1 完成標準
- [x] 所有 5 個任務完成
- [x] ETL 邏輯可獨立執行
- [x] Dashboard 可手動觸發任務
- [x] 設定可透過 UI 管理

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

### 已修改
- `dashboard/backend/app/main.py` - 整合 scheduler ✅
- `dashboard/backend/requirements.txt` - 加入新依賴 ✅
- `dashboard/frontend/src/features/admin/AdminPanel.jsx` - 加入 ETL 標籤 ✅
- `docker-compose.yml` - 加入環境變數和掛載 ✅

### 已新增
- `database/init/13_create_etl_settings.sql` ✅
- `dashboard/backend/app/etl/` - 整個目錄 ✅
- `dashboard/backend/app/routers/etl_jobs.py` ✅
- `dashboard/frontend/src/features/admin/ETLJobsManager.jsx` ✅
- `dashboard/frontend/src/features/admin/ETLSettingsManager.jsx` ✅
- `dashboard/frontend/src/api/etl.js` ✅

### 需要保留（參考用）
- `airflow/dags/` - 保留作為邏輯參考，標記為 deprecated

---

## 📅 預估時程

| Phase | 預估時間 | 狀態 | 備註 |
|-------|---------|------|------|
| Phase 1 | 3-4 天 | ✅ 完成 | 建立新架構 |
| Phase 2 | 2-3 天 | 🔄 進行中 | 測試與驗證 |
| Phase 3 | 1 天 | ⏳ 待開始 | 清理與文檔 |
| **總計** | **6-8 天** | | 不含緩衝時間 |

---

## 🎯 成功指標

1. ✅ Docker 記憶體使用降低 > 2GB
2. ✅ 容器數量減少 3-4 個
3. ✅ ETL 任務執行成功率 = 100%
4. ✅ 所有功能與 Airflow 版本一致
5. ✅ 可透過 Dashboard 管理所有 ETL 設定

---

## 🧪 測試指南

### 測試步驟

1. **重建後端容器**
   ```bash
   docker-compose up -d --build dashboard-backend
   ```

2. **檢查排程器狀態**
   ```bash
   curl http://localhost:8000/api/admin/etl/status
   ```

3. **查看所有任務**
   ```bash
   curl http://localhost:8000/api/admin/etl/jobs
   ```

4. **手動觸發任務**
   ```bash
   curl -X POST http://localhost:8000/api/admin/etl/jobs/import_dicts/trigger
   curl -X POST http://localhost:8000/api/admin/etl/jobs/process_chat_messages/trigger
   ```

5. **查看執行記錄**
   ```bash
   curl http://localhost:8000/api/admin/etl/logs
   ```

6. **透過 Dashboard UI 測試**
   - 訪問 http://localhost:3000/admin
   - 點擊 "ETL Jobs" 標籤
   - 測試手動觸發、暫停、恢復功能

---

## 📝 後續工作

### Phase 2 待完成
1. 執行完整的 ETL 任務測試
2. 比對新舊系統的輸出結果
3. 監控一週的並行運行

### Phase 3 待完成
1. 停用 Airflow DAGs
2. 更新 docker-compose.yml 移除 Airflow 相關服務
3. 更新 README.md 和 SETUP.md
4. 移除或歸檔 airflow/ 目錄

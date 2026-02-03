"""
ETL Module
ETL 任務模組，取代 Airflow DAGs

包含：
- scheduler: APScheduler 排程管理
- config: ETL 設定管理
- tasks: 任務入口函數
- processors/: 核心處理邏輯
"""

from .scheduler import init_scheduler, get_scheduler, shutdown_scheduler
from .config import ETLConfig

__all__ = [
    'init_scheduler',
    'get_scheduler',
    'shutdown_scheduler',
    'ETLConfig',
]

"""
ETL Tasks Module
ETL 任務入口函數
"""

import logging
from datetime import datetime
from typing import Dict, Any, Callable

from sqlalchemy import text

from app.etl.config import ETLConfig

logger = logging.getLogger(__name__)


def log_execution(job_id: str, job_name: str, result: Dict[str, Any]):
    """
    記錄任務執行結果到 etl_execution_log

    Args:
        job_id: 任務 ID
        job_name: 任務名稱
        result: 執行結果
    """
    engine = ETLConfig.get_engine()
    if not engine:
        logger.warning("Cannot log execution: database engine not initialized")
        return

    try:
        import json
        with engine.connect() as conn:
            # Clean error message - remove problematic characters
            error_msg = result.get('error')
            if error_msg:
                # Truncate long error messages and escape quotes
                error_msg = str(error_msg)[:500]
            
            conn.execute(
                text("""
                    INSERT INTO etl_execution_log
                        (job_id, job_name, status, started_at, completed_at,
                         duration_seconds, records_processed, error_message, metadata)
                    VALUES
                        (:job_id, :job_name, :status, :started_at, :completed_at,
                         :duration, :records, :error, :metadata)
                """),
                {
                    "job_id": job_id,
                    "job_name": job_name,
                    "status": result.get('status', 'unknown'),
                    "started_at": result.get('started_at', datetime.now()),
                    "completed_at": datetime.now(),
                    "duration": result.get('execution_time_seconds', 0),
                    "records": result.get('total_processed', 0),
                    "error": error_msg,
                    "metadata": json.dumps({})
                }
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log execution: {e}")


def run_process_chat_messages() -> Dict[str, Any]:
    """
    執行處理聊天訊息任務

    排程時間：每小時執行
    """
    logger.info("=" * 60)
    logger.info("Running scheduled task: process_chat_messages")
    logger.info("=" * 60)

    try:
        from app.etl.processors.chat_processor import ChatProcessor

        processor = ChatProcessor()
        result = processor.run()

        log_execution('process_chat_messages', '處理聊天訊息', result)

        return result
    except Exception as e:
        logger.error(f"process_chat_messages failed: {e}")
        result = {'status': 'failed', 'error': str(e)}
        log_execution('process_chat_messages', '處理聊天訊息', result)
        return result


def run_discover_new_words() -> Dict[str, Any]:
    """
    執行 AI 詞彙發現任務

    排程時間：每 3 小時執行
    """
    logger.info("=" * 60)
    logger.info("Running scheduled task: discover_new_words")
    logger.info("=" * 60)

    try:
        from app.etl.processors.word_discovery import WordDiscoveryProcessor

        processor = WordDiscoveryProcessor()
        result = processor.run()

        log_execution('discover_new_words', 'AI 詞彙發現', result)

        return result
    except Exception as e:
        logger.error(f"discover_new_words failed: {e}")
        result = {'status': 'failed', 'error': str(e)}
        log_execution('discover_new_words', 'AI 詞彙發現', result)
        return result


def run_import_dicts() -> Dict[str, Any]:
    """
    執行字典匯入任務

    手動觸發
    """
    logger.info("=" * 60)
    logger.info("Running manual task: import_dicts")
    logger.info("=" * 60)

    try:
        from app.etl.processors.dict_importer import DictImporter

        importer = DictImporter()
        result = importer.run()

        log_execution('import_dicts', '匯入字典', result)

        return result
    except Exception as e:
        logger.error(f"import_dicts failed: {e}")
        result = {'status': 'failed', 'error': str(e)}
        log_execution('import_dicts', '匯入字典', result)
        return result


# 任務註冊表（用於 API 手動觸發）
TASK_REGISTRY: Dict[str, Callable[[], Dict[str, Any]]] = {
    'process_chat_messages': run_process_chat_messages,
    'discover_new_words': run_discover_new_words,
    'import_dicts': run_import_dicts,
}

# 手動任務列表（不在排程中，只能手動觸發）
MANUAL_TASKS = [
    {
        'id': 'import_dicts',
        'name': '匯入字典',
        'description': '將 text_analysis/ 目錄下的字典檔匯入資料庫',
        'type': 'manual'
    }
]

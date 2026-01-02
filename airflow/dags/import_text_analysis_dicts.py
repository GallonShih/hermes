"""
Airflow DAG: Import Text Analysis Dictionaries
導入文字分析所需的字典資料到 PostgreSQL

此 DAG 會讀取以下檔案並導入到資料庫：
- meaningless_words.json -> meaningless_words table
- replace_words.json -> replace_words table
- special_words.json -> special_words table

執行方式：手動觸發（schedule_interval=None）
"""

from datetime import datetime
from pathlib import Path
import json

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

# 默認參數
default_args = {
    'owner': 'hermes',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 2),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

# DAG 定義
dag = DAG(
    'import_text_analysis_dicts',
    default_args=default_args,
    description='Import text analysis dictionaries to PostgreSQL',
    schedule_interval=None,  # 手動觸發
    catchup=False,
    tags=['text-analysis', 'import', 'manual'],
)


def create_tables_if_not_exists(**context):
    """
    創建文字分析相關的資料表（如果不存在）
    """
    # 獲取資料庫連接
    pg_hook = PostgresHook(postgres_conn_id='postgres_hermes')

    # 創建表的 SQL
    create_tables_sql = """
    -- 無意義詞彙表
    CREATE TABLE IF NOT EXISTS meaningless_words (
        id SERIAL PRIMARY KEY,
        word VARCHAR(255) NOT NULL UNIQUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 替換詞彙表 (key-value mapping)
    CREATE TABLE IF NOT EXISTS replace_words (
        id SERIAL PRIMARY KEY,
        source_word VARCHAR(255) NOT NULL UNIQUE,
        target_word VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 特殊詞彙表
    CREATE TABLE IF NOT EXISTS special_words (
        id SERIAL PRIMARY KEY,
        word VARCHAR(255) NOT NULL UNIQUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- 創建索引以提升查詢效能
    CREATE INDEX IF NOT EXISTS idx_meaningless_words_word ON meaningless_words(word);
    CREATE INDEX IF NOT EXISTS idx_replace_words_source ON replace_words(source_word);
    CREATE INDEX IF NOT EXISTS idx_replace_words_target ON replace_words(target_word);
    CREATE INDEX IF NOT EXISTS idx_special_words_word ON special_words(word);
    """

    # 執行 SQL
    pg_hook.run(create_tables_sql)

    print("=" * 60)
    print("Tables created or already exist:")
    print("  - meaningless_words")
    print("  - replace_words")
    print("  - special_words")
    print("=" * 60)

    # 檢查表是否存在並返回資訊
    check_sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('meaningless_words', 'replace_words', 'special_words')
        ORDER BY table_name;
    """

    tables = pg_hook.get_records(check_sql)
    table_names = [table[0] for table in tables]

    print(f"Confirmed tables exist: {table_names}")

    return {
        'tables_created': table_names,
        'count': len(table_names)
    }


def import_meaningless_words(**context):
    """
    導入無意義詞彙
    """
    # 讀取 JSON 檔案
    json_file = Path('/opt/airflow/text_analysis/meaningless_words.json')

    if not json_file.exists():
        raise FileNotFoundError(f"File not found: {json_file}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = data.get('meaningless_words', [])

    # 獲取資料庫連接
    pg_hook = PostgresHook(postgres_conn_id='postgres_hermes')

    # 使用 INSERT ... ON CONFLICT DO NOTHING 來避免重複
    insert_sql = """
        INSERT INTO meaningless_words (word)
        VALUES (%s)
        ON CONFLICT (word) DO NOTHING;
    """

    # 批次插入
    inserted_count = 0
    for word in words:
        pg_hook.run(insert_sql, parameters=(word,))
        inserted_count += 1

    print(f"Processed {inserted_count} meaningless words")

    # 查詢總數
    count_sql = "SELECT COUNT(*) FROM meaningless_words;"
    result = pg_hook.get_first(count_sql)
    total_count = result[0] if result else 0

    print(f"Total meaningless words in database: {total_count}")

    return {
        'processed': inserted_count,
        'total': total_count
    }


def import_replace_words(**context):
    """
    導入替換詞彙對照表
    """
    # 讀取 JSON 檔案
    json_file = Path('/opt/airflow/text_analysis/replace_words.json')

    if not json_file.exists():
        raise FileNotFoundError(f"File not found: {json_file}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    replace_map = data.get('replace_words', {})

    # 獲取資料庫連接
    pg_hook = PostgresHook(postgres_conn_id='postgres_hermes')

    # 使用 INSERT ... ON CONFLICT DO UPDATE 來更新或插入
    upsert_sql = """
        INSERT INTO replace_words (source_word, target_word)
        VALUES (%s, %s)
        ON CONFLICT (source_word)
        DO UPDATE SET
            target_word = EXCLUDED.target_word,
            updated_at = NOW();
    """

    # 批次插入/更新
    processed_count = 0
    for source, target in replace_map.items():
        pg_hook.run(upsert_sql, parameters=(source, target))
        processed_count += 1

    print(f"Processed {processed_count} replace word mappings")

    # 查詢總數
    count_sql = "SELECT COUNT(*) FROM replace_words;"
    result = pg_hook.get_first(count_sql)
    total_count = result[0] if result else 0

    print(f"Total replace words in database: {total_count}")

    return {
        'processed': processed_count,
        'total': total_count
    }


def import_special_words(**context):
    """
    導入特殊詞彙
    """
    # 讀取 JSON 檔案
    json_file = Path('/opt/airflow/text_analysis/special_words.json')

    if not json_file.exists():
        raise FileNotFoundError(f"File not found: {json_file}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = data.get('special_words', [])

    # 獲取資料庫連接
    pg_hook = PostgresHook(postgres_conn_id='postgres_hermes')

    # 使用 INSERT ... ON CONFLICT DO NOTHING 來避免重複
    insert_sql = """
        INSERT INTO special_words (word)
        VALUES (%s)
        ON CONFLICT (word) DO NOTHING;
    """

    # 批次插入
    inserted_count = 0
    for word in words:
        pg_hook.run(insert_sql, parameters=(word,))
        inserted_count += 1

    print(f"Processed {inserted_count} special words")

    # 查詢總數
    count_sql = "SELECT COUNT(*) FROM special_words;"
    result = pg_hook.get_first(count_sql)
    total_count = result[0] if result else 0

    print(f"Total special words in database: {total_count}")

    return {
        'processed': inserted_count,
        'total': total_count
    }


def verify_import(**context):
    """
    驗證導入結果
    """
    # 從 XCom 獲取各個任務的結果
    meaningless_result = context['task_instance'].xcom_pull(task_ids='import_meaningless_words')
    replace_result = context['task_instance'].xcom_pull(task_ids='import_replace_words')
    special_result = context['task_instance'].xcom_pull(task_ids='import_special_words')

    summary = {
        'meaningless_words': meaningless_result,
        'replace_words': replace_result,
        'special_words': special_result,
        'timestamp': datetime.now().isoformat()
    }

    print("=" * 60)
    print("Import Summary:")
    print("=" * 60)
    print(f"Meaningless Words - Processed: {meaningless_result['processed']}, Total: {meaningless_result['total']}")
    print(f"Replace Words     - Processed: {replace_result['processed']}, Total: {replace_result['total']}")
    print(f"Special Words     - Processed: {special_result['processed']}, Total: {special_result['total']}")
    print("=" * 60)

    return summary


# Task 0: 創建表（如果不存在）
task_create_tables = PythonOperator(
    task_id='create_tables_if_not_exists',
    python_callable=create_tables_if_not_exists,
    dag=dag,
)

# Task 1: 導入無意義詞彙
task_import_meaningless = PythonOperator(
    task_id='import_meaningless_words',
    python_callable=import_meaningless_words,
    dag=dag,
)

# Task 2: 導入替換詞彙
task_import_replace = PythonOperator(
    task_id='import_replace_words',
    python_callable=import_replace_words,
    dag=dag,
)

# Task 3: 導入特殊詞彙
task_import_special = PythonOperator(
    task_id='import_special_words',
    python_callable=import_special_words,
    dag=dag,
)

# Task 4: 驗證導入結果
task_verify = PythonOperator(
    task_id='verify_import',
    python_callable=verify_import,
    dag=dag,
)

# 定義任務依賴
# 1. 先創建表
# 2. 表創建完成後，三個導入任務並行執行
# 3. 所有導入任務完成後，執行驗證
task_create_tables >> [task_import_meaningless, task_import_replace, task_import_special] >> task_verify

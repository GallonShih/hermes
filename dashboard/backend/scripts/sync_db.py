#!/usr/bin/env python3
"""
DB Sync Script
==============
在兩個 PostgreSQL 資料庫之間，以時間範圍批次同步指定資料表的資料。
PK 重複時略過（ON CONFLICT DO NOTHING）。

使用方式（時間範圍）：
    python sync_db.py \\
        --source-url "postgresql://user:pass@host:5432/dbname" \\
        --target-url "postgresql://user:pass@host:5432/dbname" \\
        --table chat_messages \\
        --start "2025-01-01T00:00:00+00:00" \\
        --end   "2025-01-02T00:00:00+00:00"

使用方式（全表同步，適合無時間欄位的資料表）：
    python sync_db.py \\
        --source-url "postgresql://user:pass@host:5432/dbname" \\
        --target-url "postgresql://user:pass@host:5432/dbname" \\
        --table replace_words \\
        --all

選用參數：
    --time-column   指定時間過濾欄位（預設自動判斷）
    --batch-size    每批次筆數（預設 1000）
    --dry-run       只計算筆數，不實際寫入
    --verbose       顯示詳細進度

需要：psycopg2-binary（已在 requirements.txt 內）

支援的資料表及預設時間欄位：
    chat_messages           → published_at
    processed_chat_messages → published_at
    live_streams            → actual_start_time
    其他資料表              → created_at（自動偵測）

不支援的資料表（SERIAL PK，需額外處理）：
    stream_stats

分頁策略：
    使用 Keyset Pagination（游標分頁），以 (time_col, pk_col) 作為游標，
    避免 LIMIT/OFFSET 在時間戳重複時漏資料。
    僅支援單欄 PK 的資料表。

連線管理：
    - connect_timeout=30s，避免連線 hang 住
    - 遇到 OperationalError / InterfaceError 時自動重連，最多 5 次
    - 重連間隔 10s

同步策略（--pk-first）：
    預設策略（chunked pre-filter）：
        每個 chunk 從 source 批次拉完整資料，pre-filter 掉 target 已有的 PK。
        適合重複率低、或 source 為本地的情境。

    PK-first 策略（--pk-first）：
        每個 chunk 先比對 source / target 的 PK 差集，只拉真正缺少的完整資料。
        適合重複率高（>90%）、source 為遠端的情境（大幅減少網路傳輸）。
"""

import argparse
import sys
import datetime
import time
from typing import Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not found. Install with: pip install psycopg2-binary")
    sys.exit(1)


# ── 各資料表預設時間欄位 ──────────────────────────────────────────────────────

TABLE_TIME_COLUMNS = {
    "chat_messages": "published_at",
    "processed_chat_messages": "published_at",
    "live_streams": "actual_start_time",
    "etl_execution_log": "started_at",
    "word_analysis_log": "created_at",
}

# ── 各資料表自訂衝突欄位（SERIAL PK 將自動排除出 INSERT）────────────────────
# 適用於 id 由兩端各自產生、以業務欄位作為唯一識別的資料表
TABLE_CONFLICT_COLUMNS: dict[str, str] = {
    "word_trend_groups": "name",
    "replace_words": "source_word",
    "special_words": "word",
}

# SERIAL PK 的資料表目前不支援同步（sequence 不同步問題需額外處理）
UNSUPPORTED_TABLES = {"stream_stats"}

DEFAULT_TIME_COLUMN = "created_at"

# ── 連線與重連設定 ────────────────────────────────────────────────────────────

CONNECT_TIMEOUT = 30    # seconds – psycopg2 connect timeout
MAX_RECONNECT   = 5     # max reconnect attempts on connection drop
RECONNECT_WAIT  = 10    # seconds between reconnect attempts


# ── 連線管理 ──────────────────────────────────────────────────────────────────

def connect_source(url: str):
    """Connect to source DB (read-only) with timeout."""
    conn = psycopg2.connect(url, connect_timeout=CONNECT_TIMEOUT)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def connect_target(url: str):
    """Connect to target DB with timeout."""
    return psycopg2.connect(url, connect_timeout=CONNECT_TIMEOUT)


def with_retry(fn, reconnect_fn, label: str = ""):
    """
    Execute fn(), reconnecting and retrying on psycopg2 connection errors.
    reconnect_fn() is called to refresh the broken connection before each retry.
    """
    for attempt in range(1, MAX_RECONNECT + 1):
        try:
            return fn()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if attempt < MAX_RECONNECT:
                tag = f" ({label})" if label else ""
                print(
                    f"\n  [WARN] Connection lost{tag}: {e}"
                    f"\n  [RECONNECT] Attempt {attempt}/{MAX_RECONNECT - 1}, "
                    f"waiting {RECONNECT_WAIT}s..."
                )
                time.sleep(RECONNECT_WAIT)
                reconnect_fn()
                print("  [RECONNECT] OK")
            else:
                raise


# ── 資料庫 introspection ──────────────────────────────────────────────────────

def get_columns(conn, table_name: str) -> list[str]:
    """取得資料表所有欄位名稱（依原始順序）"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        rows = cur.fetchall()
    if not rows:
        raise ValueError(f"Table '{table_name}' not found in public schema.")
    return [r[0] for r in rows]


def get_primary_keys(conn, table_name: str) -> list[str]:
    """取得資料表 PK 欄位清單"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
               AND tc.table_schema    = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema    = 'public'
              AND tc.table_name      = %s
            ORDER BY kcu.ordinal_position
            """,
            (table_name,),
        )
        rows = cur.fetchall()
    if not rows:
        raise ValueError(f"No primary key found for table '{table_name}'.")
    return [r[0] for r in rows]


def get_json_columns(conn, table_name: str) -> dict[str, str]:
    """
    找出 JSON / JSONB 欄位，回傳 {column_name: data_type}。
    兩種型別讀取時都需要 ::text cast，寫入時用對應的 ::json / ::jsonb cast。
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = %s
              AND data_type    IN ('json', 'jsonb')
            """,
            (table_name,),
        )
        rows = cur.fetchall()
    return {r[0]: r[1] for r in rows}


def get_serial_columns(conn, table_name: str) -> set[str]:
    """找出使用 SERIAL / GENERATED 的欄位（供後續判斷是否需要 OVERRIDING）"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = %s
              AND (
                  column_default LIKE 'nextval(%%'
                  OR is_identity = 'YES'
              )
            """,
            (table_name,),
        )
        rows = cur.fetchall()
    return {r[0] for r in rows}


def detect_time_column(table_name: str, columns: list[str]) -> str:
    """自動偵測時間過濾欄位"""
    if table_name in TABLE_TIME_COLUMNS:
        col = TABLE_TIME_COLUMNS[table_name]
        if col in columns:
            return col
    if DEFAULT_TIME_COLUMN in columns:
        return DEFAULT_TIME_COLUMN
    # 最後嘗試常見名稱
    for candidate in ("updated_at", "published_at", "collected_at", "started_at"):
        if candidate in columns:
            return candidate
    raise ValueError(
        f"Cannot detect time column for table '{table_name}'. "
        f"Use --time-column to specify one. Available columns: {columns}"
    )


# ── 查詢 ──────────────────────────────────────────────────────────────────────

def count_rows(
    conn,
    table_name: str,
    time_col: str,
    start: datetime.datetime,
    end: datetime.datetime,
) -> int:
    """計算來源資料列數（時間範圍模式）"""
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE "{time_col}" >= %s AND "{time_col}" < %s',
            (start, end),
        )
        return cur.fetchone()[0]


def count_all_rows(conn, table_name: str) -> int:
    """計算來源資料列數（全表模式）"""
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        return cur.fetchone()[0]


def fetch_batch_keyset(
    conn,
    table_name: str,
    columns: list[str],
    json_cols: dict[str, str],
    time_col: str,
    pk_col: str,
    start: datetime.datetime,
    end: datetime.datetime,
    cursor_time: Optional[datetime.datetime],
    cursor_pk,
    batch_size: int,
) -> list[tuple]:
    """
    Keyset Pagination 取資料。

    使用 (time_col, pk_col) 作為游標，確保時間戳相同時不漏資料。
    游標邏輯：下一批 = time_col > cursor_time
                    OR (time_col = cursor_time AND pk_col > cursor_pk)

    JSONB 欄位以 ::text 讀出，保留 JSON null（"null" 字串）
    與 SQL NULL（Python None）的區別，供寫入時正確還原。
    """
    # JSONB 欄位 cast 成 text，其餘保持原型別
    col_list = ", ".join(
        f'"{c}"::text AS "{c}"' if c in json_cols else f'"{c}"'
        for c in columns
    )

    if cursor_time is None:
        # 第一批：從 start 開始
        sql = f"""
            SELECT {col_list}
            FROM "{table_name}"
            WHERE "{time_col}" >= %s AND "{time_col}" < %s
            ORDER BY "{time_col}", "{pk_col}"
            LIMIT %s
        """
        params = (start, end, batch_size)
    else:
        # 後續批次：以游標接續，不需要 OFFSET
        sql = f"""
            SELECT {col_list}
            FROM "{table_name}"
            WHERE "{time_col}" < %s
              AND (
                  "{time_col}" > %s
                  OR ("{time_col}" = %s AND "{pk_col}" > %s)
              )
            ORDER BY "{time_col}", "{pk_col}"
            LIMIT %s
        """
        params = (end, cursor_time, cursor_time, cursor_pk, batch_size)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_batch_keyset_all(
    conn,
    table_name: str,
    columns: list[str],
    json_cols: dict[str, str],
    pk_col: str,
    cursor_pk,
    batch_size: int,
) -> list[tuple]:
    """
    全表 Keyset Pagination（無時間過濾）。
    只以 pk_col 作為游標，適合無時間欄位或時間欄位全為 NULL 的資料表。
    """
    col_list = ", ".join(
        f'"{c}"::text AS "{c}"' if c in json_cols else f'"{c}"'
        for c in columns
    )

    if cursor_pk is None:
        sql = f"""
            SELECT {col_list}
            FROM "{table_name}"
            ORDER BY "{pk_col}"
            LIMIT %s
        """
        params = (batch_size,)
    else:
        sql = f"""
            SELECT {col_list}
            FROM "{table_name}"
            WHERE "{pk_col}" > %s
            ORDER BY "{pk_col}"
            LIMIT %s
        """
        params = (cursor_pk, batch_size)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# ── 寫入 ──────────────────────────────────────────────────────────────────────

def build_insert_sql(
    table_name: str,
    insert_columns: list[str],
    has_serial: bool,
    conflict_column: Optional[str],
) -> str:
    """
    建立 execute_values 相容的 INSERT 語句。
    VALUES 後使用單一 %s，由 execute_values 展開為多列。

    conflict_column 未指定：
      - INSERT 包含所有欄位（含 SERIAL PK，加 OVERRIDING SYSTEM VALUE）
      - ON CONFLICT DO NOTHING（涵蓋所有 UNIQUE / PK 約束）
    conflict_column 已指定：
      - INSERT 排除 SERIAL PK（讓 target 自動產生 id）
      - ON CONFLICT ("conflict_column") DO NOTHING
    """
    col_list  = ", ".join(f'"{c}"' for c in insert_columns)
    overriding = "OVERRIDING SYSTEM VALUE " if (has_serial and not conflict_column) else ""
    conflict  = f'ON CONFLICT ("{conflict_column}") DO NOTHING' if conflict_column else "ON CONFLICT DO NOTHING"

    return (
        f'INSERT INTO "{table_name}" ({col_list}) '
        f"{overriding}"
        f"VALUES %s "
        f"{conflict}"
    )


def build_row_template(insert_columns: list[str], json_cols: dict[str, str]) -> str:
    """
    建立 execute_values 的 per-row template。
    JSON/JSONB 欄位使用 %s::json 或 %s::jsonb，讓 PostgreSQL 把 text 轉回正確型別：
      - SQL NULL  → None   → %s::json[b] → NULL           ✓
      - JSON null → "null" → %s::json[b] → JSON null      ✓
      - JSON obj  → "{...}"→ %s::json[b] → JSON obj       ✓
    insert_columns 為實際要 INSERT 的欄位（可能已排除 SERIAL PK）。
    """
    placeholders = [
        f"%s::{json_cols[c]}" if c in json_cols else "%s"
        for c in insert_columns
    ]
    return "(" + ", ".join(placeholders) + ")"


def insert_batch(conn, sql: str, rows: list[tuple], row_template: str) -> int:
    """批次寫入，回傳實際寫入筆數（ON CONFLICT DO NOTHING 略過的不計）"""
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur, sql, rows, template=row_template, page_size=len(rows)
        )
        inserted = cur.rowcount
    conn.commit()
    return max(inserted, 0)


# ── chat_messages 專用：pre-filter 分頁策略 ──────────────────────────────────

CHUNKED_PREFILTER_TABLES = {"chat_messages"}
DEFAULT_CHUNK_MINUTES = 15


def fetch_source_pks(
    conn,
    table_name: str,
    pk_col: str,
    time_col: str,
    start: datetime.datetime,
    end: datetime.datetime,
) -> set:
    """取得 source 在指定時間範圍內的 PK set（供 pk-first 策略使用）。"""
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT "{pk_col}" FROM "{table_name}" '
            f'WHERE "{time_col}" >= %s AND "{time_col}" < %s',
            (start, end),
        )
        return {r[0] for r in cur.fetchall()}


def fetch_target_pks(
    conn,
    table_name: str,
    pk_col: str,
    time_col: str,
    start: datetime.datetime,
    end: datetime.datetime,
) -> set:
    """取得 target 在指定時間範圍內已存在的 PK set，供 pre-filter 使用。"""
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT "{pk_col}" FROM "{table_name}" '
            f'WHERE "{time_col}" >= %s AND "{time_col}" < %s',
            (start, end),
        )
        return {r[0] for r in cur.fetchall()}


def fetch_rows_by_pks(
    conn,
    table_name: str,
    columns: list[str],
    json_cols: dict[str, str],
    pk_col: str,
    pks: set,
    fetch_batch_size: int = 500,
) -> list[tuple]:
    """
    依指定 PK set 取得完整資料列（batched IN query）。
    當 pks 數量超過 fetch_batch_size 時自動分批，避免 query 過大。
    """
    if not pks:
        return []

    col_list = ", ".join(
        f'"{c}"::text AS "{c}"' if c in json_cols else f'"{c}"'
        for c in columns
    )

    pk_list = list(pks)
    rows: list[tuple] = []
    for i in range(0, len(pk_list), fetch_batch_size):
        batch = pk_list[i:i + fetch_batch_size]
        placeholders = ", ".join(["%s"] * len(batch))
        sql = (
            f'SELECT {col_list} FROM "{table_name}" '
            f'WHERE "{pk_col}" IN ({placeholders})'
        )
        with conn.cursor() as cur:
            cur.execute(sql, batch)
            rows.extend(cur.fetchall())
    return rows


def sync_chunked_pk_first(
    src_conn,
    tgt_conn,
    src_url: str,
    tgt_url: str,
    table_name: str,
    columns: list[str],
    pk_col: str,
    time_col: str,
    json_cols: dict[str, str],
    insert_columns: list[str],
    insert_indices: list[int],
    insert_sql: str,
    row_template: str,
    start: datetime.datetime,
    end: datetime.datetime,
    total: int,
    chunk_minutes: int,
    batch_size: int,
    verbose: bool,
) -> tuple[int, int, int]:
    """
    PK-first chunked 同步策略（適合高重複率 + 遠端 source）。

    每個 chunk 流程：
      1. 取 target PKs（本地，快）
      2. 取 source PKs（遠端，輕量，只傳 PK 字串）
      3. 計算 missing_pks = source_pks - target_pks
      4. 僅拉 missing_pks 對應的完整資料（WHERE pk IN (...)）
      5. 插入

    回傳 (total_processed, total_inserted, total_skipped)
    """
    src = [src_conn]
    tgt = [tgt_conn]

    def reconnect_src():
        try:
            src[0].close()
        except Exception:
            pass
        src[0] = connect_source(src_url)

    def reconnect_tgt():
        try:
            tgt[0].close()
        except Exception:
            pass
        tgt[0] = connect_target(tgt_url)

    chunk_delta = datetime.timedelta(minutes=chunk_minutes)
    chunk_start = start
    chunk_num   = 0

    total_processed = 0
    total_inserted  = 0
    total_skipped   = 0

    while chunk_start < end:
        chunk_end = min(chunk_start + chunk_delta, end)
        chunk_num += 1

        # 1. Target PKs（本地）
        target_pks = with_retry(
            lambda cs=chunk_start, ce=chunk_end: fetch_target_pks(
                tgt[0], table_name, pk_col, time_col, cs, ce
            ),
            reconnect_tgt,
            "target/fetch_pks",
        )

        # 2. Source PKs（遠端，輕量）
        source_pks = with_retry(
            lambda cs=chunk_start, ce=chunk_end: fetch_source_pks(
                src[0], table_name, pk_col, time_col, cs, ce
            ),
            reconnect_src,
            "source/fetch_pks",
        )

        # 3. 計算差集
        missing_pks  = source_pks - target_pks
        chunk_total  = len(source_pks)
        chunk_skipped = chunk_total - len(missing_pks)

        total_processed += chunk_total
        total_skipped   += chunk_skipped

        pct = min(total_processed / total * 100, 100) if total > 0 else 100
        status = (
            f"  Chunk {chunk_num:4d} | "
            f"{chunk_start.strftime('%m-%d %H:%M')} → {chunk_end.strftime('%H:%M')} | "
            f"source {chunk_total:6,} | skipped {chunk_skipped:6,} | "
            f"missing {len(missing_pks):4,} | {pct:.1f}%"
        )

        if verbose:
            print(status)

        # 4. 只拉 missing PKs 的完整資料
        inserted = 0
        if missing_pks:
            rows = with_retry(
                lambda mp=missing_pks: fetch_rows_by_pks(
                    src[0], table_name, columns, json_cols, pk_col, mp, batch_size,
                ),
                reconnect_src,
                "source/fetch_rows",
            )
            if rows:
                insert_rows = [tuple(r[i] for i in insert_indices) for r in rows]
                inserted = with_retry(
                    lambda ir=insert_rows: insert_batch(tgt[0], insert_sql, ir, row_template),
                    reconnect_tgt,
                    "target/insert",
                )
                total_inserted += inserted

        if not verbose or missing_pks:
            print(f"{status} | inserted {inserted:4,}")

        chunk_start = chunk_end

    return total_processed, total_inserted, total_skipped


def sync_chunked_prefilter(
    src_conn,
    tgt_conn,
    src_url: str,
    tgt_url: str,
    table_name: str,
    columns: list[str],
    pk_col: str,
    pk_col_idx: int,
    time_col: str,
    time_col_idx: int,
    json_cols: dict[str, str],
    insert_columns: list[str],
    insert_indices: list[int],
    insert_sql: str,
    row_template: str,
    start: datetime.datetime,
    end: datetime.datetime,
    total: int,
    chunk_minutes: int,
    batch_size: int,
    verbose: bool,
) -> tuple[int, int, int]:
    """
    Chunked pre-filter 同步策略（僅限 chat_messages）。

    將時間範圍切成 chunk_minutes 的小塊，每塊先從 target 取出已存在的 PK set，
    再從 source 讀取資料時過濾掉已存在的 row，只 INSERT 真正新的資料。

    連線中斷時自動重連（source / target 各自重連）。

    回傳 (total_processed, total_inserted, total_prefilter_skipped)
    """
    # ── 可重連的連線 holder ──
    src = [src_conn]
    tgt = [tgt_conn]

    def reconnect_src():
        try:
            src[0].close()
        except Exception:
            pass
        src[0] = connect_source(src_url)

    def reconnect_tgt():
        try:
            tgt[0].close()
        except Exception:
            pass
        tgt[0] = connect_target(tgt_url)

    chunk_delta = datetime.timedelta(minutes=chunk_minutes)
    chunk_start = start
    chunk_num   = 0

    total_processed = 0
    total_inserted  = 0
    total_skipped   = 0
    batch_num       = 0

    while chunk_start < end:
        chunk_end = min(chunk_start + chunk_delta, end)
        chunk_num += 1

        # ── 取 target 已存在的 PK set（支援重連）──
        target_pks = with_retry(
            lambda cs=chunk_start, ce=chunk_end: fetch_target_pks(
                tgt[0], table_name, pk_col, time_col, cs, ce
            ),
            reconnect_tgt,
            "target/fetch_pks",
        )
        if verbose:
            print(
                f"\n  [Chunk {chunk_num}] {chunk_start.strftime('%H:%M')} → {chunk_end.strftime('%H:%M')} "
                f"| target already has {len(target_pks):,} PKs"
            )

        # ── Keyset 批次讀取 + pre-filter ──
        cursor_time = None
        cursor_pk   = None

        while True:
            batch_num += 1

            # 拍下游標快照，避免 lambda 捕獲可變變數
            ct, cp = cursor_time, cursor_pk
            rows = with_retry(
                lambda cs=chunk_start, ce=chunk_end, _ct=ct, _cp=cp: fetch_batch_keyset(
                    src[0], table_name, columns, json_cols,
                    time_col, pk_col,
                    cs, ce,
                    _ct, _cp,
                    batch_size,
                ),
                reconnect_src,
                "source/fetch_batch",
            )
            if not rows:
                break

            last_row    = rows[-1]
            cursor_pk   = last_row[pk_col_idx]
            cursor_time = last_row[time_col_idx]

            # pre-filter：排除 target 已有的 PK
            new_rows    = [r for r in rows if r[pk_col_idx] not in target_pks]
            prefiltered = len(rows) - len(new_rows)

            inserted = 0
            if new_rows:
                insert_rows = [tuple(r[i] for i in insert_indices) for r in new_rows]
                inserted = with_retry(
                    lambda ir=insert_rows: insert_batch(tgt[0], insert_sql, ir, row_template),
                    reconnect_tgt,
                    "target/insert",
                )

            total_processed += len(rows)
            total_inserted  += inserted
            total_skipped   += prefiltered

            pct = min(total_processed / total * 100, 100)
            print(
                f"  Batch {batch_num:4d} | processed {total_processed:8,}/{total:,} "
                f"| inserted {inserted:5,} | pre-filtered {prefiltered:5,} | {pct:.1f}%"
            )

        chunk_start = chunk_end

    return total_processed, total_inserted, total_skipped


# ── 主流程 ────────────────────────────────────────────────────────────────────

def sync(
    source_url: str,
    target_url: str,
    table_name: str,
    start: Optional[datetime.datetime],
    end: Optional[datetime.datetime],
    sync_all: bool,
    time_column: Optional[str],
    conflict_column: Optional[str],
    batch_size: int,
    chunk_minutes: int,
    pk_first: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    if table_name in UNSUPPORTED_TABLES:
        raise ValueError(
            f"Table '{table_name}' is not supported for sync. "
            f"Unsupported tables: {sorted(UNSUPPORTED_TABLES)}"
        )

    print(f"\n{'='*60}")
    print(f"  Table      : {table_name}")
    if sync_all:
        print(f"  Time range : ALL ROWS")
    else:
        print(f"  Time range : {start.isoformat()} → {end.isoformat()}")
    print(f"  Batch size : {batch_size}")
    print(f"  Mode       : {'DRY-RUN (no writes)' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    src_conn = None
    tgt_conn = None

    try:
        # ── 連線 ──
        print("Connecting to source DB...")
        src_conn = connect_source(source_url)

        if not dry_run:
            print("Connecting to target DB...")
            tgt_conn = connect_target(target_url)

        # ── Schema 偵測 ──
        columns      = get_columns(src_conn, table_name)
        pk_columns   = get_primary_keys(src_conn, table_name)
        serial_cols  = get_serial_columns(src_conn, table_name)
        json_cols    = get_json_columns(src_conn, table_name)
        time_col     = None if sync_all else (time_column or detect_time_column(table_name, columns))
        has_serial   = bool(serial_cols & set(pk_columns))

        if len(pk_columns) > 1:
            raise ValueError(
                f"Table '{table_name}' has a composite PK {pk_columns}, "
                f"which is not supported by keyset pagination."
            )
        pk_col = pk_columns[0]

        print(f"Columns     : {columns}")
        print(f"PK column   : {pk_col}")
        if not sync_all:
            print(f"Time column : {time_col}")
        if serial_cols:
            print(f"Serial cols : {sorted(serial_cols)}")
        if json_cols:
            print(f"JSON cols   : {sorted(json_cols)}")

        # ── 決定衝突欄位（優先用手動指定，否則查 TABLE_CONFLICT_COLUMNS）──
        conflict_column = conflict_column or TABLE_CONFLICT_COLUMNS.get(table_name)
        if conflict_column:
            print(f"Conflict on : {conflict_column} (SERIAL PK excluded from INSERT)")
        print()

        if not sync_all and time_col not in columns:
            raise ValueError(f"Time column '{time_col}' not found in table '{table_name}'.")

        # ── 計算總筆數 ──
        if sync_all:
            total = count_all_rows(src_conn, table_name)
        else:
            total = count_rows(src_conn, table_name, time_col, start, end)
        print(f"Rows to sync: {total:,}")

        if total == 0:
            print("Nothing to sync. Done.")
            return

        if dry_run:
            print("Dry-run mode: skipping actual write.")
            return

        # ── 決定 INSERT 欄位（conflict_column 模式下排除 SERIAL PK）──
        serial_pk_cols = serial_cols & set(pk_columns)
        if conflict_column:
            if conflict_column not in columns:
                raise ValueError(f"--conflict-column '{conflict_column}' not found in table '{table_name}'.")
            insert_columns  = [c for c in columns if c not in serial_pk_cols]
            insert_indices  = [i for i, c in enumerate(columns) if c not in serial_pk_cols]
        else:
            insert_columns  = columns
            insert_indices  = list(range(len(columns)))

        # ── 建立 INSERT SQL 與 per-row template ──
        insert_sql   = build_insert_sql(table_name, insert_columns, has_serial, conflict_column)
        row_template = build_row_template(insert_columns, json_cols)
        if verbose:
            print(f"Insert SQL  : {insert_sql}")
            print(f"Row template: {row_template}\n")

        # ── 欄位索引（供游標提取用）──
        pk_col_idx   = columns.index(pk_col)
        time_col_idx = columns.index(time_col) if not sync_all else None

        use_chunked = (table_name in CHUNKED_PREFILTER_TABLES) and (not sync_all)
        if use_chunked:
            strategy_name = f"pk-first (chunk={chunk_minutes}min)" if pk_first else f"chunked pre-filter (chunk={chunk_minutes}min)"
            print(f"Strategy    : {strategy_name}\n")
        else:
            print()

        # ── 同步策略分支 ──
        if use_chunked and pk_first:
            processed, total_inserted, total_skipped = sync_chunked_pk_first(
                src_conn=src_conn,
                tgt_conn=tgt_conn,
                src_url=source_url,
                tgt_url=target_url,
                table_name=table_name,
                columns=columns,
                pk_col=pk_col,
                time_col=time_col,
                json_cols=json_cols,
                insert_columns=insert_columns,
                insert_indices=insert_indices,
                insert_sql=insert_sql,
                row_template=row_template,
                start=start,
                end=end,
                total=total,
                chunk_minutes=chunk_minutes,
                batch_size=batch_size,
                verbose=verbose,
            )
            skipped_label = "pk-first pre-filtered"
        elif use_chunked:
            processed, total_inserted, total_skipped = sync_chunked_prefilter(
                src_conn=src_conn,
                tgt_conn=tgt_conn,
                src_url=source_url,
                tgt_url=target_url,
                table_name=table_name,
                columns=columns,
                pk_col=pk_col,
                pk_col_idx=pk_col_idx,
                time_col=time_col,
                time_col_idx=time_col_idx,
                json_cols=json_cols,
                insert_columns=insert_columns,
                insert_indices=insert_indices,
                insert_sql=insert_sql,
                row_template=row_template,
                start=start,
                end=end,
                total=total,
                chunk_minutes=chunk_minutes,
                batch_size=batch_size,
                verbose=verbose,
            )
            skipped_label = "pre-filtered"
        else:
            # ── 非 chunked：可重連的連線 holder ──
            src = [src_conn]
            tgt = [tgt_conn]

            def reconnect_src():
                try:
                    src[0].close()
                except Exception:
                    pass
                src[0] = connect_source(source_url)

            def reconnect_tgt():
                try:
                    tgt[0].close()
                except Exception:
                    pass
                tgt[0] = connect_target(target_url)

            cursor_time    = None
            cursor_pk      = None
            processed      = 0
            total_inserted = 0
            total_skipped  = 0
            batch_num      = 0

            while True:
                batch_num += 1
                ct, cp = cursor_time, cursor_pk

                if sync_all:
                    rows = with_retry(
                        lambda _cp=cp: fetch_batch_keyset_all(
                            src[0], table_name, columns, json_cols,
                            pk_col, _cp, batch_size,
                        ),
                        reconnect_src,
                        "source/fetch_batch",
                    )
                else:
                    rows = with_retry(
                        lambda _ct=ct, _cp=cp: fetch_batch_keyset(
                            src[0], table_name, columns, json_cols,
                            time_col, pk_col,
                            start, end,
                            _ct, _cp,
                            batch_size,
                        ),
                        reconnect_src,
                        "source/fetch_batch",
                    )
                if not rows:
                    break

                last_row  = rows[-1]
                cursor_pk = last_row[pk_col_idx]
                if not sync_all:
                    cursor_time = last_row[time_col_idx]

                insert_rows = [tuple(r[i] for i in insert_indices) for r in rows]
                inserted = with_retry(
                    lambda ir=insert_rows: insert_batch(tgt[0], insert_sql, ir, row_template),
                    reconnect_tgt,
                    "target/insert",
                )
                skipped  = len(rows) - inserted
                total_inserted += inserted
                total_skipped  += skipped
                processed      += len(rows)

                pct = min(processed / total * 100, 100)
                print(
                    f"  Batch {batch_num:4d} | processed {processed:8,}/{total:,} "
                    f"| inserted {inserted:5,} | skipped {skipped:5,} | {pct:.1f}%"
                )
            skipped_label = "PK conflict"

        # ── 結果摘要 ──
        print(f"\n{'─'*60}")
        print(f"  Total fetched  : {processed:,}")
        print(f"  Total inserted : {total_inserted:,}")
        print(f"  Total skipped  : {total_skipped:,} ({skipped_label})")
        print(f"{'─'*60}")

    finally:
        if src_conn:
            try:
                src_conn.close()
            except Exception:
                pass
        if tgt_conn:
            try:
                tgt_conn.close()
            except Exception:
                pass


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_datetime(s: str) -> datetime.datetime:
    """支援 ISO 8601 格式，沒有時區時視為 UTC"""
    try:
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime format: '{s}'. Use ISO 8601, e.g. '2025-01-01T00:00:00+00:00'"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Batch sync a PostgreSQL table between two databases (skip on PK conflict).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── 連線 ──
    conn_group = parser.add_argument_group("Connection")
    conn_group.add_argument(
        "--source-url",
        required=True,
        metavar="URL",
        help="Source DB connection URL, e.g. postgresql://user:pass@host:5432/db",
    )
    conn_group.add_argument(
        "--target-url",
        required=True,
        metavar="URL",
        help="Target DB connection URL",
    )

    # ── 同步範圍 ──
    sync_group = parser.add_argument_group("Sync parameters")
    sync_group.add_argument(
        "--table",
        required=True,
        metavar="TABLE",
        help="Table name to sync",
    )
    sync_group.add_argument(
        "--all",
        action="store_true",
        dest="sync_all",
        help="Sync all rows without time filtering (for tables with no time column or all-NULL timestamps)",
    )
    sync_group.add_argument(
        "--start",
        default=None,
        type=parse_datetime,
        metavar="DATETIME",
        help="Start time (inclusive), ISO 8601 format. e.g. '2025-01-01T00:00:00+00:00'",
    )
    sync_group.add_argument(
        "--end",
        default=None,
        type=parse_datetime,
        metavar="DATETIME",
        help="End time (exclusive), ISO 8601 format. e.g. '2025-01-02T00:00:00+00:00'",
    )
    sync_group.add_argument(
        "--time-column",
        default=None,
        metavar="COLUMN",
        help=(
            "Column used for time-range filtering. "
            f"Auto-detected if omitted. Defaults: {TABLE_TIME_COLUMNS}"
        ),
    )
    sync_group.add_argument(
        "--conflict-column",
        default=None,
        metavar="COLUMN",
        help=(
            "Use this column as the conflict target instead of PK. "
            "SERIAL PK will be excluded from INSERT (target auto-generates id). "
            "e.g. --conflict-column name"
        ),
    )
    sync_group.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        metavar="N",
        help="Number of rows per batch (default: 1000)",
    )
    sync_group.add_argument(
        "--chunk-minutes",
        type=int,
        default=DEFAULT_CHUNK_MINUTES,
        metavar="N",
        help=(
            f"Time chunk size in minutes for chunked pre-filter strategy "
            f"(default: {DEFAULT_CHUNK_MINUTES}, applies to: {sorted(CHUNKED_PREFILTER_TABLES)})"
        ),
    )

    # ── 行為控制 ──
    parser.add_argument(
        "--pk-first",
        action="store_true",
        help=(
            "PK-first sync strategy for high-duplicate scenarios (source is remote). "
            "Per chunk: fetch source/target PKs, compute diff, fetch only missing full rows. "
            f"Only applies to: {sorted(CHUNKED_PREFILTER_TABLES)}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count rows only, do not write to target DB",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra debug info (e.g. INSERT SQL)",
    )

    args = parser.parse_args()

    if args.sync_all and (args.start or args.end):
        parser.error("--all cannot be used together with --start / --end")
    if not args.sync_all and not (args.start and args.end):
        parser.error("must provide either --all or both --start and --end")
    if not args.sync_all and args.start >= args.end:
        parser.error("--start must be earlier than --end")

    try:
        sync(
            source_url=args.source_url,
            target_url=args.target_url,
            table_name=args.table,
            start=args.start,
            end=args.end,
            sync_all=args.sync_all,
            time_column=args.time_column,
            conflict_column=args.conflict_column,
            batch_size=args.batch_size,
            chunk_minutes=args.chunk_minutes,
            pk_first=args.pk_first,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

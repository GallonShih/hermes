#!/usr/bin/env python3
"""
臨時調試腳本：檢查 collector 的 last_activity_time
"""
import os
import sys
import time
from datetime import datetime, timedelta

# 添加 collector 目錄到路徑
sys.path.insert(0, '/app/collector')

try:
    # 嘗試導入並訪問正在運行的 collector 實例
    # 這個方法需要修改 main.py 來暴露實例
    
    print("=" * 60)
    print("Collector Activity Monitor")
    print("=" * 60)
    print(f"Current time: {datetime.now()}")
    print()
    
    # 方法 1: 讀取日誌查找最後的訊息時間
    print("Checking chat messages in database...")
    
    from database import get_db_session
    from sqlalchemy import text
    
    with get_db_session() as session:
        # 查詢最後一條聊天訊息的時間
        result = session.execute(text("""
            SELECT 
                message_id,
                author_name,
                message,
                published_at,
                created_at,
                NOW() - created_at as time_since_last
            FROM chat_messages 
            ORDER BY created_at DESC 
            LIMIT 1
        """)).fetchone()
        
        if result:
            print(f"Last chat message:")
            print(f"  Message ID: {result[0]}")
            print(f"  Author: {result[1]}")
            print(f"  Content: {result[2][:50]}...")
            print(f"  Published: {result[3]}")
            print(f"  Saved at: {result[4]}")
            print(f"  Time since: {result[5]}")
        else:
            print("  No messages found in database")
        
        print()
        
        # 查詢最後 10 條訊息的統計
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total,
                MAX(created_at) as last_created,
                MIN(created_at) as first_created
            FROM chat_messages 
            WHERE created_at > NOW() - INTERVAL '1 hour'
        """)).fetchone()
        
        print(f"Messages in last hour:")
        print(f"  Total: {result[0]}")
        print(f"  First: {result[2]}")
        print(f"  Last: {result[1]}")
        
        print()
        
        # 查詢 buffer flush 的頻率
        result = session.execute(text("""
            SELECT 
                DATE_TRUNC('minute', created_at) as minute,
                COUNT(*) as msg_count
            FROM chat_messages 
            WHERE created_at > NOW() - INTERVAL '30 minutes'
            GROUP BY DATE_TRUNC('minute', created_at)
            ORDER BY minute DESC
            LIMIT 10
        """)).fetchall()
        
        print(f"Message rate (last 30 min, by minute):")
        if result:
            for row in result:
                print(f"  {row[0]}: {row[1]} messages")
        else:
            print("  No messages in last 30 minutes")
    
    print()
    print("=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

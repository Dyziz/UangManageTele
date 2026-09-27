import sqlite3
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

DB_FILE = os.getenv("DATABASE_FILE", "finance.db")

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        telegram_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (telegram_id) REFERENCES users (telegram_id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def save_transaction(telegram_id: int, username: Optional[str], first_name: str, 
                     amount: float, category: str, tx_type: str, description: str) -> str:
    tx_id = str(uuid.uuid4())[:8]  # Short id for telegram callback data
    conn = get_connection()
    cursor = conn.cursor()

    # Upsert user
    cursor.execute("""
    INSERT INTO users (telegram_id, username, first_name)
    VALUES (?, ?, ?)
    ON CONFLICT(telegram_id) DO UPDATE SET
        username=excluded.username,
        first_name=excluded.first_name;
    """, (telegram_id, username, first_name))

    # Insert transaction
    cursor.execute("""
    INSERT INTO transactions (transaction_id, telegram_id, category, type, amount, description)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (tx_id, telegram_id, category, tx_type, amount, description))

    conn.commit()
    conn.close()
    return tx_id

def delete_transaction(tx_id: str, telegram_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT transaction_id, category, amount, description, type 
    FROM transactions 
    WHERE transaction_id = ? AND telegram_id = ?;
    """, (tx_id, telegram_id))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    data = dict(row)
    cursor.execute("DELETE FROM transactions WHERE transaction_id = ?;", (tx_id,))
    conn.commit()
    conn.close()
    return data

MONTH_NAMES = {
    '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
    '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
    '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
}

def get_rekap_data(telegram_id: int, period: str = 'month', custom_param: Optional[str] = None) -> Tuple[Dict[str, int], int, int, str]:
    """
    Flexible aggregation:
    - period = 'today': Hari ini
    - period = 'week': 7 hari terakhir
    - period = 'month': Bulan ini
    - period = 'last_month': Bulan lalu
    - period = 'custom_month': custom_param is 'YYYY-MM'
    
    Returns (cat_data, total_expense, total_income, period_label)
    """
    conn = get_connection()
    cursor = conn.cursor()

    params = [telegram_id]
    inc_params = [telegram_id]

    if period == 'today':
        where_clause = "date(created_at, 'localtime') = date('now', 'localtime')"
        period_label = "Hari Ini"
    elif period == 'week':
        where_clause = "created_at >= datetime('now', '-7 days')"
        period_label = "7 Hari Terakhir"
    elif period == 'last_month':
        where_clause = "strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'start of month', '-1 month')"
        period_label = "Bulan Lalu"
    elif period == 'custom_month' and custom_param:
        where_clause = "strftime('%Y-%m', created_at, 'localtime') = ?"
        params.append(custom_param)
        inc_params.append(custom_param)
        parts = custom_param.split('-')
        m_name = MONTH_NAMES.get(parts[1], parts[1]) if len(parts) == 2 else custom_param
        year = parts[0] if len(parts) == 2 else ""
        period_label = f"{m_name} {year}".strip()
    else:  # default 'month'
        where_clause = "strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m', 'now', 'localtime')"
        now = datetime.now()
        m_name = MONTH_NAMES.get(now.strftime('%m'), '')
        period_label = f"Bulan Ini ({m_name})"

    # Expenses by category
    query_exp = f"""
    SELECT category, SUM(amount) as total
    FROM transactions
    WHERE telegram_id = ? 
      AND type = 'EXPENSE'
      AND {where_clause}
    GROUP BY category
    ORDER BY total DESC;
    """
    cursor.execute(query_exp, params)
    rows = cursor.fetchall()
    cat_data = {row['category']: int(row['total']) for row in rows}
    total_expense = sum(cat_data.values())

    # Total income
    query_inc = f"""
    SELECT SUM(amount) as total
    FROM transactions
    WHERE telegram_id = ? 
      AND type = 'INCOME'
      AND {where_clause};
    """
    cursor.execute(query_inc, inc_params)
    inc_row = cursor.fetchone()
    total_income = int(inc_row['total'] or 0)

    conn.close()
    return cat_data, total_expense, total_income, period_label

def get_monthly_rekap(telegram_id: int) -> Tuple[Dict[str, int], int, int]:
    cat_data, total_exp, total_inc, _ = get_rekap_data(telegram_id, 'month')
    return cat_data, total_exp, total_inc


def get_recent_transactions(telegram_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT transaction_id, category, type, amount, description, created_at
    FROM transactions
    WHERE telegram_id = ?
    ORDER BY created_at DESC
    LIMIT ?;
    """, (telegram_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_paginated_transactions(telegram_id: int, page: int = 1, per_page: int = 5) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Returns (items, total_count, total_pages)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE telegram_id = ?;", (telegram_id,))
    total_count = cursor.fetchone()[0]

    if total_count == 0:
        conn.close()
        return [], 0, 1

    total_pages = max(1, (total_count + per_page - 1) // per_page)
    # Clamp page
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    cursor.execute("""
    SELECT transaction_id, category, type, amount, description, created_at
    FROM transactions
    WHERE telegram_id = ?
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?;
    """, (telegram_id, per_page, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows], total_count, total_pages


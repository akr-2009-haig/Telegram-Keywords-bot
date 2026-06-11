# -*- coding: utf-8 -*-
"""Database management using SQLite"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import threading

class Database:
    """SQLite database manager"""

    def __init__(self, db_path):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_admin INTEGER DEFAULT 0,
                is_owner INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER UNIQUE,
                title TEXT,
                username TEXT,
                invite_link TEXT,
                member_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                is_private INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY,
                word TEXT UNIQUE,
                is_active INTEGER DEFAULT 1,
                match_count INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                id INTEGER PRIMARY KEY,
                word TEXT UNIQUE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forwarded_messages (
                id INTEGER PRIMARY KEY,
                original_message_id INTEGER,
                original_chat_id INTEGER,
                forwarded_message_id INTEGER,
                forwarded_chat_id INTEGER,
                keyword TEXT,
                sender_username TEXT,
                sender_id INTEGER,
                message_text TEXT,
                group_title TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY,
                date TEXT UNIQUE,
                messages_checked INTEGER DEFAULT 0,
                messages_forwarded INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS stats_date_idx ON stats (date)
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS userbot_session (
                id INTEGER PRIMARY KEY,
                phone TEXT,
                session_string TEXT,
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                username TEXT,
                added_by INTEGER,
                permissions TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    def add_user(self, user_id, username, first_name, last_name, is_owner=False):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users (id, username, first_name, last_name, is_owner)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, 1 if is_owner else 0))
        conn.commit()

    def get_user(self, user_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def is_owner(self, user_id):
        user = self.get_user(user_id)
        return user["is_owner"] == 1 if user else False

    def add_group(self, chat_id, title, username=None, invite_link=None, member_count=0, is_private=False):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO groups (chat_id, title, username, invite_link, member_count, is_private)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chat_id, title, username, invite_link, member_count, 1 if is_private else 0))
        conn.commit()

    def get_groups(self, active_only=True):
        conn = self._get_conn()
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM groups WHERE is_active = 1 ORDER BY added_at DESC")
        else:
            cursor.execute("SELECT * FROM groups ORDER BY added_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_group(self, chat_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM groups WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_group(self, chat_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM groups WHERE chat_id = ?", (chat_id,))
        conn.commit()

    def delete_all_groups(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM groups")
        conn.commit()

    def toggle_group(self, chat_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM groups WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if row:
            new_status = 0 if row["is_active"] == 1 else 1
            cursor.execute("UPDATE groups SET is_active = ? WHERE chat_id = ?", (new_status, chat_id))
            conn.commit()
            return new_status == 1
        return False

    def add_keyword(self, word):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO keywords (word) VALUES (?)", (word.lower(),))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_keywords(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM keywords WHERE is_active = 1 ORDER BY word")
        return [row["word"] for row in cursor.fetchall()]

    def delete_keyword(self, word):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keywords WHERE word = ?", (word.lower(),))
        conn.commit()

    def clear_keywords(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keywords")
        conn.commit()

    def add_blacklist(self, word):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO blacklist (word) VALUES (?)", (word.lower(),))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_blacklist(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM blacklist ORDER BY word")
        return [row["word"] for row in cursor.fetchall()]

    def delete_blacklist(self, word):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM blacklist WHERE word = ?", (word.lower(),))
        conn.commit()

    def add_forwarded_message(self, original_message_id, original_chat_id,
                            forwarded_message_id, forwarded_chat_id,
                            keyword, sender_username, sender_id,
                            message_text, group_title):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO forwarded_messages 
            (original_message_id, original_chat_id, forwarded_message_id, forwarded_chat_id,
             keyword, sender_username, sender_id, message_text, group_title)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (original_message_id, original_chat_id, forwarded_message_id, forwarded_chat_id,
              keyword, sender_username, sender_id, message_text, group_title))
        conn.commit()
        return cursor.lastrowid

    def get_forwarded_message(self, record_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM forwarded_messages WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_forwarded_message_status(self, record_id, status):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE forwarded_messages SET status = ? WHERE id = ?", (status, record_id))
        conn.commit()

    def get_recent_messages(self, limit=20, offset=0):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM forwarded_messages 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        return [dict(row) for row in cursor.fetchall()]

    def get_messages_count(self, hours=24):
        conn = self._get_conn()
        cursor = conn.cursor()
        since = datetime.now() - timedelta(hours=hours)
        cursor.execute("""
            SELECT COUNT(*) as count FROM forwarded_messages 
            WHERE created_at > ?
        """, (since.isoformat(),))
        row = cursor.fetchone()
        return row["count"] if row else 0

    def get_total_messages_count(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM forwarded_messages")
        row = cursor.fetchone()
        return row["count"] if row else 0

    def is_duplicate(self, sender_id, message_text, minutes=30):
        """Check if a similar message was recently forwarded from same sender"""
        conn = self._get_conn()
        cursor = conn.cursor()
        since = datetime.now() - timedelta(minutes=minutes)
        cursor.execute("""
            SELECT COUNT(*) as count FROM forwarded_messages
            WHERE sender_id = ? AND message_text = ? AND created_at > ?
        """, (sender_id, message_text, since.isoformat()))
        row = cursor.fetchone()
        return row["count"] > 0 if row else False

    def get_setting(self, key, default=None):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))
        conn.commit()

    def increment_stat(self, messages_checked=0, messages_forwarded=0):
        conn = self._get_conn()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO stats (date, messages_checked, messages_forwarded)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                messages_checked = messages_checked + excluded.messages_checked,
                messages_forwarded = messages_forwarded + excluded.messages_forwarded
        """, (today, messages_checked, messages_forwarded))
        conn.commit()

    def get_stats(self, days=30):
        conn = self._get_conn()
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT 
                SUM(messages_checked) as total_checked,
                SUM(messages_forwarded) as total_forwarded,
                COUNT(*) as days_active
            FROM stats 
            WHERE date >= ?
        """, (since,))
        row = cursor.fetchone()
        return {
            "total_checked": row["total_checked"] or 0,
            "total_forwarded": row["total_forwarded"] or 0,
            "days_active": row["days_active"] or 0
        }

    def save_userbot_session(self, phone, session_string):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM userbot_session")
        cursor.execute("""
            INSERT INTO userbot_session (phone, session_string, is_active)
            VALUES (?, ?, 1)
        """, (phone, session_string))
        conn.commit()

    def get_userbot_session(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM userbot_session WHERE is_active = 1 LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def clear_userbot_session(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM userbot_session")
        conn.commit()

    def add_admin(self, user_id, username, added_by, permissions=None):
        conn = self._get_conn()
        cursor = conn.cursor()
        perms = json.dumps(permissions or ["all"])
        cursor.execute("""
            INSERT OR REPLACE INTO admins (user_id, username, added_by, permissions)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, added_by, perms))
        conn.commit()

    def get_admins(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins")
        return [dict(row) for row in cursor.fetchall()]

    def delete_admin(self, user_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()

    def is_admin(self, user_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

    def has_permission(self, user_id, permission):
        if self.is_owner(user_id):
            return True
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT permissions FROM admins WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            perms = json.loads(row['permissions'])
            return 'all' in perms or permission in perms
        return False

    def update_admin_permissions(self, user_id, permissions):
        conn = self._get_conn()
        cursor = conn.cursor()
        perms = json.dumps(permissions)
        cursor.execute('UPDATE admins SET permissions = ? WHERE user_id = ?', (perms, user_id))
        conn.commit()

    def get_admin_permissions(self, user_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT permissions FROM admins WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row['permissions'])
        return []

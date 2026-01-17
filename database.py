# database.py
import sqlite3
import os
import sys
import json
from datetime import datetime
from config import APP_NAME, DB_NAME

class DatabaseManager:
    def __init__(self):
        self.db_path = self._get_app_data_path()
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._init_db()
        self._migrate_db()

    def _get_app_data_path(self):
        if sys.platform == "win32":
            app_data = os.getenv('LOCALAPPDATA')
        else:
            app_data = os.path.expanduser("~/.local/share")
        
        folder = os.path.join(app_data, APP_NAME)
        if not os.path.exists(folder):
            os.makedirs(folder)
        return os.path.join(folder, DB_NAME)

    def _init_db(self):
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT,
                password TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                title TEXT, 
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                task TEXT,
                due_date TEXT,
                is_done INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def _migrate_db(self):
        try:
            self.cursor.execute("ALTER TABLE todos ADD COLUMN due_date TEXT")
            self.conn.commit()
        except sqlite3.OperationalError: pass
        try:
            self.cursor.execute("ALTER TABLE projects ADD COLUMN password TEXT")
            self.conn.commit()
        except sqlite3.OperationalError: pass

    # --- HELPER: Extracts clean text title from JSON or Plain Text ---
    def _get_plain_text_title(self, content):
        try:
            # Try to parse as JSON (New Format)
            data = json.loads(content)
            # If successful, extract the 'text' field
            raw_text = data.get("text", "")
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, it's likely old plain text (Old Format)
            raw_text = content
        
        # Grab the first line, limit to 30 chars
        title = raw_text.split('\n')[0][:30].strip()
        return title if title else "Untitled"

    def add_project(self, name, description):
        self.cursor.execute("INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)",
                            (name, description, datetime.now().strftime("%Y-%m-%d %H:%M")))
        self.conn.commit()

    def get_projects(self, search_query=""):
        if search_query:
            q = f"%{search_query}%"
            self.cursor.execute("SELECT * FROM projects WHERE name LIKE ? OR description LIKE ? ORDER BY id DESC", (q, q))
        else:
            self.cursor.execute("SELECT * FROM projects ORDER BY id DESC")
        return self.cursor.fetchall()

    def delete_project(self, project_id):
        self.cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()

    def set_project_password(self, project_id, password):
        self.cursor.execute("UPDATE projects SET password = ? WHERE id = ?", (password, project_id))
        self.conn.commit()

    def get_project_password(self, project_id):
        self.cursor.execute("SELECT password FROM projects WHERE id = ?", (project_id,))
        res = self.cursor.fetchone()
        return res[0] if res else None

    def add_note(self, project_id, content="New Note"):
        # FIX: Use helper to generate clean title
        title = self._get_plain_text_title(content)
        
        self.cursor.execute("INSERT INTO notes (project_id, title, content, timestamp) VALUES (?, ?, ?, ?)",
                            (project_id, title, content, datetime.now().strftime("%Y-%m-%d %H:%M")))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_note(self, note_id, content):
        # FIX: Use helper to generate clean title
        title = self._get_plain_text_title(content)
        
        self.cursor.execute("UPDATE notes SET title = ?, content = ?, timestamp = ? WHERE id = ?",
                            (title, content, datetime.now().strftime("%Y-%m-%d %H:%M"), note_id))
        self.conn.commit()

    def get_notes(self, project_id, search_query=""):
        if search_query:
            q = f"%{search_query}%"
            self.cursor.execute("SELECT id, project_id, title, timestamp FROM notes WHERE project_id = ? AND (title LIKE ? OR content LIKE ?) ORDER BY timestamp DESC", (project_id, q, q))
        else:
            self.cursor.execute("SELECT id, project_id, title, timestamp FROM notes WHERE project_id = ? ORDER BY timestamp DESC", (project_id,))
        return self.cursor.fetchall()

    def get_note_content(self, note_id):
        self.cursor.execute("SELECT content FROM notes WHERE id = ?", (note_id,))
        result = self.cursor.fetchone()
        return result[0] if result else ""
    
    def get_all_notes_content(self, project_id):
        self.cursor.execute("SELECT title, content FROM notes WHERE project_id = ? ORDER BY timestamp DESC", (project_id,))
        return self.cursor.fetchall()

    def delete_note(self, note_id):
        self.cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()

    def add_todo(self, project_id, task, due_date=""):
        self.cursor.execute("INSERT INTO todos (project_id, task, due_date, created_at) VALUES (?, ?, ?, ?)",
                            (project_id, task, due_date, datetime.now().strftime("%Y-%m-%d")))
        self.conn.commit()

    def get_todos(self, project_id):
        self.cursor.execute("""
            SELECT id, project_id, task, due_date, is_done, created_at 
            FROM todos WHERE project_id = ? ORDER BY is_done ASC, id DESC
        """, (project_id,))
        return self.cursor.fetchall()

    def toggle_todo(self, todo_id, is_done):
        val = 1 if is_done else 0
        self.cursor.execute("UPDATE todos SET is_done = ? WHERE id = ?", (val, todo_id))
        self.conn.commit()

    def delete_todo(self, todo_id):
        self.cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self.conn.commit()
import tkinter as tk
from tkinter import ttk, font, filedialog
import sqlite3
import os
import sys
import re
import calendar
from datetime import datetime

# --- Optional PDF Support ---
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
    from reportlab.pdfgen import canvas
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False

APP_NAME = "Note"
DB_NAME = "noteapp.db"

COLORS = {
    "bg_main": "#FDFCF0",        
    "bg_sec": "#F4EBC3",         
    "bg_hover": "#E6D0A8",       
    "bg_active": "#D4B483",      
    "fg_text": "#4B3621",        
    "fg_sub": "#6F4E37",         
    "accent": "#A0522D",         
    "search_hi": "#FFF59D",      
    "search_active": "#FF9800",  
    "white": "#FFFFFF",
    "error": "#D32F2F"
}

# --- Database Manager ---
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
        title = content.split('\n')[0][:30] if content else "Untitled"
        self.cursor.execute("INSERT INTO notes (project_id, title, content, timestamp) VALUES (?, ?, ?, ?)",
                            (project_id, title, content, datetime.now().strftime("%Y-%m-%d %H:%M")))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_note(self, note_id, content):
        title = content.split('\n')[0][:30] if content else "Untitled"
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

# --- CUSTOM POPUP CLASSES ---
class CustomDialog(tk.Toplevel):
    def __init__(self, parent, title, width=350, height=160):
        super().__init__(parent)
        self.withdraw() # <--- FIXED: Hide window initially to prevent "flash"
        self.title(title)
        self.geometry(f"{width}x{height}")
        try: self.iconbitmap("icon.ico")
        except: pass
        self.configure(bg=COLORS["bg_main"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Position the window
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        self.deiconify() # <--- FIXED: Show window only after it is ready

class CustomMessageDialog(CustomDialog):
    def __init__(self, parent, title, message, is_error=False):
        super().__init__(parent, title)
        fg_color = COLORS["error"] if is_error else COLORS["fg_text"]
        tk.Label(self, text=message, bg=COLORS["bg_main"], fg=fg_color, wraplength=300, font=("Segoe UI", 10)).pack(expand=True, padx=20, pady=20)
        ttk.Button(self, text="OK", command=self.destroy).pack(pady=(0, 20))
        self.wait_window()

class CustomAskYesNo(CustomDialog):
    def __init__(self, parent, title, message):
        super().__init__(parent, title)
        self.result = False
        tk.Label(self, text=message, bg=COLORS["bg_main"], fg=COLORS["fg_text"], wraplength=300, font=("Segoe UI", 10)).pack(expand=True, padx=20, pady=20)
        f = tk.Frame(self, bg=COLORS["bg_main"])
        f.pack(pady=(0, 20))
        ttk.Button(f, text="Yes", command=self.on_yes).pack(side="left", padx=10)
        ttk.Button(f, text="No", command=self.destroy).pack(side="left", padx=10)
        self.wait_window()
    def on_yes(self):
        self.result = True
        self.destroy()

class CustomAskString(CustomDialog):
    def __init__(self, parent, title, prompt, show=None):
        super().__init__(parent, title, height=180)
        self.result = None
        tk.Label(self, text=prompt, bg=COLORS["bg_main"], fg=COLORS["fg_text"], font=("Segoe UI", 10)).pack(pady=(20, 5))
        self.entry = ttk.Entry(self, show=show, width=30)
        self.entry.pack(pady=5)
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda e: self.on_ok())
        f = tk.Frame(self, bg=COLORS["bg_main"])
        f.pack(pady=20)
        ttk.Button(f, text="OK", command=self.on_ok).pack(side="left", padx=10)
        ttk.Button(f, text="Cancel", command=self.destroy).pack(side="left", padx=10)
        self.wait_window()
    def on_ok(self):
        self.result = self.entry.get()
        self.destroy()

class CalendarDialog(CustomDialog):
    def __init__(self, parent, callback):
        super().__init__(parent, "Select Date", 250, 250)
        self.callback = callback
        self.year = datetime.now().year
        self.month = datetime.now().month
        self._setup_ui()
        self._update_calendar()
    def _setup_ui(self):
        header = tk.Frame(self, bg=COLORS["bg_sec"])
        header.pack(fill="x", pady=5)
        tk.Button(header, text="<", command=self._prev_month, bg=COLORS["bg_main"], relief="flat").pack(side="left", padx=5)
        self.lbl_month = tk.Label(header, text="", bg=COLORS["bg_sec"], font=("Segoe UI", 10, "bold"))
        self.lbl_month.pack(side="left", expand=True)
        tk.Button(header, text=">", command=self._next_month, bg=COLORS["bg_main"], relief="flat").pack(side="right", padx=5)
        self.cal_frame = tk.Frame(self, bg=COLORS["bg_main"])
        self.cal_frame.pack(fill="both", expand=True, padx=10, pady=5)
    def _update_calendar(self):
        for widget in self.cal_frame.winfo_children(): widget.destroy()
        self.lbl_month.config(text=f"{calendar.month_name[self.month]} {self.year}")
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for i, day in enumerate(days):
            tk.Label(self.cal_frame, text=day, bg=COLORS["bg_main"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold")).grid(row=0, column=i)
        cal = calendar.monthcalendar(self.year, self.month)
        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day != 0:
                    tk.Button(self.cal_frame, text=str(day), width=3, relief="flat", bg=COLORS["white"],
                              command=lambda d=day: self._select_date(d)).grid(row=r+1, column=c, padx=1, pady=1)
    def _prev_month(self):
        self.month -= 1
        if self.month == 0: self.month, self.year = 12, self.year - 1
        self._update_calendar()
    def _next_month(self):
        self.month += 1
        if self.month == 13: self.month, self.year = 1, self.year + 1
        self._update_calendar()
    def _select_date(self, day):
        self.callback(f"{day:02d}-{self.month:02d}-{self.year}")
        self.destroy()

def show_msg(parent, title, msg, is_error=False): CustomMessageDialog(parent, title, msg, is_error)
def ask_yes_no(parent, title, msg): d = CustomAskYesNo(parent, title, msg); return d.result
def ask_string(parent, title, prompt, show=None): d = CustomAskString(parent, title, prompt, show); return d.result

# --- Scrollable Frame ---
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, bg_color=COLORS["bg_main"], *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style="Card.TFrame")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas.create_window((0,0), window=self.scrollable_frame, anchor="nw"), width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.scrollable_frame.bind('<Enter>', lambda e: self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")))
        self.scrollable_frame.bind('<Leave>', lambda e: self.canvas.unbind_all("<MouseWheel>"))

# --- Main Application ---
class NoteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1150x750")
        try: self.iconbitmap("icon.ico")
        except: pass
        self.configure(bg=COLORS["bg_main"])
        self._setup_styles()
        self.db = DatabaseManager()
        self.current_project = None
        self.current_note_id = None
        self.search_matches = [] 
        self.current_match_index = -1
        self.container = ttk.Frame(self, style="Main.TFrame")
        self.container.pack(fill="both", expand=True)
        self.show_projects_view()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        self.default_font = font.Font(family="Segoe UI", size=10)
        self.bold_font = font.Font(family="Segoe UI", size=10, weight="bold")
        self.italic_font = font.Font(family="Segoe UI", size=10, slant="italic")
        self.heading_font = font.Font(family="Segoe UI", size=14, weight="bold")
        style.configure("TFrame", background=COLORS["bg_main"])
        style.configure("Main.TFrame", background=COLORS["bg_main"])
        style.configure("Card.TFrame", background=COLORS["bg_main"])
        style.configure("TLabel", background=COLORS["bg_main"], foreground=COLORS["fg_text"], font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=COLORS["fg_text"], background=COLORS["bg_main"])
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground=COLORS["fg_sub"], background=COLORS["bg_main"])
        style.configure("TButton", font=("Segoe UI", 9, "bold"), background=COLORS["bg_sec"], foreground=COLORS["fg_text"], borderwidth=1)
        style.map("TButton", background=[("active", COLORS["bg_hover"])])
        style.configure("Tool.TButton", font=("Segoe UI", 9), padding=2, background=COLORS["bg_sec"])
        style.map("Tool.TButton", background=[("active", COLORS["bg_active"]), ("pressed", COLORS["bg_active"])])
        style.configure("Delete.TButton", font=("Segoe UI", 8), background=COLORS["bg_main"], foreground="#A00", borderwidth=0)
        style.map("Delete.TButton", background=[("active", "#FFE0E0")])
        style.configure("TEntry", fieldbackground=COLORS["white"], bordercolor=COLORS["bg_sec"])

    def clear_container(self):
        self.auto_save_current()
        for widget in self.container.winfo_children(): widget.destroy()

    def show_projects_view(self):
        self.clear_container()
        self.current_note_id = None
        top_bar = ttk.Frame(self.container, padding=(40, 30))
        top_bar.pack(fill="x")
        title_frame = ttk.Frame(top_bar)
        title_frame.pack(side="left")
        ttk.Label(title_frame, text="My Notebooks", style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_frame, text="Manage your projects and thoughts", style="Sub.TLabel").pack(anchor="w")
        ctrl_frame = ttk.Frame(top_bar)
        ctrl_frame.pack(side="right")
        self.proj_search_var = tk.StringVar()
        self.proj_search_var.trace("w", lambda n,i,m: self.refresh_project_list())
        e_search = ttk.Entry(ctrl_frame, textvariable=self.proj_search_var, width=25)
        e_search.pack(side="left", padx=10)
        ttk.Button(ctrl_frame, text="+ New Notebook", command=self.open_new_project_dialog).pack(side="left")
        list_header = ttk.Frame(self.container, padding=(40, 10))
        list_header.pack(fill="x")
        ttk.Label(list_header, text="NOTE", font=("Segoe UI", 8, "bold"), width=35).pack(side="left")
        ttk.Label(list_header, text="DESCRIPTION", font=("Segoe UI", 8, "bold")).pack(side="left", padx=20)
        list_area = ttk.Frame(self.container, padding=(40, 0, 40, 40))
        list_area.pack(fill="both", expand=True)
        self.proj_scroll = ScrollableFrame(list_area, bg_color=COLORS["bg_main"])
        self.proj_scroll.pack(fill="both", expand=True)
        self.refresh_project_list()

    def refresh_project_list(self):
        for w in self.proj_scroll.scrollable_frame.winfo_children(): w.destroy()
        projects = self.db.get_projects(self.proj_search_var.get())
        if not projects:
            ttk.Label(self.proj_scroll.scrollable_frame, text="No notebooks found.", padding=20).pack()
        for row in projects: self.create_project_row(row)

    def create_project_row(self, row_data):
        pid, name, desc, created, password = row_data
        row = tk.Frame(self.proj_scroll.scrollable_frame, bg=COLORS["white"], pady=12, padx=10, bd=1, relief="solid")
        row.pack(fill="x", pady=5)
        def try_open(e, p=pid, n=name, pwd=password):
            if pwd:
                inp = ask_string(self, "Password Required", f"Enter password for '{n}':", show='*')
                if inp == pwd: self.open_project_detail(p, n)
                elif inp is not None: show_msg(self, "Error", "Incorrect password.", True)
            else:
                self.open_project_detail(p, n)
        info_frame = tk.Frame(row, bg=COLORS["white"])
        info_frame.pack(side="left", fill="both", expand=True)
        name_text = f"🔒 {name}" if password else name
        l_name = tk.Label(info_frame, text=name_text, font=("Segoe UI", 12, "bold"), fg=COLORS["fg_text"], bg=COLORS["white"], width=30, anchor="w")
        l_name.pack(side="left")
        l_desc = tk.Label(info_frame, text=desc, font=("Segoe UI", 10), fg=COLORS["fg_sub"], bg=COLORS["white"], anchor="w")
        l_desc.pack(side="left", fill="x", padx=20)
        meta_frame = tk.Frame(row, bg=COLORS["white"])
        meta_frame.pack(side="right")
        tk.Label(meta_frame, text=f"Created: {created}", font=("Segoe UI", 8), fg="#888", bg=COLORS["white"]).pack(side="left", padx=15)
        ttk.Button(meta_frame, text="Delete", style="Delete.TButton", command=lambda: self.confirm_delete_project(pid)).pack(side="right", padx=5)
        for w in [row, info_frame, l_name, l_desc, meta_frame]: w.bind("<Button-1>", try_open)

    def confirm_delete_project(self, pid):
        if ask_yes_no(self, "Delete Notebook", "Are you sure? This will delete all notes and tasks inside."):
            self.db.delete_project(pid)
            self.refresh_project_list()

    def open_project_detail(self, pid, name):
        self.clear_container()
        self.current_project = pid
        self.current_note_id = None
        header = ttk.Frame(self.container, padding=(20, 10))
        header.pack(fill="x")
        ttk.Button(header, text="← Back", command=self.show_projects_view, width=8).pack(side="left", padx=(0, 20))
        ttk.Label(header, text=name, style="Header.TLabel").pack(side="left")
        tools_frame = ttk.Frame(header)
        tools_frame.pack(side="right")
        ttk.Button(tools_frame, text="Export PDF", style="Tool.TButton", command=self.open_export_dialog).pack(side="left", padx=5)
        has_pass = self.db.get_project_password(pid)
        if has_pass:
            ttk.Button(tools_frame, text="Change Password", style="Tool.TButton", command=self.change_password_dialog).pack(side="left", padx=5)
            ttk.Button(tools_frame, text="Remove Lock", style="Tool.TButton", command=self.remove_password_dialog).pack(side="left", padx=5)
        else:
            ttk.Button(tools_frame, text="Set Password", style="Tool.TButton", command=self.set_password_dialog).pack(side="left", padx=5)
        
        paned = tk.PanedWindow(self.container, orient=tk.HORIZONTAL, bg=COLORS["bg_sec"], sashwidth=4)
        paned.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        pane_notes = tk.Frame(paned, bg=COLORS["bg_main"])
        paned.add(pane_notes, width=280)
        n_tool = tk.Frame(pane_notes, bg=COLORS["bg_sec"], pady=5, padx=5)
        n_tool.pack(fill="x")
        self.note_search_var = tk.StringVar()
        self.note_search_var.trace("w", lambda n,i,m: self.refresh_notes_list())
        ttk.Entry(n_tool, textvariable=self.note_search_var).pack(side="left", fill="x", expand=True)
        ttk.Button(n_tool, text="+", width=3, command=self.create_new_note).pack(side="right", padx=(5,0))
        self.note_scroll = ScrollableFrame(pane_notes, bg_color=COLORS["bg_main"])
        self.note_scroll.pack(fill="both", expand=True)
        
        pane_editor = tk.Frame(paned, bg=COLORS["white"])
        paned.add(pane_editor, width=500)
        self.editor_toolbar = tk.Frame(pane_editor, bg="#eee", pady=5, padx=5)
        fmt_frame = tk.Frame(self.editor_toolbar, bg="#eee")
        fmt_frame.pack(side="left", padx=(0, 10))
        ttk.Button(fmt_frame, text="B", width=2, style="Tool.TButton", command=lambda: self.toggle_format("bold")).pack(side="left", padx=1)
        ttk.Button(fmt_frame, text="I", width=2, style="Tool.TButton", command=lambda: self.toggle_format("italic")).pack(side="left", padx=1)
        ttk.Button(fmt_frame, text="U", width=2, style="Tool.TButton", command=lambda: self.toggle_format("underline")).pack(side="left", padx=1)
        self.btn_bullet = ttk.Button(fmt_frame, text="•", width=2, style="Tool.TButton", command=lambda: self.insert_smart_list("bullet"))
        self.btn_bullet.pack(side="left", padx=1)
        self.btn_number = ttk.Button(fmt_frame, text="1.", width=2, style="Tool.TButton", command=lambda: self.insert_smart_list("number"))
        self.btn_number.pack(side="left", padx=1)
        search_frame = tk.Frame(self.editor_toolbar, bg="#eee")
        search_frame.pack(side="left", padx=10)
        self.editor_search_var = tk.StringVar()
        self.editor_search_var.trace("w", self.on_search_type)
        self.e_editor_search = ttk.Entry(search_frame, textvariable=self.editor_search_var, width=15)
        self.e_editor_search.pack(side="left")
        self.e_editor_search.bind("<Return>", lambda e: self.navigate_search("next"))
        self.e_editor_search.bind("<Down>", lambda e: self.navigate_search("next"))
        self.e_editor_search.bind("<Up>", lambda e: self.navigate_search("prev"))
        
        # FIX: Separate widget creation from binding
        lbl_clear = tk.Label(search_frame, text="✕", bg="#eee", fg="#999", cursor="hand2")
        lbl_clear.pack(side="left", padx=(2, 5))
        lbl_clear.bind("<Button-1>", self.clear_search)
        
        self.lbl_search_count = tk.Label(search_frame, text="", bg="#eee", fg=COLORS["fg_sub"], font=("Segoe UI", 9))
        self.lbl_search_count.pack(side="left")
        self.btn_del_note = ttk.Button(self.editor_toolbar, text="Delete Note", style="Delete.TButton", command=self.delete_current_note)
        self.btn_del_note.pack(side="right", padx=5)
        self.editor_text = tk.Text(pane_editor, font=self.default_font, wrap="word", bd=0, padx=20, pady=20, bg=COLORS["white"], fg=COLORS["fg_text"])
        self.editor_text.tag_configure("bold", font=self.bold_font)
        self.editor_text.tag_configure("italic", font=self.italic_font)
        self.editor_text.tag_configure("underline", underline=True)
        self.editor_text.tag_configure("heading", font=self.heading_font)
        self.editor_text.tag_configure("search_hi", background=COLORS["search_hi"])
        self.editor_text.tag_configure("search_active", background=COLORS["search_active"], foreground="white")
        self.editor_text.bind("<KeyRelease>", self.on_text_activity)
        self.editor_text.bind("<ButtonRelease-1>", self.on_text_activity)
        
        pane_todo = tk.Frame(paned, bg=COLORS["bg_main"])
        paned.add(pane_todo, width=280)
        t_head = tk.Frame(pane_todo, bg=COLORS["bg_sec"], pady=8, padx=10)
        t_head.pack(fill="x")
        tk.Label(t_head, text="Todo", font=("Segoe UI", 10, "bold"), bg=COLORS["bg_sec"], fg=COLORS["fg_text"]).pack(anchor="w")
        t_input = tk.Frame(pane_todo, bg=COLORS["bg_main"], pady=5)
        t_input.pack(fill="x")
        self.e_task = ttk.Entry(t_input, width=15)
        self.e_task.pack(side="left", fill="x", expand=True, padx=(5,0))
        self.e_date = ttk.Entry(t_input, width=12, justify="center")
        self.e_date.insert(0, "DD-MM-YYYY")
        self.e_date.bind("<FocusIn>", lambda e: self.e_date.delete(0, "end") if "D" in self.e_date.get() else None)
        self.e_date.pack(side="left", padx=5)
        tk.Button(t_input, text="📅", width=3, bg=COLORS["bg_sec"], relief="flat", command=lambda: CalendarDialog(self, lambda d: (self.e_date.delete(0,"end"), self.e_date.insert(0,d)))).pack(side="left", padx=2)
        self.e_task.bind("<Return>", lambda e: self.add_task())
        self.e_date.bind("<Return>", lambda e: self.add_task())
        ttk.Button(t_input, text="Add", width=4, command=self.add_task).pack(side="right", padx=(0,5))
        self.todo_scroll = ScrollableFrame(pane_todo, bg_color=COLORS["bg_main"])
        self.todo_scroll.pack(fill="both", expand=True)
        self.refresh_notes_list()
        self.refresh_todo_list()

    def refresh_notes_list(self):
        for w in self.note_scroll.scrollable_frame.winfo_children(): w.destroy()
        notes = self.db.get_notes(self.current_project, self.note_search_var.get())
        for nid, pid, title, ts in notes:
            item = tk.Frame(self.note_scroll.scrollable_frame, bg=COLORS["white"], bd=1, relief="solid")
            item.pack(fill="x", pady=2, padx=2)
            def select_wrapper(e, n=nid): self.auto_save_current(); self.load_editor(n)
            f = tk.Frame(item, bg=COLORS["white"], padx=8, pady=8)
            f.pack(fill="x")
            tk.Label(f, text=title, font=("Segoe UI", 10, "bold"), bg=COLORS["white"], anchor="w", fg=COLORS["fg_text"]).pack(fill="x")
            tk.Label(f, text=ts, font=("Segoe UI", 8), fg="#999", bg=COLORS["white"], anchor="w").pack(fill="x")
            for w in [item, f] + f.winfo_children(): w.bind("<Button-1>", select_wrapper)

    def load_editor(self, nid):
        self.current_note_id = nid
        fresh_content = self.db.get_note_content(nid)
        self.clear_search(None)
        self.editor_toolbar.pack(side="top", fill="x")
        self.editor_text.pack(fill="both", expand=True)
        self.editor_text.delete("1.0", "end")
        self.editor_text.insert("1.0", fresh_content)
        self.on_text_activity(None)

    def create_new_note(self):
        self.auto_save_current()
        nid = self.db.add_note(self.current_project)
        self.refresh_notes_list()
        self.load_editor(nid)

    def auto_save_current(self):
        if self.current_note_id:
            content = self.editor_text.get("1.0", "end-1c")
            self.db.update_note(self.current_note_id, content)
            self.refresh_notes_list()

    def delete_current_note(self):
        if self.current_note_id and ask_yes_no(self, "Delete", "Delete this note?"):
            self.db.delete_note(self.current_note_id)
            self.current_note_id = None
            self.editor_toolbar.pack_forget()
            self.editor_text.pack_forget()
            self.refresh_notes_list()

    def add_task(self):
        task = self.e_task.get().strip()
        date = self.e_date.get().strip()
        if "D" in date: date = ""
        if task:
            self.db.add_todo(self.current_project, task, date)
            self.e_task.delete(0, "end")
            self.refresh_todo_list()

    def refresh_todo_list(self):
        for w in self.todo_scroll.scrollable_frame.winfo_children(): w.destroy()
        todos = self.db.get_todos(self.current_project)
        for tid, pid, task, date, is_done, _ in todos:
            row = tk.Frame(self.todo_scroll.scrollable_frame, bg=COLORS["white"], pady=2)
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=bool(is_done))
            def toggle(t=tid, v=var): self.db.toggle_todo(t, v.get()); self.refresh_todo_list()
            tk.Checkbutton(row, variable=var, command=lambda: toggle(tid, var), bg=COLORS["white"], activebackground=COLORS["white"]).pack(side="left")
            fg_col = "#aaa" if is_done else COLORS["fg_text"]
            tk.Label(row, text=task, bg=COLORS["white"], fg=fg_col, wraplength=140, justify="left", anchor="w").pack(side="left", fill="x", expand=True)
            if date: tk.Label(row, text=date, bg=COLORS["white"], fg=COLORS["accent"], font=("Segoe UI", 8)).pack(side="left", padx=5)
            btn_del = tk.Label(row, text="✕", fg="#aaa", bg=COLORS["white"], cursor="hand2")
            btn_del.pack(side="right", padx=5)
            btn_del.bind("<Button-1>", lambda e, t=tid: self.delete_task(t))

    def delete_task(self, tid):
        self.db.delete_todo(tid)
        self.refresh_todo_list()

    def open_export_dialog(self):
        d = CustomDialog(self, "Export PDF", 300, 150)
        tk.Label(d, text="Select Export Mode", bg=COLORS["bg_main"], font=("Segoe UI", 10, "bold")).pack(pady=15)
        f = tk.Frame(d, bg=COLORS["bg_main"])
        f.pack(pady=10)
        ttk.Button(f, text="Current Note", command=lambda: [d.destroy(), self.generate_pdf_export("current")]).pack(side="left", padx=10)
        ttk.Button(f, text="Whole Notebook", command=lambda: [d.destroy(), self.generate_pdf_export("notebook")]).pack(side="left", padx=10)

    def generate_pdf_export(self, mode):
        if not HAS_PDF_SUPPORT: return show_msg(self, "Error", "PDF support missing. Run: pip install reportlab", True)
        data = []
        if mode == "current":
            if not self.current_note_id: return show_msg(self, "Error", "No note selected!", True)
            data.append((self.editor_text.get("1.0", "1.end"), self.editor_text.get("1.0", "end-1c")))
            hint = data[0][0]
        else:
            data = self.db.get_all_notes_content(self.current_project)
            if not data: return show_msg(self, "Info", "Notebook is empty.", True)
            hint = "Notebook_Export"
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="".join([c for c in hint if c.isalnum() or c==' ']).strip(), filetypes=[("PDF", "*.pdf")])
        if not path: return
        try:
            doc = SimpleDocTemplate(path, pagesize=letter)
            styles = getSampleStyleSheet()
            style_t = ParagraphStyle('MT', parent=styles['Heading1'], alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=14, spaceAfter=12)
            style_b = ParagraphStyle('MB', parent=styles['BodyText'], alignment=TA_JUSTIFY, fontName='Helvetica', fontSize=12, leading=14)
            story = []
            for title, content in data:
                story.append(Paragraph(title, style_t))
                lines = content.split('\n')
                if lines and lines[0].strip() == title.strip(): lines = lines[1:]
                for p in lines:
                    if p.strip(): story.append(Paragraph(p, style_b)); story.append(Spacer(1, 6))
                if mode == "notebook": story.append(PageBreak())
            doc.build(story, onFirstPage=lambda c,d: c.drawCentredString(letter[0]/2, 20, str(c.getPageNumber())), onLaterPages=lambda c,d: c.drawCentredString(letter[0]/2, 20, str(c.getPageNumber())))
            show_msg(self, "Success", "PDF Exported!")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def set_password_dialog(self):
        pwd = ask_string(self, "Set Password", "Enter new password:", show='*')
        if pwd: self.db.set_project_password(self.current_project, pwd); show_msg(self, "Success", "Password set!"); self.open_project_detail(self.current_project, self.db.cursor.execute("SELECT name FROM projects WHERE id=?",(self.current_project,)).fetchone()[0])

    def change_password_dialog(self):
        pwd = ask_string(self, "Change Password", "Enter new password:", show='*')
        if pwd: self.db.set_project_password(self.current_project, pwd); show_msg(self, "Success", "Password changed!")

    def remove_password_dialog(self):
        if ask_yes_no(self, "Remove Lock", "Remove password?"): self.db.set_project_password(self.current_project, None); show_msg(self, "Success", "Lock removed."); self.open_project_detail(self.current_project, self.db.cursor.execute("SELECT name FROM projects WHERE id=?",(self.current_project,)).fetchone()[0])

    def open_new_project_dialog(self):
        d = CustomDialog(self, "New Notebook", 400, 250)
        tk.Label(d, text="Notebook Name", bg=COLORS["bg_main"], font=("Segoe UI", 10, "bold")).pack(pady=(20,5))
        e1 = ttk.Entry(d, width=40); e1.pack(pady=5)
        tk.Label(d, text="Description", bg=COLORS["bg_main"]).pack(pady=5)
        e2 = ttk.Entry(d, width=40); e2.pack(pady=5)
        def save():
            if e1.get(): self.db.add_project(e1.get(), e2.get()); d.destroy(); self.refresh_project_list()
        ttk.Button(d, text="Create", command=save).pack(pady=20)

    def on_text_activity(self, event):
        self.editor_text.tag_remove("heading", "1.0", "end")
        self.editor_text.tag_add("heading", "1.0", "1.end")
        try:
            line = self.editor_text.get("insert linestart", "insert lineend")
            self._set_btn_active(self.btn_bullet, bool(re.match(r"^\s*•\s*", line)))
            self._set_btn_active(self.btn_number, bool(re.match(r"^\s*\d+\.\s*", line)))
        except: pass

    def _set_btn_active(self, btn, is_active): btn.state(["pressed"] if is_active else ["!pressed"])
    def toggle_format(self, tag):
        try: self.editor_text.tag_remove(tag, "sel.first", "sel.last") if tag in self.editor_text.tag_names("sel.first") else self.editor_text.tag_add(tag, "sel.first", "sel.last")
        except: pass
    def insert_smart_list(self, type):
        try: start, end = self.editor_text.index("sel.first"), self.editor_text.index("sel.last")
        except: start = end = self.editor_text.index("insert")
        start, end = f"{start} linestart", f"{end} lineend"
        lines = self.editor_text.get(start, end).split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            clean = re.sub(r"^\s*(•|\d+\.)\s*", "", line)
            if not clean.strip() and len(lines) > 1: new_lines.append(""); continue
            if type == "bullet": new_lines.append(clean if re.match(r"^\s*•", line) else f" • {clean}")
            else: new_lines.append(clean if re.match(r"^\s*\d+\.", line) else f" {i+1}. {clean}")
        self.editor_text.delete(start, end); self.editor_text.insert(start, "\n".join(new_lines)); self.on_text_activity(None)
    def clear_search(self, event): self.editor_search_var.set(""); self.lbl_search_count.config(text=""); self.editor_text.tag_remove("search_hi", "1.0", "end"); self.editor_text.tag_remove("search_active", "1.0", "end"); self.search_matches = []
    def on_search_type(self, *args):
        self.editor_text.tag_remove("search_hi", "1.0", "end"); self.editor_text.tag_remove("search_active", "1.0", "end"); self.search_matches = []
        q = self.editor_search_var.get()
        if not q: return self.lbl_search_count.config(text="")
        pos = "1.0"
        while True:
            pos = self.editor_text.search(q, pos, stopindex="end", nocase=True)
            if not pos: break
            end = f"{pos}+{len(q)}c"; self.search_matches.append((pos, end)); self.editor_text.tag_add("search_hi", pos, end); pos = end
        self.lbl_search_count.config(text="Not Found" if not self.search_matches else f"0/{len(self.search_matches)}")
    def navigate_search(self, direction):
        if not self.search_matches: return
        self.editor_text.tag_remove("search_active", "1.0", "end")
        self.current_match_index = (self.current_match_index + (1 if direction == "next" else -1)) % len(self.search_matches)
        start, end = self.search_matches[self.current_match_index]
        self.editor_text.tag_add("search_active", start, end); self.editor_text.see(start); self.lbl_search_count.config(text=f"{self.current_match_index+1}/{len(self.search_matches)}")

if __name__ == "__main__":
    app = NoteApp()
    app.mainloop()
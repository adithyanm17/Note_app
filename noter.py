import tkinter as tk
from tkinter import ttk, messagebox, font, filedialog, simpledialog
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
    from reportlab.lib.units import inch
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
        """Adds columns to existing databases if missing."""
        try:
            self.cursor.execute("ALTER TABLE todos ADD COLUMN due_date TEXT")
            self.conn.commit()
        except sqlite3.OperationalError: pass
        
        try:
            self.cursor.execute("ALTER TABLE projects ADD COLUMN password TEXT")
            self.conn.commit()
        except sqlite3.OperationalError: pass

    # --- Project Ops ---
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

    # --- Note Ops ---
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

    # --- Todo Ops ---
    def add_todo(self, project_id, task, due_date=""):
        self.cursor.execute("INSERT INTO todos (project_id, task, due_date, created_at) VALUES (?, ?, ?, ?)",
                            (project_id, task, due_date, datetime.now().strftime("%Y-%m-%d")))
        self.conn.commit()

    def get_todos(self, project_id):
        # Explicitly select columns to avoid ordering issues with migrated databases
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

# --- Calendar Dialog Class ---
class CalendarDialog(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("Select Date")
        self.geometry("250x250")
        self.iconbitmap("icon.ico")
        self.configure(bg=COLORS["bg_main"])
        self.resizable(False, False)
        
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
        for widget in self.cal_frame.winfo_children():
            widget.destroy()
            
        self.lbl_month.config(text=f"{calendar.month_name[self.month]} {self.year}")
        
        # Days Header
        days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        for i, day in enumerate(days):
            tk.Label(self.cal_frame, text=day, bg=COLORS["bg_main"], fg=COLORS["accent"], font=("Segoe UI", 8, "bold")).grid(row=0, column=i)
            
        # Days Grid
        cal = calendar.monthcalendar(self.year, self.month)
        for r, week in enumerate(cal):
            for c, day in enumerate(week):
                if day != 0:
                    btn = tk.Button(self.cal_frame, text=str(day), width=3, relief="flat", bg=COLORS["white"],
                                    command=lambda d=day: self._select_date(d))
                    btn.grid(row=r+1, column=c, padx=1, pady=1)

    def _prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self._update_calendar()

    def _next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self._update_calendar()

    def _select_date(self, day):
        date_str = f"{day:02d}-{self.month:02d}-{self.year}"
        self.callback(date_str)
        self.destroy()

# --- Helper: Smart Scrollable Frame ---
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, bg_color=COLORS["bg_main"], *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style="Card.TFrame")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', self._configure_window_width)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.scrollable_frame.bind('<Enter>', self._bound_to_mousewheel)
        self.scrollable_frame.bind('<Leave>', self._unbound_to_mousewheel)

    def _configure_window_width(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

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
        for widget in self.container.winfo_children():
            widget.destroy()

    # ==========================
    # VIEW 1: PROJECTS LIST
    # ==========================
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
        ttk.Label(list_header, text="PROJECT NAME", font=("Segoe UI", 8, "bold"), width=35).pack(side="left")
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
        for row in projects:
            self.create_project_row(row)

    def create_project_row(self, row_data):
        pid, name, desc, created, password = row_data
        
        row = tk.Frame(self.proj_scroll.scrollable_frame, bg=COLORS["white"], pady=12, padx=10, bd=1, relief="solid")
        row.pack(fill="x", pady=5)
        
        def try_open(e, p=pid, n=name, pwd=password):
            if pwd:
                inp = simpledialog.askstring("Password Required", f"Enter password for '{n}':", show='*')
                if inp == pwd:
                    self.open_project_detail(p, n)
                elif inp is not None:
                    messagebox.showerror("Error", "Incorrect password.")
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
        l_time = tk.Label(meta_frame, text=f"Created: {created}", font=("Segoe UI", 8), fg="#888", bg=COLORS["white"])
        l_time.pack(side="left", padx=15)
        btn_del = ttk.Button(meta_frame, text="Delete", style="Delete.TButton", command=lambda: self.confirm_delete_project(pid))
        btn_del.pack(side="right", padx=5)

        for w in [row, info_frame, l_name, l_desc, meta_frame, l_time]:
            w.bind("<Button-1>", try_open)

    def confirm_delete_project(self, pid):
        if messagebox.askyesno("Delete Notebook", "Are you sure? This will delete all notes and tasks inside."):
            self.db.delete_project(pid)
            self.refresh_project_list()

    # ==========================
    # VIEW 2: PROJECT DETAIL
    # ==========================
    def open_project_detail(self, pid, name):
        self.clear_container()
        self.current_project = pid
        self.current_note_id = None
        
        header = ttk.Frame(self.container, padding=(20, 10))
        header.pack(fill="x")
        btn_back = ttk.Button(header, text="← Back", command=self.show_projects_view, width=8)
        btn_back.pack(side="left", padx=(0, 20))
        
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

        # --- PANE 1: NOTES LIST ---
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

        # --- PANE 2: EDITOR ---
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
        
        lbl_clear = tk.Label(search_frame, text="✕", bg="#eee", fg="#999", cursor="hand2")
        lbl_clear.pack(side="left", padx=(2, 5))
        lbl_clear.bind("<Button-1>", self.clear_search)
        self.lbl_search_count = tk.Label(search_frame, text="", bg="#eee", fg=COLORS["fg_sub"], font=("Segoe UI", 9))
        self.lbl_search_count.pack(side="left")

        self.btn_del_note = ttk.Button(self.editor_toolbar, text="Delete Note", style="Delete.TButton", command=self.delete_current_note)
        self.btn_del_note.pack(side="right", padx=5)

        self.editor_text = tk.Text(pane_editor, font=self.default_font, wrap="word", 
                                   bd=0, padx=20, pady=20, bg=COLORS["white"], fg=COLORS["fg_text"])
        
        self.editor_text.tag_configure("bold", font=self.bold_font)
        self.editor_text.tag_configure("italic", font=self.italic_font)
        self.editor_text.tag_configure("underline", underline=True)
        self.editor_text.tag_configure("heading", font=self.heading_font)
        self.editor_text.tag_configure("search_hi", background=COLORS["search_hi"])
        self.editor_text.tag_configure("search_active", background=COLORS["search_active"], foreground="white")
        
        self.editor_text.bind("<KeyRelease>", self.on_text_activity)
        self.editor_text.bind("<ButtonRelease-1>", self.on_text_activity)

        # --- PANE 3: TO-DO ---
        pane_todo = tk.Frame(paned, bg=COLORS["bg_main"])
        paned.add(pane_todo, width=280)
        t_head = tk.Frame(pane_todo, bg=COLORS["bg_sec"], pady=8, padx=10)
        t_head.pack(fill="x")
        tk.Label(t_head, text="Project Tasks", font=("Segoe UI", 10, "bold"), bg=COLORS["bg_sec"], fg=COLORS["fg_text"]).pack(anchor="w")
        
        t_input = tk.Frame(pane_todo, bg=COLORS["bg_main"], pady=5)
        t_input.pack(fill="x")
        
        self.e_task = ttk.Entry(t_input, width=15)
        self.e_task.pack(side="left", fill="x", expand=True, padx=(5,0))
        
        self.e_date = ttk.Entry(t_input, width=12, justify="center")
        self.e_date.insert(0, "DD-MM-YYYY")
        self.e_date.bind("<FocusIn>", lambda e: self.e_date.delete(0, "end") if "D" in self.e_date.get() else None)
        self.e_date.pack(side="left", padx=5)
        
        # Calendar Button
        btn_cal = tk.Button(t_input, text="📅", width=3, bg=COLORS["bg_sec"], relief="flat",
                            command=lambda: CalendarDialog(self, self._set_date_from_cal))
        btn_cal.pack(side="left", padx=2)

        self.e_task.bind("<Return>", lambda e: self.add_task())
        self.e_date.bind("<Return>", lambda e: self.add_task())

        ttk.Button(t_input, text="Add", width=4, command=self.add_task).pack(side="right", padx=(0,5))
        
        self.todo_scroll = ScrollableFrame(pane_todo, bg_color=COLORS["bg_main"])
        self.todo_scroll.pack(fill="both", expand=True)

        self.refresh_notes_list()
        self.refresh_todo_list()

    def _set_date_from_cal(self, date_str):
        self.e_date.delete(0, "end")
        self.e_date.insert(0, date_str)

    # --- Note Logic ---
    def refresh_notes_list(self):
        for w in self.note_scroll.scrollable_frame.winfo_children(): w.destroy()
        notes = self.db.get_notes(self.current_project, self.note_search_var.get())
        for nid, pid, title, ts in notes:
            item = tk.Frame(self.note_scroll.scrollable_frame, bg=COLORS["white"], bd=1, relief="solid")
            item.pack(fill="x", pady=2, padx=2)
            
            def select_wrapper(e, n=nid): 
                self.auto_save_current()
                self.load_editor(n)
            
            f = tk.Frame(item, bg=COLORS["white"], padx=8, pady=8)
            f.pack(fill="x")
            l1 = tk.Label(f, text=title, font=("Segoe UI", 10, "bold"), bg=COLORS["white"], anchor="w", fg=COLORS["fg_text"])
            l1.pack(fill="x")
            l2 = tk.Label(f, text=ts, font=("Segoe UI", 8), fg="#999", bg=COLORS["white"], anchor="w")
            l2.pack(fill="x")
            for w in [item, f, l1, l2]: w.bind("<Button-1>", select_wrapper)

    def load_editor(self, nid, content=None):
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
        if self.current_note_id and messagebox.askyesno("Delete", "Delete this note?"):
            self.db.delete_note(self.current_note_id)
            self.current_note_id = None
            self.editor_toolbar.pack_forget()
            self.editor_text.pack_forget()
            self.refresh_notes_list()

    # --- PDF EXPORT (UPDATED) ---
    def open_export_dialog(self):
        d = tk.Toplevel(self)
        d.title("Export PDF")
        d.geometry("300x150")
        d.iconbitmap("icon.ico")
        d.resizable(False, False)
        d.configure(bg=COLORS["bg_main"])
        
        tk.Label(d, text="Select Export Mode", bg=COLORS["bg_main"], font=("Segoe UI", 10, "bold")).pack(pady=15)
        
        def export(mode):
            d.destroy()
            self.generate_pdf_export(mode)

        f = tk.Frame(d, bg=COLORS["bg_main"])
        f.pack(pady=10)
        ttk.Button(f, text="Current Note", command=lambda: export("current")).pack(side="left", padx=10)
        ttk.Button(f, text="Whole Notebook", command=lambda: export("notebook")).pack(side="left", padx=10)

    def generate_pdf_export(self, mode):
        if not HAS_PDF_SUPPORT:
            messagebox.showerror("Error", "PDF support missing. Run: pip install reportlab")
            return

        data_to_print = [] 
        if mode == "current":
            if not self.current_note_id:
                messagebox.showerror("Error", "No note selected!")
                return
            content = self.editor_text.get("1.0", "end-1c")
            title = content.split('\n')[0][:50] if content else "Untitled"
            data_to_print.append((title, content))
            filename_hint = title
        else:
            data_to_print = self.db.get_all_notes_content(self.current_project)
            if not data_to_print:
                messagebox.showinfo("Info", "Notebook is empty.")
                return
            filename_hint = "Notebook_Export"

        safe_title = "".join([c for c in filename_hint if c.isalpha() or c.isdigit() or c==' ']).strip()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=safe_title,
            filetypes=[("PDF Document", "*.pdf")]
        )
        if not file_path: return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom Styles for Centered Heading and Justified Body
            style_title = ParagraphStyle('MyTitle', parent=styles['Heading1'], alignment=TA_CENTER, fontName='Helvetica-Bold', fontSize=14, spaceAfter=12)
            style_body = ParagraphStyle('MyBody', parent=styles['BodyText'], alignment=TA_JUSTIFY, fontName='Helvetica', fontSize=12, leading=14)

            story = []

            for title, content in data_to_print:
                # Add Heading (Title)
                story.append(Paragraph(title, style_title))
                
                # Split content into lines to check the first line
                lines = content.split('\n')
                
                # Fix Duplication: If first line equals title, skip it
                if lines and lines[0].strip() == title.strip():
                    lines = lines[1:]
                
                for paragraph in lines:
                    if paragraph.strip():
                        story.append(Paragraph(paragraph, style_body))
                        story.append(Spacer(1, 6))
                
                if mode == "notebook":
                    story.append(PageBreak())

            def add_page_number(canvas, doc):
                page_num = canvas.getPageNumber()
                text = "%d" % page_num
                canvas.setFont("Helvetica", 10)
                # Centered Page Number
                canvas.drawCentredString(letter[0] / 2.0, 20, text)

            doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
            messagebox.showinfo("Success", "PDF Exported Successfully!")

        except Exception as e:
            messagebox.showerror("PDF Error", str(e))

    # --- PASSWORD FEATURE ---
    def set_password_dialog(self):
        pwd = simpledialog.askstring("Set Password", "Enter new password:", show='*')
        if pwd:
            self.db.set_project_password(self.current_project, pwd)
            messagebox.showinfo("Success", "Password set successfully!")
            self.open_project_detail(self.current_project, self.db.cursor.execute("SELECT name FROM projects WHERE id=?",(self.current_project,)).fetchone()[0])

    def change_password_dialog(self):
        pwd = simpledialog.askstring("Change Password", "Enter new password:", show='*')
        if pwd:
            self.db.set_project_password(self.current_project, pwd)
            messagebox.showinfo("Success", "Password changed!")

    def remove_password_dialog(self):
        if messagebox.askyesno("Remove Lock", "Are you sure you want to remove the password?"):
            self.db.set_project_password(self.current_project, None)
            messagebox.showinfo("Success", "Lock removed.")
            self.open_project_detail(self.current_project, self.db.cursor.execute("SELECT name FROM projects WHERE id=?",(self.current_project,)).fetchone()[0])

    # --- Text Activity Handler ---
    def on_text_activity(self, event):
        self.editor_text.tag_remove("heading", "1.0", "end")
        self.editor_text.tag_add("heading", "1.0", "1.end")

        try:
            current_idx = self.editor_text.index("insert")
            line_content = self.editor_text.get(f"{current_idx} linestart", f"{current_idx} lineend")
            
            if re.match(r"^\s*•\s*", line_content):
                self._set_btn_active(self.btn_bullet, True)
            else:
                self._set_btn_active(self.btn_bullet, False)

            if re.match(r"^\s*\d+\.\s*", line_content):
                self._set_btn_active(self.btn_number, True)
            else:
                self._set_btn_active(self.btn_number, False)
        except:
            pass

    def _set_btn_active(self, btn, is_active):
        if is_active:
             btn.state(["pressed"]) 
        else:
             btn.state(["!pressed"])

    def toggle_format(self, tag_name):
        try:
            if tag_name in self.editor_text.tag_names("sel.first"):
                self.editor_text.tag_remove(tag_name, "sel.first", "sel.last")
            else:
                self.editor_text.tag_add(tag_name, "sel.first", "sel.last")
        except tk.TclError: pass

    # --- Smart List Logic ---
    def insert_smart_list(self, list_type="bullet"):
        try:
            start = self.editor_text.index("sel.first")
            end = self.editor_text.index("sel.last")
        except tk.TclError:
            start = self.editor_text.index("insert linestart")
            end = self.editor_text.index("insert lineend")

        text_block = self.editor_text.get(start, end)
        lines = text_block.split('\n')
        new_lines = []
        
        pat_bullet = re.compile(r"^\s*•\s*") 
        pat_number = re.compile(r"^\s*\d+\.\s*")

        for i, line in enumerate(lines):
            is_bullet = bool(pat_bullet.match(line))
            is_number = bool(pat_number.match(line))
            
            clean_line = pat_bullet.sub("", line)
            clean_line = pat_number.sub("", clean_line)
            clean_line = clean_line.strip()

            if not clean_line and len(lines) > 1: 
                 new_lines.append("")
                 continue

            if list_type == "bullet":
                if is_bullet: 
                    new_lines.append(clean_line)
                else: 
                    new_lines.append(f" • {clean_line}")
            
            elif list_type == "number":
                if is_number:
                    new_lines.append(clean_line)
                else:
                    new_lines.append(f" {i+1}. {clean_line}")

        self.editor_text.delete(start, end)
        self.editor_text.insert(start, "\n".join(new_lines))
        self.on_text_activity(None) 

    # --- Instant Search Logic ---
    def clear_search(self, event):
        self.editor_search_var.set("")
        self.lbl_search_count.config(text="")
        self.editor_text.tag_remove("search_hi", "1.0", "end")
        self.editor_text.tag_remove("search_active", "1.0", "end")
        self.search_matches = []
        self.current_match_index = -1

    def on_search_type(self, *args):
        self.editor_text.tag_remove("search_hi", "1.0", "end")
        self.editor_text.tag_remove("search_active", "1.0", "end")
        self.search_matches = []
        self.current_match_index = -1
        
        query = self.editor_search_var.get()
        if not query:
            self.lbl_search_count.config(text="")
            return

        start_pos = "1.0"
        while True:
            pos = self.editor_text.search(query, start_pos, stopindex="end", nocase=True)
            if not pos: break
            length = len(query)
            end_pos = f"{pos}+{length}c"
            self.search_matches.append((pos, end_pos))
            self.editor_text.tag_add("search_hi", pos, end_pos)
            start_pos = end_pos
            
        count = len(self.search_matches)
        if count == 0:
            self.lbl_search_count.config(text="Not Found")
        else:
            self.lbl_search_count.config(text=f"0/{count}")

    def navigate_search(self, direction="next"):
        if not self.search_matches: return
        self.editor_text.tag_remove("search_active", "1.0", "end")
        count = len(self.search_matches)
        
        if direction == "next":
            self.current_match_index = (self.current_match_index + 1) % count
        else:
            self.current_match_index = (self.current_match_index - 1) % count
            
        start, end = self.search_matches[self.current_match_index]
        self.editor_text.tag_add("search_active", start, end)
        self.editor_text.see(start)
        self.lbl_search_count.config(text=f"{self.current_match_index + 1}/{count}")

    # --- Todo Logic ---
    def add_task(self):
        task = self.e_task.get().strip()
        date = self.e_date.get().strip()
        if "D" in date: date = "" # Handle placeholder

        if task:
            self.db.add_todo(self.current_project, task, date)
            self.e_task.delete(0, "end")
            self.refresh_todo_list()

    def refresh_todo_list(self):
        for w in self.todo_scroll.scrollable_frame.winfo_children(): w.destroy()
        # Returns: id, project_id, task, due_date, is_done, created_at
        todos = self.db.get_todos(self.current_project)
        
        for tid, pid, task, date, is_done, _ in todos:
            row = tk.Frame(self.todo_scroll.scrollable_frame, bg=COLORS["white"], pady=2)
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=is_done)
            def toggle(t=tid, v=var):
                self.db.toggle_todo(t, v.get())
                self.refresh_todo_list()
            cb = tk.Checkbutton(row, variable=var, command=toggle, bg=COLORS["white"], activebackground=COLORS["white"])
            cb.pack(side="left")
            fg_col = "#aaa" if is_done else COLORS["fg_text"]
            lbl = tk.Label(row, text=task, bg=COLORS["white"], fg=fg_col, wraplength=140, justify="left", anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            
            # Show Date if exists
            if date:
                l_date = tk.Label(row, text=date, bg=COLORS["white"], fg=COLORS["accent"], font=("Segoe UI", 8))
                l_date.pack(side="left", padx=5)

            btn_del = tk.Label(row, text="✕", fg="#aaa", bg=COLORS["white"], cursor="hand2")
            btn_del.pack(side="right", padx=5)
            btn_del.bind("<Button-1>", lambda e, t=tid: self.delete_task(t))

    def delete_task(self, tid):
        self.db.delete_todo(tid)
        self.refresh_todo_list()

    # --- Dialogs ---
    def open_new_project_dialog(self):
        d = tk.Toplevel(self)
        d.title("New Notebook")
        d.geometry("400x250")
        try: d.iconbitmap("icon.ico")
        except: pass
        d.configure(bg=COLORS["bg_main"])
        tk.Label(d, text="Notebook Name", bg=COLORS["bg_main"], font=("Segoe UI", 10, "bold")).pack(pady=(20,5))
        e1 = ttk.Entry(d, width=40)
        e1.pack(pady=5)
        tk.Label(d, text="Description", bg=COLORS["bg_main"]).pack(pady=5)
        e2 = ttk.Entry(d, width=40)
        e2.pack(pady=5)
        def save():
            if e1.get():
                self.db.add_project(e1.get(), e2.get())
                d.destroy()
                self.refresh_project_list()
        ttk.Button(d, text="Create", command=save).pack(pady=20)

if __name__ == "__main__":
    app = NoteApp()
    app.mainloop()
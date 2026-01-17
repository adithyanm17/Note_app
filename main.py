# main.py
import tkinter as tk
from tkinter import ttk, font, filedialog
import re
import os
import json
from config import APP_NAME, COLORS
from database import DatabaseManager
from whiteboard import Whiteboard
from ui_shared import (
    ScrollableFrame, CalendarDialog, show_msg, 
    ask_yes_no, ask_string
)

# --- Optional Dependencies ---
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as PDFImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from spellchecker import SpellChecker
    HAS_SPELL = True
    spell = SpellChecker()
except ImportError:
    HAS_SPELL = False

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
        
        # Search Vars
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
        self.heading_font = font.Font(family="Segoe UI", size=16, weight="bold")
        
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
        if hasattr(self, 'editor_text'): 
            self.auto_save_current()
        for widget in self.container.winfo_children(): widget.destroy()

    # --- PROJECT VIEW ---
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
        pwd = self.db.get_project_password(pid)
        if pwd:
            inp = ask_string(self, "Password Required", "Enter password to delete:", show='*')
            if inp != pwd: return show_msg(self, "Error", "Incorrect password.", True)
        if ask_yes_no(self, "Delete Notebook", "Are you sure? This will delete all notes and tasks inside."):
            self.db.delete_project(pid)
            self.refresh_project_list()

    # --- PROJECT DETAIL VIEW ---
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
        
        # 1. Notes List Pane (Left) - Kept standard width
        pane_notes = tk.Frame(paned, bg=COLORS["bg_main"])
        paned.add(pane_notes, width=230)
        
        n_tool = tk.Frame(pane_notes, bg=COLORS["bg_sec"], pady=5, padx=5)
        n_tool.pack(fill="x")
        self.note_search_var = tk.StringVar()
        self.note_search_var.trace("w", lambda n,i,m: self.refresh_notes_list())
        ttk.Entry(n_tool, textvariable=self.note_search_var).pack(side="left", fill="x", expand=True)
        ttk.Button(n_tool, text="+", width=3, command=self.create_new_note).pack(side="right", padx=(5,0))
        self.note_scroll = ScrollableFrame(pane_notes, bg_color=COLORS["bg_main"])
        self.note_scroll.pack(fill="both", expand=True)
        
        # 2. Editor Pane (Center) - WIDENED to ~750
        pane_center = tk.Frame(paned, bg=COLORS["white"])
        paned.add(pane_center, width=750)
        
        self.notebook_tabs = ttk.Notebook(pane_center)
        self.notebook_tabs.pack(fill="both", expand=True)
        
        self.tab_editor = tk.Frame(self.notebook_tabs, bg="white")
        self.notebook_tabs.add(self.tab_editor, text=" 📝 Editor ")
        self._setup_editor_ui(self.tab_editor)
        
        # --- WHITEBOARD SETUP ---
        app_data_path = os.path.dirname(self.db.db_path)
        self.tab_whiteboard = Whiteboard(self.notebook_tabs, storage_path=app_data_path)
        self.notebook_tabs.add(self.tab_whiteboard, text=" ✏️ Notepad ")

        # 3. Todo Pane (Right) - NARROWED to ~170
        pane_todo = tk.Frame(paned, bg=COLORS["bg_main"])
        paned.add(pane_todo, width=170)
        self._setup_todo_ui(pane_todo)

        self.refresh_notes_list()
        self.refresh_todo_list()

    def _setup_editor_ui(self, parent):
        self.editor_toolbar = tk.Frame(parent, bg="#eee", pady=5, padx=5)
        self.editor_toolbar.pack(side="top", fill="x")
        
        fmt_frame = tk.Frame(self.editor_toolbar, bg="#eee")
        fmt_frame.pack(side="left", padx=(0, 10))
        
        ttk.Button(fmt_frame, text="H", width=2, style="Tool.TButton", command=self.toggle_heading).pack(side="left", padx=1)
        ttk.Button(fmt_frame, text="B", width=2, style="Tool.TButton", command=lambda: self.toggle_format("bold")).pack(side="left", padx=1)
        ttk.Button(fmt_frame, text="I", width=2, style="Tool.TButton", command=lambda: self.toggle_format("italic")).pack(side="left", padx=1)
        
        self.list_mb = ttk.Menubutton(fmt_frame, text="List Options ▼", direction='below')
        self.list_mb.pack(side="left", padx=5)
        self.list_menu = tk.Menu(self.list_mb, tearoff=0)
        self.list_mb.configure(menu=self.list_menu)
        
        self.list_menu.add_command(label="• Bullet List", command=lambda: self.insert_smart_list("bullet"))
        self.list_menu.add_command(label="1. Numeric List", command=lambda: self.insert_smart_list("number"))
        self.list_menu.add_command(label="A. Alpha Upper", command=lambda: self.insert_smart_list("alpha_upper"))
        self.list_menu.add_command(label="a. Alpha Lower", command=lambda: self.insert_smart_list("alpha_lower"))

        ttk.Button(fmt_frame, text="↶", width=2, style="Tool.TButton", command=self.undo_action).pack(side="left", padx=1)
        ttk.Button(fmt_frame, text="↷", width=2, style="Tool.TButton", command=self.redo_action).pack(side="left", padx=1)

        search_frame = tk.Frame(self.editor_toolbar, bg="#eee")
        search_frame.pack(side="left", padx=10)
        self.editor_search_var = tk.StringVar()
        self.editor_search_var.trace("w", self.on_search_type) 
        self.e_editor_search = ttk.Entry(search_frame, textvariable=self.editor_search_var, width=15)
        self.e_editor_search.pack(side="left")
        
        self.editor_text = tk.Text(parent, font=self.default_font, wrap="word", bd=0, padx=20, pady=20, 
                                   bg=COLORS["white"], fg=COLORS["fg_text"],
                                   undo=True, maxundo=5, autoseparators=False)
        self.editor_text.pack(fill="both", expand=True)
        
        self.editor_text.tag_configure("bold", font=self.bold_font)
        self.editor_text.tag_configure("italic", font=self.italic_font)
        self.editor_text.tag_configure("heading", font=self.heading_font, spacing3=10)
        self.editor_text.tag_configure("search_hi", background=COLORS["search_active"], foreground="white") 
        self.editor_text.tag_configure("misspelled", foreground="red", underline=True)
        self.editor_text.tag_raise("search_hi")
        self.editor_text.tag_raise("misspelled")
        
        self.editor_text.bind("<KeyRelease>", self.on_key_release)
        self.editor_text.bind("<Key>", self.on_key_press)
        self.editor_text.bind("<Control-z>", lambda e: self.undo_action())
        self.editor_text.bind("<Control-y>", lambda e: self.redo_action())
        self.editor_text.bind("<FocusOut>", lambda e: self.auto_save_current())

    def _setup_todo_ui(self, parent):
        t_head = tk.Frame(parent, bg=COLORS["bg_sec"], pady=8, padx=10)
        t_head.pack(fill="x")
        tk.Label(t_head, text="Todo", font=("Segoe UI", 10, "bold"), bg=COLORS["bg_sec"]).pack(anchor="w")
        
        t_input = tk.Frame(parent, bg=COLORS["bg_main"], pady=5)
        t_input.pack(fill="x")
        
        # --- REMOVED Date Entry, just text ---
        self.e_task = ttk.Entry(t_input)
        self.e_task.pack(side="left", fill="x", expand=True, padx=(5,0))
        
        self.e_task.bind("<Return>", lambda e: self.add_task())
        ttk.Button(t_input, text="+", width=3, command=self.add_task).pack(side="right", padx=(5,5))
        
        self.todo_scroll = ScrollableFrame(parent, bg_color=COLORS["bg_main"])
        self.todo_scroll.pack(fill="both", expand=True)

    def insert_smart_list(self, list_type):
        try:
            start = self.editor_text.index("sel.first")
            end = self.editor_text.index("sel.last")
        except:
            start = self.editor_text.index("insert")
            end = start
            
        start_line = f"{start} linestart"
        end_line = f"{end} lineend"
        content = self.editor_text.get(start_line, end_line)
        lines = content.split('\n')
        new_lines = []
        prefix_pattern = r"^\s*(•|\d+\.|[A-Za-z]\.)\s*"

        for i, line in enumerate(lines):
            clean_text = re.sub(prefix_pattern, "", line)
            if not clean_text.strip() and len(lines) > 1:
                new_lines.append("")
                continue
            
            if list_type == "bullet": new_prefix = "• "
            elif list_type == "number": new_prefix = f"{i+1}. "
            elif list_type == "alpha_upper": new_prefix = f"{chr(65 + i)}. "
            elif list_type == "alpha_lower": new_prefix = f"{chr(97 + i)}. "
            else: new_prefix = ""

            new_lines.append(f"{new_prefix}{clean_text}")

        self.editor_text.delete(start_line, end_line)
        self.editor_text.insert(start_line, "\n".join(new_lines))
        self.auto_save_current()

    def on_key_press(self, event):
        if event.char in ['.', '!', '?', '\n']:
            self.editor_text.edit_separator()

    def on_key_release(self, event):
        if event.keysym in ['space', 'Return', 'period', 'comma', 'semicolon']:
            self.check_previous_word()

    def check_previous_word(self):
        if not HAS_SPELL: return
        if self.editor_text.compare("insert-1c", "<", "1.0"): return
        target_index = "insert-2c"
        if self.editor_text.compare(target_index, "<", "1.0"): return
        word_start = self.editor_text.index(f"{target_index} wordstart")
        word_end = self.editor_text.index(f"{target_index} wordend")
        word = self.editor_text.get(word_start, word_end)
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word and spell.unknown([clean_word]):
            self.editor_text.tag_add("misspelled", word_start, word_end)
        else:
            self.editor_text.tag_remove("misspelled", word_start, word_end)

    def undo_action(self, event=None):
        try: self.editor_text.edit_undo()
        except: pass
        return "break"

    def redo_action(self, event=None):
        try: self.editor_text.edit_redo()
        except: pass
        return "break"

    def on_search_type(self, *args):
        self.editor_text.tag_remove("search_hi", "1.0", "end")
        query = self.editor_search_var.get()
        if not query: return
        start_pos = "1.0"
        first_match = None
        while True:
            pos = self.editor_text.search(query, start_pos, stopindex="end", nocase=True)
            if not pos: break
            end_pos = f"{pos}+{len(query)}c"
            self.editor_text.tag_add("search_hi", pos, end_pos)
            if not first_match: first_match = pos
            start_pos = end_pos
        if first_match:
            self.editor_text.see(first_match)

    def toggle_format(self, tag):
        try: 
            current = self.editor_text.tag_names("sel.first")
            if tag in current: self.editor_text.tag_remove(tag, "sel.first", "sel.last")
            else: self.editor_text.tag_add(tag, "sel.first", "sel.last")
            self.auto_save_current()
        except: pass

    def toggle_heading(self):
        try:
            try:
                start = self.editor_text.index("sel.first")
                end = self.editor_text.index("sel.last")
            except tk.TclError:
                start = self.editor_text.index("insert linestart")
                end = self.editor_text.index("insert lineend")
            current_tags = self.editor_text.tag_names(start)
            if "heading" in current_tags:
                self.editor_text.tag_remove("heading", start, end)
            else:
                self.editor_text.tag_add("heading", start, end)
            self.auto_save_current()
        except Exception: pass
        
    def refresh_notes_list(self):
        for w in self.note_scroll.scrollable_frame.winfo_children(): w.destroy()
        notes = self.db.get_notes(self.current_project, self.note_search_var.get())
        for nid, pid, title, ts in notes:
            item = tk.Frame(self.note_scroll.scrollable_frame, bg=COLORS["white"], bd=1, relief="solid")
            item.pack(fill="x", pady=2, padx=2)
            def select_wrapper(e, n=nid): self.auto_save_current(); self.load_editor(n)
            f = tk.Frame(item, bg=COLORS["white"], padx=8, pady=8)
            f.pack(fill="x")
            tk.Label(f, text=title, font=("Segoe UI", 10, "bold"), bg=COLORS["white"], anchor="w").pack(fill="x")
            def load(e, n=nid): self.auto_save_current(); self.load_editor(n)
            for w in [item, f] + f.winfo_children(): w.bind("<Button-1>", load)

    def get_content_snapshot(self):
        text = self.editor_text.get("1.0", "end-1c")
        tags_data = []
        for tag in ["bold", "italic", "heading"]:
            ranges = self.editor_text.tag_ranges(tag)
            if ranges:
                tags_data.append({
                    "name": tag,
                    "ranges": [str(r) for r in ranges]
                })
        return json.dumps({"text": text, "tags": tags_data})

    def apply_content_snapshot(self, json_str):
        self.editor_text.delete("1.0", "end")
        try:
            data = json.loads(json_str)
            self.editor_text.insert("1.0", data.get("text", ""))
            
            for tag_info in data.get("tags", []):
                tag_name = tag_info["name"]
                ranges = tag_info["ranges"]
                for i in range(0, len(ranges), 2):
                    self.editor_text.tag_add(tag_name, ranges[i], ranges[i+1])
        except (json.JSONDecodeError, TypeError):
            self.editor_text.insert("1.0", json_str)

    def load_editor(self, nid):
        self.current_note_id = nid
        # 1. Load Text Content
        content = self.db.get_note_content(nid)
        self.apply_content_snapshot(content)
        self.editor_text.edit_reset()
        # 2. Load Whiteboard Page 0 for this note
        self.tab_whiteboard.load_board(nid)

    def create_new_note(self):
        self.auto_save_current()
        nid = self.db.add_note(self.current_project)
        self.refresh_notes_list()
        self.load_editor(nid)

    def auto_save_current(self):
        if self.current_note_id:
            # 1. Save Text
            content = self.get_content_snapshot()
            self.db.update_note(self.current_note_id, content)
            self.refresh_notes_list()
            # 2. Save Whiteboard
            self.tab_whiteboard.save_current_page()

    def open_export_dialog(self):
        d = tk.Toplevel(self)
        d.title("Export PDF")
        ttk.Button(d, text="Current Note + All Sketches", command=lambda: [d.destroy(), self.generate_pdf_export()]).pack(pady=20, padx=20)

    def generate_pdf_export(self):
        if not HAS_PDF: return show_msg(self, "Error", "Install 'reportlab' first.", True)
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path: return
        try:
            doc = SimpleDocTemplate(path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            if self.current_note_id:
                start_index = "1.0"
                while True:
                    text_segment = self.editor_text.get(start_index, f"{start_index} lineend")
                    if not text_segment: break
                    tags = self.editor_text.tag_names(start_index)
                    style = styles['Heading1'] if "heading" in tags else styles['BodyText']
                    story.append(Paragraph(text_segment, style))
                    story.append(Spacer(1, 6))
                    start_index = self.editor_text.index(f"{start_index} + 1 line")
                    if self.editor_text.compare(start_index, "==", "end"): break
            
            # --- UPDATED: Get ALL whiteboard pages ---
            draw_paths = self.tab_whiteboard.get_all_image_paths()
            if draw_paths:
                story.append(PageBreak())
                story.append(Paragraph("Attached Sketches:", styles['Heading2']))
                story.append(Spacer(1, 10))
                for idx, p in enumerate(draw_paths):
                    story.append(Paragraph(f"Page {idx+1}", styles['Heading3']))
                    story.append(PDFImage(p, width=400, height=300))
                    story.append(Spacer(1, 10))
            
            doc.build(story)
            show_msg(self, "Success", "PDF Exported Successfully!")
        except Exception as e:
            show_msg(self, "Error", str(e), True)

    def add_task(self):
        t = self.e_task.get().strip()
        # --- REMOVED Date Logic ---
        if t: 
            self.db.add_todo(self.current_project, t, "") # Pass empty string for date
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
            # --- Removed Date Display ---
            tk.Label(row, text=task, bg=COLORS["white"], fg=fg_col, wraplength=140, justify="left", anchor="w").pack(side="left", fill="x", expand=True)
            btn_del = tk.Label(row, text="✕", fg="#aaa", bg=COLORS["white"], cursor="hand2")
            btn_del.pack(side="right", padx=5)
            btn_del.bind("<Button-1>", lambda e, t=tid: self.delete_task(t))

    def delete_task(self, tid):
        self.db.delete_todo(tid)
        self.refresh_todo_list()

    def set_password_dialog(self): 
        p = ask_string(self, "Set", "Password:", show="*")
        if p: self.db.set_project_password(self.current_project, p); show_msg(self, "Done", "Locked.")
        
    def change_password_dialog(self):
        p = ask_string(self, "Change", "New Password:", show="*")
        if p: self.db.set_project_password(self.current_project, p)

    def open_new_project_dialog(self):
        p = ask_string(self, "New", "Name:")
        if p: self.db.add_project(p, ""); self.refresh_project_list()

if __name__ == "__main__":
    app = NoteApp()
    app.mainloop()
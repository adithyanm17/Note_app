# main.py
import tkinter as tk
from tkinter import ttk, font, filedialog
import re
from config import APP_NAME, COLORS
from database import DatabaseManager
from noter import CustomDialog
from ui_shared import (
    ScrollableFrame, CalendarDialog, show_msg, 
    ask_yes_no, ask_string
)

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
        pwd = self.db.get_project_password(pid)
        if pwd:
            inp = ask_string(self, "Password Required", "Enter password to delete:", show='*')
            if inp != pwd: return show_msg(self, "Error", "Incorrect password.", True)
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
        
        # --- FIX: Label Creation & Binding on separate lines ---
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
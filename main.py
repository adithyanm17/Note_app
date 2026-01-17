# main.py
import tkinter as tk
from tkinter import ttk, font, filedialog
import re
import os
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
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
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
        if hasattr(self, 'editor_text'): 
            self.auto_save_current()
        for widget in self.container.winfo_children(): widget.destroy()

    # --- PROJECT VIEW (Same as before) ---
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
        
        # Header
        header = ttk.Frame(self.container, padding=(20, 10))
        header.pack(fill="x")
        ttk.Button(header, text="← Back", command=self.show_projects_view, width=8).pack(side="left", padx=(0, 20))
        ttk.Label(header, text=name, style="Header.TLabel").pack(side="left")
        
        tools_frame = ttk.Frame(header)
        tools_frame.pack(side="right")
        ttk.Button(tools_frame, text="Export PDF", style="Tool.TButton", command=self.open_export_dialog).pack(side="left", padx=5)
        
        has_pass = self.db.get_project_password(pid)
        if has_pass:
            ttk.Button(tools_frame, text="Pass Settings", style="Tool.TButton", command=self.change_password_dialog).pack(side="left", padx=5)
        else:
            ttk.Button(tools_frame, text="Lock", style="Tool.TButton", command=self.set_password_dialog).pack(side="left", padx=5)
        
        # Main Layout: Notes List | Editor/Whiteboard | Todo
        paned = tk.PanedWindow(self.container, orient=tk.HORIZONTAL, bg=COLORS["bg_sec"], sashwidth=4)
        paned.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # 1. Notes List Pane
        pane_notes = tk.Frame(paned, bg=COLORS["bg_main"])
        paned.add(pane_notes, width=250)
        n_tool = tk.Frame(pane_notes, bg=COLORS["bg_sec"], pady=5, padx=5)
        n_tool.pack(fill="x")
        self.note_search_var = tk.StringVar()
        self.note_search_var.trace("w", lambda n,i,m: self.refresh_notes_list())
        ttk.Entry(n_tool, textvariable=self.note_search_var).pack(side="left", fill="x", expand=True)
        ttk.Button(n_tool, text="+", width=3, command=self.create_new_note).pack(side="right", padx=(5,0))
        self.note_scroll = ScrollableFrame(pane_notes, bg_color=COLORS["bg_main"])
        self.note_scroll.pack(fill="both", expand=True)
        
        # 2. Central Pane (Tabs: Text Editor & Whiteboard)
        pane_center = tk.Frame(paned, bg=COLORS["white"])
        paned.add(pane_center, width=550)
        
        self.notebook_tabs = ttk.Notebook(pane_center)
        self.notebook_tabs.pack(fill="both", expand=True)
        
        # Tab 1: Text Editor
        self.tab_editor = tk.Frame(self.notebook_tabs, bg="white")
        self.notebook_tabs.add(self.tab_editor, text=" 📝 Editor ")
        self._setup_editor_ui(self.tab_editor)
        
        # Tab 2: Whiteboard
        self.tab_whiteboard = Whiteboard(self.notebook_tabs)
        self.notebook_tabs.add(self.tab_whiteboard, text=" ✏️ Notepad ")

        # 3. Todo Pane
        pane_todo = tk.Frame(paned, bg=COLORS["bg_main"])
        paned.add(pane_todo, width=250)
        self._setup_todo_ui(pane_todo)

        self.refresh_notes_list()
        self.refresh_todo_list()

    def _setup_editor_ui(self, parent):
        self.editor_toolbar = tk.Frame(parent, bg="#eee", pady=5, padx=5)
        self.editor_toolbar.pack(side="top", fill="x")
        
        # Formatting
        fmt_frame = tk.Frame(self.editor_toolbar, bg="#eee")
        fmt_frame.pack(side="left", padx=(0, 10))
        ttk.Button(fmt_frame, text="B", width=2, style="Tool.TButton", command=lambda: self.toggle_format("bold")).pack(side="left", padx=1)
        ttk.Button(fmt_frame, text="I", width=2, style="Tool.TButton", command=lambda: self.toggle_format("italic")).pack(side="left", padx=1)
        
        # Spell Check Button
        ttk.Button(fmt_frame, text="abc✓", width=4, style="Tool.TButton", command=self.check_spelling).pack(side="left", padx=5)
        
        # Undo/Redo Buttons (Visual cues)
        ttk.Button(fmt_frame, text="↶", width=2, style="Tool.TButton", command=self.undo_action).pack(side="left", padx=1)
        ttk.Button(fmt_frame, text="↷", width=2, style="Tool.TButton", command=self.redo_action).pack(side="left", padx=1)

        # Search
        search_frame = tk.Frame(self.editor_toolbar, bg="#eee")
        search_frame.pack(side="left", padx=10)
        self.editor_search_var = tk.StringVar()
        self.editor_search_var.trace("w", self.on_search_type)
        self.e_editor_search = ttk.Entry(search_frame, textvariable=self.editor_search_var, width=15)
        self.e_editor_search.pack(side="left")
        
        # Text Widget
        # undo=True enables built-in stack. maxundo=5 limits depth. autoseparators=False lets us group manually.
        self.editor_text = tk.Text(parent, font=self.default_font, wrap="word", bd=0, padx=20, pady=20, 
                                   bg=COLORS["white"], fg=COLORS["fg_text"],
                                   undo=True, maxundo=5, autoseparators=False)
        self.editor_text.pack(fill="both", expand=True)
        
        self.editor_text.tag_configure("bold", font=self.bold_font)
        self.editor_text.tag_configure("italic", font=self.italic_font)
        self.editor_text.tag_configure("misspelled", foreground="red", underline=True)
        
        # Bindings
        self.editor_text.bind("<KeyRelease>", self.on_text_activity)
        self.editor_text.bind("<Key>", self.on_key_press)
        self.editor_text.bind("<Control-z>", lambda e: self.undo_action())
        self.editor_text.bind("<Control-y>", lambda e: self.redo_action())

    def _setup_todo_ui(self, parent):
        t_head = tk.Frame(parent, bg=COLORS["bg_sec"], pady=8, padx=10)
        t_head.pack(fill="x")
        tk.Label(t_head, text="Todo", font=("Segoe UI", 10, "bold"), bg=COLORS["bg_sec"]).pack(anchor="w")
        
        t_input = tk.Frame(parent, bg=COLORS["bg_main"], pady=5)
        t_input.pack(fill="x")
        self.e_task = ttk.Entry(t_input, width=15)
        self.e_task.pack(side="left", fill="x", expand=True, padx=(5,0))
        self.e_date = ttk.Entry(t_input, width=12, justify="center")
        self.e_date.insert(0, "DD-MM-YYYY")
        self.e_date.bind("<FocusIn>", lambda e: self.e_date.delete(0, "end") if "D" in self.e_date.get() else None)
        self.e_date.pack(side="left", padx=5)
        tk.Button(t_input, text="📅", width=3, bg=COLORS["bg_sec"], relief="flat", command=lambda: CalendarDialog(self, lambda d: (self.e_date.delete(0,"end"), self.e_date.insert(0,d)))).pack(side="left", padx=2)
        
        self.e_task.bind("<Return>", lambda e: self.add_task())
        ttk.Button(t_input, text="+", width=3, command=self.add_task).pack(side="right", padx=(0,5))
        
        self.todo_scroll = ScrollableFrame(parent, bg_color=COLORS["bg_main"])
        self.todo_scroll.pack(fill="both", expand=True)

    # --- UNDO / REDO / SENTENCE LOGIC ---
    def on_key_press(self, event):
        # We manually add a separator to the undo stack only when a sentence ends.
        # This groups all typing between sentences into one "Undo" step.
        if event.char in ['.', '!', '?', '\n']:
            self.editor_text.edit_separator()

    def undo_action(self, event=None):
        try: self.editor_text.edit_undo()
        except: pass # Stack empty
        return "break" # Prevent default behavior duplication

    def redo_action(self, event=None):
        try: self.editor_text.edit_redo()
        except: pass
        return "break"

    # --- SPELL CHECKER ---
    def check_spelling(self):
        if not HAS_SPELL: return show_msg(self, "Error", "Install 'pyspellchecker' to use this feature.", True)
        
        self.editor_text.tag_remove("misspelled", "1.0", "end")
        text = self.editor_text.get("1.0", "end")
        words = re.findall(r"\b\w+\b", text)
        unknown = spell.unknown(words)
        
        for word in unknown:
            start_pos = "1.0"
            while True:
                start_pos = self.editor_text.search(word, start_pos, stopindex="end", nocase=True)
                if not start_pos: break
                end_pos = f"{start_pos}+{len(word)}c"
                self.editor_text.tag_add("misspelled", start_pos, end_pos)
                start_pos = end_pos

    # --- NOTES LOGIC (Simplified for brevity, same as previous) ---
    def refresh_notes_list(self):
        for w in self.note_scroll.scrollable_frame.winfo_children(): w.destroy()
        notes = self.db.get_notes(self.current_project, self.note_search_var.get())
        for nid, pid, title, ts in notes:
            item = tk.Frame(self.note_scroll.scrollable_frame, bg=COLORS["white"], bd=1, relief="solid")
            item.pack(fill="x", pady=2, padx=2)
            f = tk.Frame(item, bg=COLORS["white"], padx=8, pady=8)
            f.pack(fill="x")
            tk.Label(f, text=title, font=("Segoe UI", 10, "bold"), bg=COLORS["white"], anchor="w").pack(fill="x")
            
            def load(e, n=nid): self.auto_save_current(); self.load_editor(n)
            for w in [item, f] + f.winfo_children(): w.bind("<Button-1>", load)

    def load_editor(self, nid):
        self.current_note_id = nid
        content = self.db.get_note_content(nid)
        self.editor_text.delete("1.0", "end")
        self.editor_text.insert("1.0", content)
        self.editor_text.edit_reset() # Clear undo stack on new note load

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

    # --- PDF EXPORT (Updated to include Drawing) ---
    def open_export_dialog(self):
        d = tk.Toplevel(self)
        d.title("Export PDF")
        ttk.Button(d, text="Current Note + Drawing", command=lambda: [d.destroy(), self.generate_pdf_export()]).pack(pady=20, padx=20)

    def generate_pdf_export(self):
        if not HAS_PDF: return show_msg(self, "Error", "Install 'reportlab' first.", True)
        
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path: return

        try:
            doc = SimpleDocTemplate(path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # 1. Add Text
            if self.current_note_id:
                text = self.editor_text.get("1.0", "end-1c")
                for line in text.split('\n'):
                    story.append(Paragraph(line, styles['BodyText']))
                    story.append(Spacer(1, 6))
            
            # 2. Add Drawing (if any)
            draw_path = self.tab_whiteboard.get_image_path_for_pdf()
            if draw_path:
                story.append(PageBreak())
                story.append(Paragraph("Attached Sketch:", styles['Heading2']))
                story.append(Spacer(1, 10))
                # Resize image to fit page width (approx 400px)
                story.append(PDFImage(draw_path, width=400, height=300))
            
            doc.build(story)
            if draw_path: os.remove(draw_path) # Clean up temp file
            show_msg(self, "Success", "PDF Exported Successfully!")
        except Exception as e:
            show_msg(self, "Error", str(e), True)

    # --- HELPER STUBS ---
    def toggle_format(self, tag):
        try: 
            current = self.editor_text.tag_names("sel.first")
            if tag in current: self.editor_text.tag_remove(tag, "sel.first", "sel.last")
            else: self.editor_text.tag_add(tag, "sel.first", "sel.last")
        except: pass
        
    def on_text_activity(self, event): pass
    def on_search_type(self, *args): pass
    
    # --- TODO Logic (Same as before) ---
    def add_task(self):
        t = self.e_task.get()
        d = self.e_date.get()
        if t: self.db.add_todo(self.current_project, t, d); self.e_task.delete(0, "end"); self.refresh_todo_list()

    def refresh_todo_list(self):
        for w in self.todo_scroll.scrollable_frame.winfo_children(): w.destroy()
        for tid, pid, task, date, done, _ in self.db.get_todos(self.current_project):
            row = tk.Frame(self.todo_scroll.scrollable_frame, bg="white")
            row.pack(fill="x", pady=1)
            var = tk.BooleanVar(value=bool(done))
            tk.Checkbutton(row, variable=var, bg="white", command=lambda t=tid, v=var: [self.db.toggle_todo(t, v.get()), self.refresh_todo_list()]).pack(side="left")
            tk.Label(row, text=task, bg="white").pack(side="left")
            tk.Label(row, text="✕", fg="#aaa", bg="white").pack(side="right", padx=5)

    # --- PASSWORDS ---
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
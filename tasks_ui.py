# tasks_ui.py
import tkinter as tk
from tkinter import ttk
from config import COLORS
from ui_shared import ScrollableFrame, CalendarDialog, show_msg, ask_yes_no

class TaskManager(tk.Frame):
    def __init__(self, parent, db, project_id):
        super().__init__(parent, bg=COLORS["bg_main"])
        self.db = db
        self.project_id = project_id
        self.target_date = ""

        # Top Header / Input Area
        self.input_frame = tk.Frame(self, bg=COLORS["bg_sec"], pady=15, padx=20)
        self.input_frame.pack(fill="x")

        # Task Name & Date Row
        row1 = tk.Frame(self.input_frame, bg=COLORS["bg_sec"])
        row1.pack(fill="x")
        
        tk.Label(row1, text="Task Name:", bg=COLORS["bg_sec"], font=("Segoe UI", 9, "bold")).pack(side="left")
        self.e_task = ttk.Entry(row1, width=30)
        self.e_task.pack(side="left", padx=10)

        self.btn_date = ttk.Button(row1, text="📅 Set Target Date", command=self._pick_date)
        self.btn_date.pack(side="left", padx=5)
        
        self.lbl_date_val = tk.Label(row1, text="No Date", bg=COLORS["bg_sec"], fg=COLORS["accent"])
        self.lbl_date_val.pack(side="left", padx=5)

        # Description Row
        row2 = tk.Frame(self.input_frame, bg=COLORS["bg_sec"], pady=10)
        row2.pack(fill="x")
        
        tk.Label(row2, text="Description:", bg=COLORS["bg_sec"], font=("Segoe UI", 9, "bold")).pack(side="left")
        self.e_desc = ttk.Entry(row2)
        self.e_desc.pack(side="left", fill="x", expand=True, padx=10)

        ttk.Button(row2, text="+ Add Task", command=self.add_task_full).pack(side="right")

        # List Area
        self.task_scroll = ScrollableFrame(self, bg_color=COLORS["bg_main"])
        self.task_scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self.refresh_tasks()

    def _pick_date(self):
        CalendarDialog(self, self._set_date_callback)

    def _set_date_callback(self, date_str):
        self.target_date = date_str
        self.lbl_date_val.config(text=date_str)

    def add_task_full(self):
        task_name = self.e_task.get().strip()
        desc = self.e_desc.get().strip()
        if task_name:
            # We use the description in place of date or extend DB if needed
            # For now, we utilize the existing db.add_todo method
            self.db.add_todo(self.project_id, f"{task_name} | {desc}", self.target_date)
            self.e_task.delete(0, "end")
            self.e_desc.delete(0, "end")
            self.target_date = ""
            self.lbl_date_val.config(text="No Date")
            self.refresh_tasks()

    def refresh_tasks(self):
        for w in self.task_scroll.scrollable_frame.winfo_children(): w.destroy()
        todos = self.db.get_todos(self.project_id)
        
        for tid, pid, task_data, due_date, is_done, _ in todos:
            # Splitting name and description if available
            parts = task_data.split(" | ")
            name = parts[0]
            desc = parts[1] if len(parts) > 1 else ""

            card = tk.Frame(self.task_scroll.scrollable_frame, bg=COLORS["white"], bd=1, relief="solid", pady=10, padx=15)
            card.pack(fill="x", pady=5)

            # Left side: Status and Text
            left = tk.Frame(card, bg=COLORS["white"])
            left.pack(side="left", fill="both", expand=True)

            var = tk.BooleanVar(value=bool(is_done))
            cb = tk.Checkbutton(left, variable=var, command=lambda t=tid, v=var: self._toggle(t, v), bg=COLORS["white"])
            cb.pack(side="left", anchor="n")

            txt_frame = tk.Frame(left, bg=COLORS["white"])
            txt_frame.pack(side="left", fill="x", padx=10)

            fg = "#aaa" if is_done else COLORS["fg_text"]
            tk.Label(txt_frame, text=name, font=("Segoe UI", 11, "bold"), fg=fg, bg=COLORS["white"]).pack(anchor="w")
            if desc:
                tk.Label(txt_frame, text=desc, font=("Segoe UI", 9), fg=COLORS["fg_sub"], bg=COLORS["white"]).pack(anchor="w")
            
            # Right side: Date and Delete
            right = tk.Frame(card, bg=COLORS["white"])
            right.pack(side="right")

            if due_date:
                tk.Label(right, text=f"📅 {due_date}", font=("Segoe UI", 8), bg=COLORS["white"], fg=COLORS["accent"]).pack(side="left", padx=10)

            ttk.Button(right, text="Delete", style="Delete.TButton", command=lambda t=tid: self._delete(t)).pack(side="right")

    def _toggle(self, tid, var):
        self.db.toggle_todo(tid, var.get())
        self.refresh_tasks()

    def _delete(self, tid):
        if ask_yes_no(self, "Delete", "Remove this task?"):
            self.db.delete_todo(tid)
            self.refresh_tasks()
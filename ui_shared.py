# ui_shared.py
import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime
from config import COLORS

class CustomDialog(tk.Toplevel):
    def __init__(self, parent, title, width=350, height=160):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.geometry(f"{width}x{height}")
        try: self.iconbitmap("icon.ico")
        except: pass
        self.configure(bg=COLORS["bg_main"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        self.deiconify()

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

def show_msg(parent, title, msg, is_error=False): CustomMessageDialog(parent, title, msg, is_error)
def ask_yes_no(parent, title, msg): d = CustomAskYesNo(parent, title, msg); return d.result
def ask_string(parent, title, prompt, show=None): d = CustomAskString(parent, title, prompt, show); return d.result
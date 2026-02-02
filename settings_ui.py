import tkinter as tk
from tkinter import ttk, filedialog
import os
import zipfile
import glob
from config import COLORS
from ui_shared import show_msg, ask_yes_no, ask_string
from database import DatabaseManager

def open_settings(parent, db, refresh_callback):
    d = tk.Toplevel(parent)
    d.title("Settings")
    d.geometry("500x550")
    d.resizable(False, False)
    d.configure(bg=COLORS["bg_main"])
    lbl_style = ("Segoe UI", 10, "bold")
    
    # Personal Info
    tk.Label(d, text="Personal Info", font=("Segoe UI", 14, "bold"), bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(anchor="w", padx=20, pady=(20, 10))
    f_info = tk.Frame(d, bg=COLORS["bg_main"], padx=20)
    f_info.pack(fill="x")
    
    tk.Label(f_info, text="Name:", bg=COLORS["bg_main"], font=lbl_style).grid(row=0, column=0, sticky="w", pady=5)
    e_name = ttk.Entry(f_info, width=30)
    e_name.grid(row=0, column=1, padx=10, pady=5)
    e_name.insert(0, db.get_setting("user_name"))
    
    def save_info():
        db.set_setting("user_name", e_name.get())
        show_msg(parent, "Saved", "Personal info updated!")
        refresh_callback()
        d.destroy()
    ttk.Button(f_info, text="Save Info", command=save_info).grid(row=2, column=1, sticky="e", pady=10)

    # Backup & Restore
    tk.Label(d, text="Data Management", font=("Segoe UI", 14, "bold"), bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(anchor="w", padx=20, pady=(0, 10))
    f_data = tk.Frame(d, bg=COLORS["bg_main"], padx=20)
    f_data.pack(fill="x")

    def export_backup():
        path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Zip Archive", "*.zip")])
        if not path: return
        try:
            app_dir = os.path.dirname(db.db_path)
            with zipfile.ZipFile(path, 'w') as zipf:
                zipf.write(db.db_path, arcname="noteapp.db")
                for img in glob.glob(os.path.join(app_dir, "wb_*.png")):
                    zipf.write(img, arcname=os.path.basename(img))
            show_msg(parent, "Success", "Backup created!")
        except Exception as e: show_msg(parent, "Error", str(e), True)

    ttk.Button(f_data, text="Export Backup (.zip)", command=export_backup).pack(side="left", padx=(0, 10))
# whiteboard.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import glob
from tkinter import filedialog
from config import COLORS

try:
    from PIL import Image, ImageDraw, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

class Whiteboard(tk.Frame):
    def __init__(self, parent, storage_path, width=600, height=400):
        super().__init__(parent, bg=COLORS["white"])
        self.storage_path = storage_path
        self.brush_color = "black"
        self.brush_size = 3
        self.last_x, self.last_y = None, None
        
        self.image = None
        self.draw = None
        self.tk_image = None
        self.active_note_id = None
        self.current_page = 0
        self.total_pages = 1
        
        self.responsive_btns = []
        self.display_mode = "long"

        # --- Toolbar ---
        self.tools = tk.Frame(self, bg="#eee", pady=5)
        self.tools.pack(side="top", fill="x")
        
        self._add_responsive_btn(self.tools, "✏️", "✏️ Pen", self.use_pen, "left")
        self._add_responsive_btn(self.tools, "🧼", "🧼 Eraser", self.use_eraser, "left")
        self._add_responsive_btn(self.tools, "🗑️", "🗑️ Clear", self.clear_canvas, "left")
        
        self.colors_frame = tk.Frame(self.tools, bg="#eee")
        self.colors_frame.pack(side="left", padx=15)
        colors = ["black", "red", "blue", "green", "#FF8C00", "purple"]
        for c in colors:
            btn = tk.Button(self.colors_frame, bg=c, width=2, height=1, 
                            command=lambda col=c: self.set_color(col), relief="flat")
            btn.pack(side="left", padx=1)

        nav_frame = tk.Frame(self.tools, bg="#eee")
        nav_frame.pack(side="right", padx=5)
        self.lbl_page = tk.Label(nav_frame, text="1/1", bg="#eee", font=("Segoe UI", 9, "bold"))
        self.lbl_page.pack(side="right", padx=10)
        self._add_responsive_btn(nav_frame, ">", "Next >", self.next_page, "right")
        self._add_responsive_btn(nav_frame, "<", "< Prev", self.prev_page, "right")
        self._add_responsive_btn(nav_frame, "📄", "📄 New Pg", self.add_new_page, "right")
        
        if HAS_PDF:
             self._add_responsive_btn(nav_frame, "💾", "💾 PDF", self.export_pdf, "right")

        # --- Canvas ---
        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        
        self.bind("<Configure>", self.on_resize)

        if HAS_PIL:
            # Initial object creation
            self.create_new_image_obj(width, height)

    def _add_responsive_btn(self, parent, short, long, command, side):
        btn = ttk.Button(parent, text=long, command=command)
        btn.pack(side=side, padx=2)
        self.responsive_btns.append((btn, short, long))

    def on_resize(self, event):
        # 1. Handle Responsive Buttons
        new_mode = "long" if event.width > 600 else "short"
        if new_mode != self.display_mode:
            self.display_mode = new_mode
            for btn, short, long in self.responsive_btns:
                btn.config(text=long if new_mode == "long" else short)
        
        # 2. Sync Image size with Canvas size so we don't lose drawings
        if HAS_PIL and self.image:
            if event.width > self.image.width or event.height > self.image.height:
                new_w = max(event.width, self.image.width)
                new_h = max(event.height, self.image.height)
                new_img = Image.new("RGB", (new_w, new_h), "white")
                new_img.paste(self.image, (0, 0))
                self.image = new_img
                self.draw = ImageDraw.Draw(self.image)

    def create_new_image_obj(self, w, h):
        self.image = Image.new("RGB", (w, h), "white")
        self.draw = ImageDraw.Draw(self.image)

    def set_color(self, color):
        self.brush_color = color
        self.brush_size = 3

    def use_pen(self):
        self.brush_color = "black"
        self.brush_size = 3

    def use_eraser(self):
        self.brush_color = "white"
        self.brush_size = 20

    def start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def draw_line(self, event):
        if self.last_x and self.last_y:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, 
                                  width=self.brush_size, fill=self.brush_color, 
                                  capstyle=tk.ROUND, smooth=True)
            if HAS_PIL and self.draw:
                self.draw.line([self.last_x, self.last_y, event.x, event.y], 
                             fill=self.brush_color, width=self.brush_size, joint="curve")
            self.last_x, self.last_y = event.x, event.y

    def stop_draw(self, event):
        self.last_x, self.last_y = None, None
        # This triggers the automatic save to disk
        self.save_current_page()

    def clear_canvas(self):
        self.canvas.delete("all")
        if HAS_PIL:
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            self.create_new_image_obj(w, h)
        self.save_current_page()

    def _get_filename(self, page_idx):
        return os.path.join(self.storage_path, f"wb_{self.active_note_id}_{page_idx}.png")

    def load_board(self, note_id):
        self.active_note_id = note_id
        self.current_page = 0
        if self.active_note_id:
            pattern = os.path.join(self.storage_path, f"wb_{self.active_note_id}_*.png")
            existing_files = glob.glob(pattern)
            indices = [int(f.split("_")[-1].split(".")[0]) for f in existing_files]
            self.total_pages = max(indices) + 1 if indices else 1
        else:
            self.total_pages = 1
        self.load_current_page_image()
        self.update_ui_state()

    def save_current_page(self):
        # CRITICAL: Do not save if no note is selected
        if not HAS_PIL or not self.active_note_id: return
        try:
            path = self._get_filename(self.current_page)
            # Ensure the folder exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.image.save(path)
        except Exception as e:
            print(f"Error saving page: {e}")

    def load_current_page_image(self):
        self.canvas.delete("all")
        if not HAS_PIL or not self.active_note_id: return
        path = self._get_filename(self.current_page)
        
        # Ensure image matches canvas size
        w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 1000
        h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 800
        
        if os.path.exists(path):
            try:
                loaded_img = Image.open(path).convert("RGB")
                self.image = loaded_img
                self.draw = ImageDraw.Draw(self.image)
                self.tk_image = ImageTk.PhotoImage(self.image)
                self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
            except Exception as e:
                print(f"Load error: {e}")
                self.create_new_image_obj(w, h)
        else:
            self.create_new_image_obj(w, h)

    def add_new_page(self):
        self.save_current_page()
        self.total_pages += 1
        self.current_page = self.total_pages - 1
        self.canvas.delete("all")
        self.create_new_image_obj(self.canvas.winfo_width(), self.canvas.winfo_height())
        self.update_ui_state()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.save_current_page()
            self.current_page += 1
            self.load_current_page_image()
            self.update_ui_state()

    def prev_page(self):
        if self.current_page > 0:
            self.save_current_page()
            self.current_page -= 1
            self.load_current_page_image()
            self.update_ui_state()

    def update_ui_state(self):
        self.lbl_page.config(text=f"{self.current_page + 1}/{self.total_pages}")

    def export_pdf(self):
        if not HAS_PDF: return
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not file_path: return
        try:
            self.save_current_page()
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            for i in range(self.total_pages):
                img_path = self._get_filename(i)
                if os.path.exists(img_path):
                    c.drawImage(img_path, 50, height - 500, width=500, height=350, preserveAspectRatio=True)
                    c.drawString(280, 20, f"Page {i+1}")
                    c.showPage()
            c.save()
            messagebox.showinfo("Success", "Whiteboard exported to PDF!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
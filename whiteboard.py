# whiteboard.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import glob
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
        
        # State
        self.image = None
        self.draw = None
        self.tk_image = None
        self.active_note_id = None
        self.current_page = 0
        self.total_pages = 1
        
        # --- Toolbar (Top) ---
        self.tools = tk.Frame(self, bg="#eee", pady=5)
        self.tools.pack(side="top", fill="x")
        
        # Drawing Tools (Removed fixed width to fix text cutting)
        ttk.Button(self.tools, text="✏️ Pen", command=self.use_pen).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🧼 Eraser", command=self.use_eraser).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🗑️ Clear", command=self.clear_canvas).pack(side="left", padx=2)
        
        # Color Palette
        self.colors_frame = tk.Frame(self.tools, bg="#eee")
        self.colors_frame.pack(side="left", padx=15)
        
        colors = ["black", "red", "blue", "green", "#FF8C00", "purple"]
        for c in colors:
            btn = tk.Button(self.colors_frame, bg=c, width=2, height=1, 
                            command=lambda col=c: self.set_color(col), relief="flat")
            btn.pack(side="left", padx=1)

        # Navigation & Export (Right Side)
        nav_frame = tk.Frame(self.tools, bg="#eee")
        nav_frame.pack(side="right", padx=5)

        self.lbl_page = tk.Label(nav_frame, text="Pg 1", bg="#eee", font=("Segoe UI", 9, "bold"))
        self.lbl_page.pack(side="right", padx=10)

        ttk.Button(nav_frame, text="Next >", command=self.next_page).pack(side="right", padx=2)
        ttk.Button(nav_frame, text="< Prev", command=self.prev_page).pack(side="right", padx=2)
        ttk.Button(nav_frame, text="📄 New Page", command=self.add_new_page).pack(side="right", padx=10)
        
        if HAS_PDF:
             ttk.Button(nav_frame, text="💾 PDF", command=self.export_pdf).pack(side="right", padx=5)

        # Canvas
        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        
        # Initialize
        if HAS_PIL:
            self.create_new_image_obj(width, height)

    def create_new_image_obj(self, w, h):
        self.image = Image.new("RGB", (w, h), "white")
        self.draw = ImageDraw.Draw(self.image)

    # --- Drawing Logic ---
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

    def clear_canvas(self):
        self.canvas.delete("all")
        if HAS_PIL:
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            self.create_new_image_obj(w, h)

    # --- FILE I/O & PAGINATION ---
    def _get_filename(self, page_idx):
        return os.path.join(self.storage_path, f"wb_{self.active_note_id}_{page_idx}.png")

    def load_board(self, note_id):
        """Called when switching notes. Resets state and loads Page 0."""
        self.active_note_id = note_id
        self.current_page = 0
        
        # Count total existing pages for this note
        if self.active_note_id:
            pattern = os.path.join(self.storage_path, f"wb_{self.active_note_id}_*.png")
            existing_files = glob.glob(pattern)
            # Determine max page index
            indices = [int(f.split("_")[-1].split(".")[0]) for f in existing_files]
            self.total_pages = max(indices) + 1 if indices else 1
        else:
            self.total_pages = 1

        self.load_current_page_image()
        self.update_ui_state()

    def save_current_page(self):
        """Saves current canvas to disk."""
        if not HAS_PIL or not self.active_note_id: return
        try:
            path = self._get_filename(self.current_page)
            self.image.save(path)
        except Exception as e:
            print(f"Error saving page: {e}")

    def load_current_page_image(self):
        """Loads image for self.current_page from disk."""
        self.clear_canvas()
        if not HAS_PIL or not self.active_note_id: return

        path = self._get_filename(self.current_page)
        if os.path.exists(path):
            try:
                loaded_img = Image.open(path).convert("RGB")
                self.image = loaded_img
                self.draw = ImageDraw.Draw(self.image)
                
                # Display on Canvas
                self.tk_image = ImageTk.PhotoImage(self.image)
                self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
            except:
                pass # If load fails, we just have a blank canvas

    def add_new_page(self):
        self.save_current_page() # Save old page first
        self.total_pages += 1
        self.current_page = self.total_pages - 1
        self.clear_canvas() # Start fresh
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
        self.lbl_page.config(text=f"Pg {self.current_page + 1}/{self.total_pages}")

    # --- PDF EXPORT ---
    def get_all_image_paths(self):
        """Returns sorted list of image paths for main PDF export"""
        paths = []
        # Save current state first to ensure it's included
        self.save_current_page()
        
        for i in range(self.total_pages):
            p = self._get_filename(i)
            if os.path.exists(p):
                paths.append(p)
        return paths

    def export_pdf(self):
        """Exports ONLY the whiteboard pages to a PDF"""
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
                    # Draw image to fit page (maintaining aspect ratio approx)
                    # For simplicity, we scale to fit width
                    c.drawImage(img_path, 50, height - 500, width=500, height=350, preserveAspectRatio=True)
                    c.drawString(280, 20, f"Page {i+1}")
                    c.showPage()
            
            c.save()
            messagebox.showinfo("Success", "Whiteboard exported to PDF!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
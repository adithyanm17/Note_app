# whiteboard.py
import tkinter as tk
from tkinter import ttk, filedialog
from config import COLORS
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

class Whiteboard(tk.Frame):
    def __init__(self, parent, width=600, height=400):
        super().__init__(parent, bg=COLORS["white"])
        self.brush_color = "black"
        self.brush_size = 3
        self.last_x, self.last_y = None, None
        self.image = None
        self.draw = None
        
        # Tools Bar
        self.tools = tk.Frame(self, bg="#eee", pady=5)
        self.tools.pack(side="top", fill="x")
        
        ttk.Button(self.tools, text="✏️ Pen", width=5, command=self.use_pen).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🧼 Eraser", width=6, command=self.use_eraser).pack(side="left", padx=2)
        ttk.Button(self.tools, text="📄 New Page", width=8, command=self.clear_canvas).pack(side="left", padx=10)
        
        if HAS_PIL:
            ttk.Button(self.tools, text="💾 Save Img", width=8, command=self.save_image).pack(side="right", padx=5)

        # Canvas
        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        
        # Initialize PIL Image for saving functionality
        if HAS_PIL:
            self.create_new_image_obj(width, height)
            self.canvas.bind("<Configure>", self.resize_image_obj)

    def create_new_image_obj(self, w, h):
        self.image = Image.new("RGB", (w, h), "white")
        self.draw = ImageDraw.Draw(self.image)

    def resize_image_obj(self, event):
        # Optional: Handle resizing if strictly needed, 
        # usually fixed size or scaling is better for paint apps
        pass

    def start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def draw_line(self, event):
        if self.last_x and self.last_y:
            # Draw on Canvas (Visible)
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y, 
                                  width=self.brush_size, fill=self.brush_color, 
                                  capstyle=tk.ROUND, smooth=True)
            # Draw on PIL Image (Invisible, for export)
            if HAS_PIL and self.draw:
                self.draw.line([self.last_x, self.last_y, event.x, event.y], 
                             fill=self.brush_color, width=self.brush_size, joint="curve")
            
            self.last_x, self.last_y = event.x, event.y

    def stop_draw(self, event):
        self.last_x, self.last_y = None, None

    def use_pen(self):
        self.brush_color = "black"
        self.brush_size = 3

    def use_eraser(self):
        self.brush_color = "white"
        self.brush_size = 20

    def clear_canvas(self):
        self.canvas.delete("all")
        if HAS_PIL:
            self.create_new_image_obj(self.canvas.winfo_width(), self.canvas.winfo_height())

    def save_image(self):
        if not HAS_PIL: return
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if file_path:
            self.image.save(file_path)

    def get_image_path_for_pdf(self):
        """Saves temp image to include in PDF report"""
        if HAS_PIL:
            temp_path = "temp_drawing.png"
            self.image.save(temp_path)
            return temp_path
        return None
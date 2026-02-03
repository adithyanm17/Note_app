# whiteboard.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import math
from tkinter import filedialog
from PIL import Image, ImageDraw, ImageTk
from config import COLORS

class Whiteboard(tk.Frame):
    def __init__(self, parent, storage_path, width=3000, height=5000):
        super().__init__(parent, bg=COLORS["white"])
        self.storage_path = storage_path
        self.brush_color = "black"
        self.brush_size = 3
        self.last_x, self.last_y = None, None
        self.active_note_id = None
        self.current_stroke_points = []
        
        # Wide dimensions to prevent left/right cropping
        self.canvas_width = width
        self.canvas_height = height

        # --- Toolbar ---
        self.tools = tk.Frame(self, bg="#eee", pady=5)
        self.tools.pack(side="top", fill="x")
        
        ttk.Button(self.tools, text="✏️ Pen", command=self.use_pen).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🧼 Eraser", command=self.use_eraser).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🗑️ Clear", command=self.clear_canvas).pack(side="left", padx=2)
        
        self.colors_frame = tk.Frame(self.tools, bg="#eee")
        self.colors_frame.pack(side="left", padx=15)
        for c in ["black", "red", "blue", "green", "#FF8C00", "purple"]:
            tk.Button(self.colors_frame, bg=c, width=2, height=1, 
                      command=lambda col=c: self.set_color(col), relief="flat").pack(side="left", padx=1)

        # --- Canvas Setup (No visible scrollbar) ---
        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair", 
                                highlightthickness=0, 
                                scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bindings for drawing and scrolling
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # PIL Image initialization for saving
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.tk_image = None

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _check_and_expand_canvas(self, y):
        # Dynamically grow the board vertically as you draw
        if y > self.canvas_height - 500:
            new_height = self.canvas_height + 2000
            new_img = Image.new("RGB", (self.canvas_width, new_height), "white")
            new_img.paste(self.image, (0, 0))
            self.image = new_img
            self.draw = ImageDraw.Draw(self.image)
            self.canvas_height = new_height
            self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))

    def set_color(self, color):
        self.brush_color = color

    def use_pen(self):
        self.brush_color = "black"
        self.brush_size = 3

    def use_eraser(self):
        self.brush_color = "white"
        self.brush_size = 20

    def start_draw(self, event):
        # Map mouse to absolute canvas coordinates to prevent cropping
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.last_x, self.last_y = canvas_x, canvas_y
        self.current_stroke_points = [(canvas_x, canvas_y)]

    def draw_line(self, event):
        if self.last_x is not None:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            self._check_and_expand_canvas(canvas_y)
            
            self.canvas.create_line(self.last_x, self.last_y, canvas_x, canvas_y, 
                                  width=self.brush_size, fill=self.brush_color, 
                                  capstyle=tk.ROUND, smooth=True, tags="temp_stroke")
            self.current_stroke_points.append((canvas_x, canvas_y))
            self.last_x, self.last_y = canvas_x, canvas_y

    def stop_draw(self, event):
        if len(self.current_stroke_points) > 10:
            self.process_shape_recognition()
        else:
            self.commit_stroke_to_pil(self.current_stroke_points)
        self.last_x, self.last_y = None, None
        self.current_stroke_points = []
        self.canvas.dtag("temp_stroke", "temp_stroke")
        self.save_current_page()

    def process_shape_recognition(self):
        pts = self.current_stroke_points
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        width, height = max_x - min_x, max_y - min_y
        center_x, center_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        
        dist_start_end = math.sqrt((pts[0][0]-pts[-1][0])**2 + (pts[0][1]-pts[-1][1])**2)
        aspect_ratio = min(width, height) / max(width, height) if max(width, height) > 0 else 0
        
        # 1. Stricter Circle Check (Forces 1:1 Aspect Ratio)
        if dist_start_end < 60 and aspect_ratio > 0.80:
            self.canvas.delete("temp_stroke")
            radius = (width + height) / 4 
            bbox = [center_x - radius, center_y - radius, center_x + radius, center_y + radius]
            self.canvas.create_oval(*bbox, outline=self.brush_color, width=self.brush_size)
            self.draw.ellipse(bbox, outline=self.brush_color, width=self.brush_size)
            return

        # 2. Perfect Straight Line Check
        path_len = sum(math.sqrt((pts[i][0]-pts[i-1][0])**2 + (pts[i][1]-pts[i-1][1])**2) for i in range(1, len(pts)))
        direct_dist = math.sqrt((pts[0][0]-pts[-1][0])**2 + (pts[0][1]-pts[-1][1])**2)
        if direct_dist > 0 and (path_len / direct_dist) < 1.10:
            self.canvas.delete("temp_stroke")
            self.canvas.create_line(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], fill=self.brush_color, width=self.brush_size)
            self.draw.line([pts[0][0], pts[0][1], pts[-1][0], pts[-1][1]], fill=self.brush_color, width=self.brush_size)
            return

        self.commit_stroke_to_pil(pts)

    def commit_stroke_to_pil(self, points):
        if self.draw and len(points) > 1:
            for i in range(1, len(points)):
                self.draw.line([points[i-1][0], points[i-1][1], points[i][0], points[i][1]], 
                               fill=self.brush_color, width=self.brush_size)

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.save_current_page()

    def load_board(self, note_id):
        self.active_note_id = note_id
        self.canvas.delete("all")
        path = os.path.join(self.storage_path, f"wb_{self.active_note_id}_continuous.png")
        if os.path.exists(path):
            try:
                loaded_img = Image.open(path).convert("RGB")
                self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
                self.image.paste(loaded_img, (0,0))
                self.draw = ImageDraw.Draw(self.image)
                self.tk_image = ImageTk.PhotoImage(self.image)
                self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
            except: pass

    def save_current_page(self):
        if not self.active_note_id: return
        path = os.path.join(self.storage_path, f"wb_{self.active_note_id}_continuous.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.image.save(path)
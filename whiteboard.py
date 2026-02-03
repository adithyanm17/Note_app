# whiteboard.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import math
from tkinter import filedialog
from PIL import Image, ImageDraw, ImageTk
from config import COLORS

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as pdf_canvas
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

class Whiteboard(tk.Frame):
    def __init__(self, parent, storage_path, width=2000, height=2000):
        super().__init__(parent, bg=COLORS["white"])
        self.storage_path = storage_path
        self.brush_color = "black"
        self.brush_size = 3
        self.last_x, self.last_y = None, None
        self.active_note_id = None
        self.current_stroke_points = []
        
        # Initial dimensions
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

        if HAS_PDF:
             ttk.Button(self.tools, text="💾 Export PDF", command=self.export_pdf).pack(side="right", padx=5)

        # --- Canvas Setup (No visible scrollbar) ---
        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair", 
                                highlightthickness=0, scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bindings for drawing and scrolling
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw_line)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        
        # Universal scrolling (Mousewheel anywhere on the canvas)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # PIL Image initialization
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.tk_image = None
        
        self._draw_page_markers()

    def _draw_page_markers(self):
        self.canvas.delete("marker")
        for y in range(1000, self.canvas_height, 1000):
            self.canvas.create_line(0, y, self.canvas_width, y, fill="#f0f0f0", dash=(10, 10), tags="marker")

    def _on_mousewheel(self, event):
        # Scrolls the view up or down
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _check_and_expand_canvas(self, y):
        # If the drawing is reaching the bottom, expand the canvas and PIL image
        if y > self.canvas_height - 200:
            new_height = self.canvas_height + 1000
            
            # Expand PIL Image
            new_img = Image.new("RGB", (self.canvas_width, new_height), "white")
            new_img.paste(self.image, (0, 0))
            self.image = new_img
            self.draw = ImageDraw.Draw(self.image)
            
            # Update Canvas
            self.canvas_height = new_height
            self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
            self._draw_page_markers()

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
        # Calculate actual Y coordinate relative to the scrolled board
        canvas_y = self.canvas.canvasy(event.y)
        self.last_x, self.last_y = event.x, canvas_y
        self.current_stroke_points = [(event.x, canvas_y)]

    def draw_line(self, event):
        if self.last_x and self.last_y:
            canvas_y = self.canvas.canvasy(event.y)
            self._check_and_expand_canvas(canvas_y) # Auto-grow logic
            
            self.canvas.create_line(self.last_x, self.last_y, event.x, canvas_y, 
                                  width=self.brush_size, fill=self.brush_color, 
                                  capstyle=tk.ROUND, smooth=True, tags="temp_stroke")
            self.current_stroke_points.append((event.x, canvas_y))
            self.last_x, self.last_y = event.x, canvas_y

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
        
        # Perfect Circle/Oval Logic
        if dist_start_end < 50 and aspect_ratio > 0.70:
            self.canvas.delete("temp_stroke")
            if aspect_ratio > 0.85: # Snap to perfect circle
                diameter = (width + height) / 2
                r = diameter / 2
                bbox = [center_x - r, center_y - r, center_x + r, center_y + r]
            else: # Keep as perfect oval
                bbox = [min_x, min_y, max_x, max_y]
            
            self.canvas.create_oval(*bbox, outline=self.brush_color, width=self.brush_size)
            self.draw.ellipse(bbox, outline=self.brush_color, width=self.brush_size)
            return

        # Perfect Straight Line Logic
        path_len = sum(math.sqrt((pts[i][0]-pts[i-1][0])**2 + (pts[i][1]-pts[i-1][1])**2) for i in range(1, len(pts)))
        direct_dist = math.sqrt((pts[0][0]-pts[-1][0])**2 + (pts[0][1]-pts[-1][1])**2)
        
        if direct_dist > 0 and (path_len / direct_dist) < 1.15:
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
        self._draw_page_markers()
        self.save_current_page()

    def load_board(self, note_id):
        self.active_note_id = note_id
        self.canvas.delete("all")
        
        path = os.path.join(self.storage_path, f"wb_{self.active_note_id}_continuous.png")
        if os.path.exists(path):
            try:
                loaded_img = Image.open(path).convert("RGB")
                # Update current state to match loaded image size
                self.canvas_width, self.canvas_height = loaded_img.size
                self.image = loaded_img
                self.draw = ImageDraw.Draw(self.image)
                self.tk_image = ImageTk.PhotoImage(self.image)
                self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
                self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
            except: 
                self.image = Image.new("RGB", (self.canvas_width, 2000), "white")
                self.draw = ImageDraw.Draw(self.image)
        
        self._draw_page_markers()

    def save_current_page(self):
        if not self.active_note_id: return
        path = os.path.join(self.storage_path, f"wb_{self.active_note_id}_continuous.png")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.image.save(path)

    def export_pdf(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not file_path: return
        try:
            c = pdf_canvas.Canvas(file_path, pagesize=letter)
            # Split the continuous image into standard PDF pages
            for y in range(0, self.canvas_height, 1000):
                box = (0, y, self.canvas_width, min(y + 1000, self.canvas_height))
                page_img = self.image.crop(box)
                temp_path = os.path.join(self.storage_path, "temp_export.png")
                page_img.save(temp_path)
                c.drawImage(temp_path, 0, 0, width=600, height=800, preserveAspectRatio=True)
                c.showPage()
            c.save()
            messagebox.showinfo("Success", "PDF Exported!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
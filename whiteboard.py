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
        self.mode = "pen"  # Options: pen, eraser, select, move
        
        self.last_x, self.last_y = None, None
        self.active_note_id = None
        self.current_stroke_points = []
        self.stroke_count = 0
        
        self.selected_tags = []  # List of tags within the selection area
        self.drag_rect = None    # The visual selection box
        self.rect_start_x = 0
        self.rect_start_y = 0
        self.clipboard_data = [] # Stores copied item properties

        self.canvas_width = width
        self.canvas_height = height

        # --- Toolbar ---
        self.tools = tk.Frame(self, bg="#eee", pady=5)
        self.tools.pack(side="top", fill="x")
        
        ttk.Button(self.tools, text="✏️ Pen", command=self.use_pen).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🧼 Eraser", command=self.use_eraser).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🖱️ Select", command=self.use_select).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🚚 Move", command=self.use_move).pack(side="left", padx=2)
        ttk.Button(self.tools, text="🗑️ Clear", command=self.clear_canvas).pack(side="left", padx=2)
        
        tk.Label(self.tools, text=" Size:", bg="#eee", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 2))
        self.size_slider = tk.Scale(self.tools, from_=1, to_=50, orient="horizontal", 
                                    showvalue=False, bg="#eee", highlightthickness=0, 
                                    command=self.update_brush_size)
        self.size_slider.set(self.brush_size)
        self.size_slider.pack(side="left", padx=5)
        
        self.colors_frame = tk.Frame(self.tools, bg="#eee")
        self.colors_frame.pack(side="left", padx=15)
        for c in ["black", "red", "blue", "green", "#FF8C00", "purple"]:
            tk.Button(self.colors_frame, bg=c, width=2, height=1, 
                      command=lambda col=c: self.set_color(col), relief="flat").pack(side="left", padx=1)

        # --- Canvas Setup ---
        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair", highlightthickness=0, 
                                scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Shortcuts
        self.canvas.bind_all("<Control-c>", lambda e: self.copy_selected())
        self.canvas.bind_all("<Control-v>", lambda e: self.paste_selected())
        self.canvas.bind_all("<Delete>", lambda e: self.delete_selected())
        
        # Scroll & Focus
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        
        # PIL State
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.tk_image = None

    def update_brush_size(self, val):
        self.brush_size = int(val)

    def use_pen(self):
        self.mode = "pen"
        self.canvas.config(cursor="crosshair")

    def use_eraser(self):
        self.mode = "eraser"
        self.canvas.config(cursor="dot")

    def use_select(self):
        self.mode = "select"
        self.canvas.config(cursor="arrow")

    def use_move(self):
        self.mode = "move"
        self.canvas.config(cursor="fleur")

    def set_color(self, color):
        self.brush_color = color
        if self.mode not in ["pen", "eraser"]: self.use_pen()

    # --- Mouse Events ---
    def on_press(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        if self.mode == "select":
            self.selected_tags = []
            if self.drag_rect: self.canvas.delete(self.drag_rect)
            self.rect_start_x, self.rect_start_y = cx, cy
            self.drag_rect = self.canvas.create_rectangle(cx, cy, cx, cy, outline="blue", dash=(4,4))
        elif self.mode == "move":
            self.rect_start_x, self.rect_start_y = cx, cy
        else:
            self.last_x, self.last_y = cx, cy
            self.stroke_count += 1
            self.current_stroke_points = [(cx, cy)]

    def on_motion(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        if self.mode == "select" and self.drag_rect:
            self.canvas.coords(self.drag_rect, self.rect_start_x, self.rect_start_y, cx, cy)
        elif self.mode == "move" and self.selected_tags:
            dx, dy = cx - self.rect_start_x, cy - self.rect_start_y
            for tag in self.selected_tags:
                self.canvas.move(tag, dx, dy)
            if self.drag_rect: self.canvas.move(self.drag_rect, dx, dy)
            self.rect_start_x, self.rect_start_y = cx, cy
        elif self.mode in ["pen", "eraser"]:
            tag = f"stroke_{self.stroke_count}"
            self.canvas.create_line(self.last_x, self.last_y, cx, cy, 
                                  width=self.brush_size, fill=self.brush_color, 
                                  capstyle=tk.ROUND, smooth=True, tags=("temp_stroke", tag))
            self.current_stroke_points.append((cx, cy))
            self.last_x, self.last_y = cx, cy
            if cy > self.canvas_height - 1000: self._expand_board()

    def on_release(self, event):
        if self.mode == "select":
            if self.drag_rect:
                bbox = self.canvas.coords(self.drag_rect)
                items = self.canvas.find_enclosed(*bbox)
                for item in items:
                    tags = self.canvas.gettags(item)
                    for t in tags:
                        if t.startswith("stroke_") and t not in self.selected_tags:
                            self.selected_tags.append(t)
        elif self.mode in ["pen", "eraser"]:
            tag = f"stroke_{self.stroke_count}"
            if len(self.current_stroke_points) > 10 and self.brush_color != "white":
                self.process_shape_recognition(tag)
            self.canvas.dtag("temp_stroke", "temp_stroke")
        
        self.rebuild_pil_image()
        self.last_x, self.last_y = None, None
        self.current_stroke_points = []
        self.save_current_page()

    # --- Shape, Move, Sync ---
    def process_shape_recognition(self, tag):
        pts = self.current_stroke_points
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
        width, height = max_x - min_x, max_y - min_y
        center_x, center_y = (min_x + max_x) / 2, (min_y + max_y) / 2
        
        dist_start_end = math.sqrt((pts[0][0]-pts[-1][0])**2 + (pts[0][1]-pts[-1][1])**2)
        aspect_ratio = min(width, height) / max(width, height) if max(width, height) > 0 else 0
        
        if dist_start_end < 60 and aspect_ratio > 0.80:
            self.canvas.delete(tag)
            radius = (width + height) / 4 
            bbox = [center_x - radius, center_y - radius, center_x + radius, center_y + radius]
            self.canvas.create_oval(*bbox, outline=self.brush_color, width=self.brush_size, tags=tag)
            return

        path_len = sum(math.sqrt((pts[i][0]-pts[i-1][0])**2 + (pts[i][1]-pts[i-1][1])**2) for i in range(1, len(pts)))
        direct_dist = math.sqrt((pts[0][0]-pts[-1][0])**2 + (pts[0][1]-pts[-1][1])**2)
        if direct_dist > 0 and (path_len / direct_dist) < 1.10:
            self.canvas.delete(tag)
            self.canvas.create_line(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1], 
                                    fill=self.brush_color, width=self.brush_size, tags=tag)

    def rebuild_pil_image(self):
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        for item in self.canvas.find_all():
            tags = self.canvas.gettags(item)
            if any(t.startswith("stroke_") for t in tags):
                itype, coords = self.canvas.type(item), self.canvas.coords(item)
                color = self.canvas.itemcget(item, "fill") or self.canvas.itemcget(item, "outline")
                width = int(float(self.canvas.itemcget(item, "width")))
                if itype == "line": self.draw.line(coords, fill=color, width=width)
                elif itype == "oval": self.draw.ellipse(coords, outline=color, width=width)

    # --- Copy, Paste, Delete ---
    def copy_selected(self):
        if self.mode in ["select", "move"] and self.selected_tags:
            self.clipboard_data = []
            for tag in self.selected_tags:
                tag_items = []
                for item in self.canvas.find_withtag(tag):
                    tag_items.append({
                        'type': self.canvas.type(item),
                        'coords': self.canvas.coords(item),
                        'color': self.canvas.itemcget(item, "fill") or self.canvas.itemcget(item, "outline"),
                        'width': self.canvas.itemcget(item, "width")
                    })
                self.clipboard_data.append(tag_items)
            messagebox.showinfo("Clipboard", f"Copied {len(self.selected_tags)} items")

    def paste_selected(self):
        if self.clipboard_data:
            offset = 50
            for tag_items in self.clipboard_data:
                self.stroke_count += 1
                new_tag = f"stroke_{self.stroke_count}"
                for props in tag_items:
                    new_coords = [c + offset for c in props['coords']]
                    if props['type'] == "line":
                        self.canvas.create_line(new_coords, fill=props['color'], width=props['width'], 
                                               tags=new_tag, capstyle=tk.ROUND, smooth=True)
                    elif props['type'] == "oval":
                        self.canvas.create_oval(new_coords, outline=props['color'], width=props['width'], tags=new_tag)
            self.rebuild_pil_image()
            self.save_current_page()

    def delete_selected(self):
        if self.selected_tags:
            for tag in self.selected_tags: self.canvas.delete(tag)
            if self.drag_rect: self.canvas.delete(self.drag_rect)
            self.selected_tags, self.drag_rect = [], None
            self.rebuild_pil_image()
            self.save_current_page()

    # --- Navigation & IO ---
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        _, v_bottom = self.canvas.yview()
        if v_bottom > 0.85: self._expand_board()

    def _expand_board(self):
        new_height = self.canvas_height + 3000
        new_img = Image.new("RGB", (self.canvas_width, new_height), "white")
        new_img.paste(self.image, (0, 0))
        self.image, self.draw = new_img, ImageDraw.Draw(new_img)
        self.canvas_height = new_height
        self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))

    def clear_canvas(self):
        if messagebox.askyesno("Clear", "Clear entire whiteboard?"):
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
                if loaded_img.height > self.canvas_height:
                    self.canvas_height = loaded_img.height
                    self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
                self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
                self.image.paste(loaded_img, (0,0))
                self.draw = ImageDraw.Draw(self.image)
                self.tk_image = ImageTk.PhotoImage(self.image)
                self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
            except: pass

    def save_current_page(self):
        if self.active_note_id:
            path = os.path.join(self.storage_path, f"wb_{self.active_note_id}_continuous.png")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self.image.save(path)
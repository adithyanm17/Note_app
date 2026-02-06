# file_converter.py
import tkinter as tk
from tkinter import ttk, filedialog
import os
from PIL import Image
from pdf2docx import Converter
from pypdf import PdfReader, PdfWriter
from config import COLORS
from ui_shared import show_msg, ask_yes_no

class FileConverterWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("File Converter & PDF Tools")
        self.geometry("500x400")
        self.configure(bg=COLORS["bg_main"])
        
        tk.Label(self, text="File Operations", font=("Segoe UI", 14, "bold"), 
                 bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(pady=20)

        btn_frame = tk.Frame(self, bg=COLORS["bg_main"])
        btn_frame.pack(fill="both", expand=True, padx=50)

        # PDF to Word
        ttk.Button(btn_frame, text="PDF to Word (.docx)", 
                   command=self.pdf_to_word).pack(fill="x", pady=10)

        # Image Format Conversion
        ttk.Button(btn_frame, text="Change Image Format (e.g. PNG to JPG)", 
                   command=self.convert_image).pack(fill="x", pady=10)

        # Split PDF
        ttk.Button(btn_frame, text="Split PDF (Individual Pages)", 
                   command=self.split_pdf).pack(fill="x", pady=10)

    def pdf_to_word(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not file_path: return
        
        output_path = file_path.replace(".pdf", ".docx")
        try:
            cv = Converter(file_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            show_msg(self, "Success", f"Converted to: {os.path.basename(output_path)}")
        except Exception as e:
            show_msg(self, "Error", str(e), True)

    def convert_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if not file_path: return
        
        # Ask for target format
        target_ext = tk.simpledialog.askstring("Format", "Enter target extension (e.g., jpg, png, webp):")
        if not target_ext: return
        
        output_path = os.path.splitext(file_path)[0] + f".{target_ext.lower()}"
        try:
            img = Image.open(file_path)
            if target_ext.lower() in ["jpg", "jpeg"]:
                img = img.convert("RGB")
            img.save(output_path)
            show_msg(self, "Success", f"Saved as {os.path.basename(output_path)}")
        except Exception as e:
            show_msg(self, "Error", str(e), True)

    def split_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not file_path: return
        
        folder = filedialog.askdirectory(title="Select Folder to Save Pages")
        if not folder: return

        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                writer = PdfWriter()
                writer.add_page(page)
                output_filename = os.path.join(folder, f"page_{i+1}.pdf")
                with open(output_filename, "wb") as f:
                    writer.write(f)
            show_msg(self, "Success", f"Split into {len(reader.pages)} files.")
        except Exception as e:
            show_msg(self, "Error", str(e), True)
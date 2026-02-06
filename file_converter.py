# file_converter.py
import tkinter as tk
from tkinter import ttk, filedialog
import os
import re
from PIL import Image, ImageTk
from pypdf import PdfReader, PdfWriter
from pdf2docx import Converter
import barcode
from barcode.writer import ImageWriter
import qrcode
from config import COLORS
from ui_shared import show_msg, ask_yes_no

class FileConverterWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Universal File Tools")
        self.geometry("600x700")
        self.configure(bg=COLORS["bg_main"])
        self.selected_file = None
        
        self._setup_ui()

    def _setup_ui(self):
        # --- File Selection Section ---
        header = tk.Frame(self, bg=COLORS["bg_sec"], pady=20)
        header.pack(fill="x")
        
        tk.Label(header, text="File & Code Utilities", font=("Segoe UI", 16, "bold"), 
                 bg=COLORS["bg_sec"], fg=COLORS["fg_text"]).pack()
        
        main_scroll = tk.Frame(self, bg=COLORS["bg_main"], padx=30, pady=20)
        main_scroll.pack(fill="both", expand=True)

        # 1. Format Conversion Area
        self._create_section_label(main_scroll, "🔄 Format Converter")
        conv_frame = tk.Frame(main_scroll, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        conv_frame.pack(fill="x", pady=(0, 20))

        self.lbl_file = tk.Label(conv_frame, text="No file selected", bg=COLORS["white"], fg=COLORS["fg_sub"], wraplength=450)
        self.lbl_file.pack(anchor="w")
        
        btn_sel = ttk.Button(conv_frame, text="Select File", command=self._select_file)
        btn_sel.pack(side="left", pady=10)

        self.target_ext = ttk.Combobox(conv_frame, values=[".pdf", ".docx", ".jpg", ".png", ".webp"], width=10)
        self.target_ext.set(".pdf")
        self.target_ext.pack(side="right", pady=10)
        tk.Label(conv_frame, text="Convert to:", bg=COLORS["white"]).pack(side="right", padx=5)

        ttk.Button(conv_frame, text="Convert Now", command=self._perform_conversion).pack(fill="x", side="bottom")

        # 2. PDF Advanced Tools (Split/Merge)
        self._create_section_label(main_scroll, "📑 PDF Tools (Split & Merge)")
        pdf_frame = tk.Frame(main_scroll, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        pdf_frame.pack(fill="x", pady=(0, 20))

        tk.Label(pdf_frame, text="Range (e.g., 1-5, 10, 12-15):", bg=COLORS["white"]).pack(anchor="w")
        self.e_range = ttk.Entry(pdf_frame)
        self.e_range.pack(fill="x", pady=5)
        
        pdf_btn_f = tk.Frame(pdf_frame, bg=COLORS["white"])
        pdf_btn_f.pack(fill="x")
        ttk.Button(pdf_btn_f, text="Split PDF", command=self._split_pdf).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(pdf_btn_f, text="Merge PDFs", command=self._merge_pdfs).pack(side="left", expand=True, fill="x", padx=2)

        # 3. Generator Area (QR & Barcode)
        self._create_section_label(main_scroll, "🏷️ Code Generator")
        gen_frame = tk.Frame(main_scroll, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        gen_frame.pack(fill="x")

        self.e_code_data = ttk.Entry(gen_frame)
        self.e_code_data.insert(0, "Type text here...")
        self.e_code_data.pack(fill="x", pady=5)

        code_btn_f = tk.Frame(gen_frame, bg=COLORS["white"])
        code_btn_f.pack(fill="x")
        ttk.Button(code_btn_f, text="Generate QR", command=self._gen_qr).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(code_btn_f, text="Generate Barcode", command=self._gen_barcode).pack(side="left", expand=True, fill="x", padx=2)

    def _create_section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"), bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(anchor="w", pady=(0, 5))

    def _select_file(self):
        f = filedialog.askopenfilename()
        if f:
            self.selected_file = f
            self.lbl_file.config(text=os.path.basename(f), fg=COLORS["fg_text"])

    def _perform_conversion(self):
        if not self.selected_file: return show_msg(self, "Error", "Please select a file first", True)
        
        ext = os.path.splitext(self.selected_file)[1].lower()
        target = self.target_ext.get().lower()

        if ext == target:
            return show_msg(self, "Note", "Source and Target formats are the same!", False)

        out = self.selected_file.replace(ext, target)
        
        try:
            # Logic for Images
            if ext in ['.jpg', '.png', '.webp', '.bmp'] and target in ['.jpg', '.png', '.webp']:
                img = Image.open(self.selected_file)
                if target in ['.jpg', '.jpeg']: img = img.convert("RGB")
                img.save(out)
            # Logic for PDF to Word
            elif ext == ".pdf" and target == ".docx":
                cv = Converter(self.selected_file)
                cv.convert(out)
                cv.close()
            else:
                return show_msg(self, "Unsupported", f"Conversion from {ext} to {target} is not implemented yet.", True)
            
            show_msg(self, "Success", f"Saved: {os.path.basename(out)}")
        except Exception as e:
            show_msg(self, "Error", str(e), True)

    def _split_pdf(self):
        if not self.selected_file or not self.selected_file.endswith(".pdf"):
            return show_msg(self, "Error", "Select a PDF file", True)
        
        range_str = self.e_range.get().strip()
        if not re.match(r"^[0-9,\-\s]+$", range_str):
            return show_msg(self, "Error", "Invalid range format (use numbers, '-' and ',')", True)

        try:
            reader = PdfReader(self.selected_file)
            writer = PdfWriter()
            # Parse ranges like "1-5, 10"
            for part in range_str.split(','):
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    for p_num in range(start-1, end):
                        writer.add_page(reader.pages[p_num])
                else:
                    writer.add_page(reader.pages[int(part)-1])
            
            out = filedialog.asksaveasfilename(defaultextension=".pdf")
            if out:
                with open(out, "wb") as f: writer.write(f)
                show_msg(self, "Success", "PDF Split successfully!")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _merge_pdfs(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if not files: return
        
        writer = PdfWriter()
        try:
            for f in files:
                reader = PdfReader(f)
                for page in reader.pages: writer.add_page(page)
            
            out = filedialog.asksaveasfilename(defaultextension=".pdf")
            if out:
                with open(out, "wb") as f: writer.write(f)
                show_msg(self, "Success", "PDFs Merged!")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _gen_qr(self):
        data = self.e_code_data.get()
        out = filedialog.asksaveasfilename(defaultextension=".png")
        if out:
            qr = qrcode.make(data)
            qr.save(out)
            show_msg(self, "Success", "QR Code Generated!")

    def _gen_barcode(self):
        data = self.e_code_data.get()
        if not data:
            return show_msg(self, "Error", "Please enter data for the barcode", True)
            
        out_path = filedialog.asksaveasfilename(defaultextension=".png")
        if out_path:
            try:
                # Strip the .png for the library as it adds it automatically
                clean_path = out_path.replace(".png", "")
                
                # Using the helper specifically from the barcode module
                import barcode
                from barcode.writer import ImageWriter
                
                # Use 'get' instead of 'get_by_name' if the attribute error persists
                CODICE = barcode.get('code128', data, writer=ImageWriter())
                CODICE.save(clean_path)
                
                show_msg(self, "Success", "Barcode Generated!")
            except Exception as e:
                show_msg(self, "Error", f"Barcode failed: {str(e)}", True)
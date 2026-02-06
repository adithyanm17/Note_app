# file_converter.py
import tkinter as tk
from tkinter import ttk, filedialog
import os
import re
import zipfile
from datetime import datetime
from PIL import Image
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
        self.geometry("700x850")
        self.configure(bg=COLORS["bg_main"])
        
        # State variables
        self.conv_file = None
        self.split_file = None
        self.merge_files = []
        
        self._setup_ui()

    def _setup_ui(self):
        header = tk.Frame(self, bg=COLORS["bg_sec"], pady=20)
        header.pack(fill="x")
        tk.Label(header, text="File & Code Utilities", font=("Segoe UI", 18, "bold"), 
                 bg=COLORS["bg_sec"], fg=COLORS["fg_text"]).pack()

        # Use a scrollable frame for the content if it gets too long
        container = tk.Frame(self, bg=COLORS["bg_main"], padx=30, pady=10)
        container.pack(fill="both", expand=True)

        # 1. FORMAT CONVERTER
        self._create_section_label(container, "🔄 Format Converter")
        conv_f = tk.Frame(container, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        conv_f.pack(fill="x", pady=(0, 20))

        self.lbl_conv = tk.Label(conv_f, text="No file selected", bg=COLORS["white"], fg=COLORS["fg_sub"], wraplength=550)
        self.lbl_conv.pack(anchor="w", pady=(0, 10))
        
        row1 = tk.Frame(conv_f, bg=COLORS["white"])
        row1.pack(fill="x")
        ttk.Button(row1, text="Select File", command=self._sel_conv).pack(side="left")
        
        self.target_ext = ttk.Combobox(row1, values=[".pdf", ".docx", ".jpg", ".png", ".webp"], state="readonly", width=12)
        self.target_ext.set(".pdf")
        self.target_ext.pack(side="right")
        tk.Label(row1, text="Convert to:", bg=COLORS["white"]).pack(side="right", padx=5)

        ttk.Button(conv_f, text="Convert Now", command=self._perform_conversion).pack(fill="x", pady=(15, 0))

        # 2. PDF SPLIT
        self._create_section_label(container, "✂️ Split PDF")
        split_f = tk.Frame(container, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        split_f.pack(fill="x", pady=(0, 20))

        self.lbl_split = tk.Label(split_f, text="No PDF selected", bg=COLORS["white"], fg=COLORS["fg_sub"])
        self.lbl_split.pack(anchor="w")
        
        ttk.Button(split_f, text="Select PDF for Splitting", command=self._sel_split).pack(anchor="w", pady=10)

        tk.Label(split_f, text="Enter Range (e.g. 1-5, 8, 10-12):", bg=COLORS["white"]).pack(anchor="w")
        self.e_range = ttk.Entry(split_f)
        self.e_range.pack(fill="x", pady=5)
        
        btn_row = tk.Frame(split_f, bg=COLORS["white"])
        btn_row.pack(fill="x", pady=5)
        ttk.Button(btn_row, text="Split Selected Range", command=self._split_range).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(btn_row, text="Split All Pages (ZIP)", command=self._split_all_to_zip).pack(side="left", expand=True, fill="x")

        # 3. PDF MERGE
        self._create_section_label(container, "🔗 Merge PDFs")
        merge_f = tk.Frame(container, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        merge_f.pack(fill="x", pady=(0, 20))

        self.lbl_merge_count = tk.Label(merge_f, text="Files attached: 0", bg=COLORS["white"], font=("Segoe UI", 9, "bold"))
        self.lbl_merge_count.pack(anchor="w")
        
        self.merge_listbox = tk.Listbox(merge_f, height=3, bg="#f9f9f9", bd=0)
        self.merge_listbox.pack(fill="x", pady=5)

        m_btn_row = tk.Frame(merge_f, bg=COLORS["white"])
        m_btn_row.pack(fill="x")
        ttk.Button(m_btn_row, text="Add Files", command=self._add_merge_files).pack(side="left", padx=(0, 5))
        ttk.Button(m_btn_row, text="Clear List", command=self._clear_merge_list).pack(side="left")
        ttk.Button(merge_f, text="Merge Into One PDF", command=self._perform_merge).pack(fill="x", pady=(10, 0))

        # 4. CODE GENERATOR
        self._create_section_label(container, "🏷️ Code Generator")
        gen_f = tk.Frame(container, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        gen_f.pack(fill="x")
        self.e_code = ttk.Entry(gen_f); self.e_code.insert(0, "Type data here..."); self.e_code.pack(fill="x", pady=(0, 10))
        g_row = tk.Frame(gen_f, bg=COLORS["white"])
        g_row.pack(fill="x")
        ttk.Button(g_row, text="Generate QR", command=self._gen_qr).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(g_row, text="Generate Barcode", command=self._gen_barcode).pack(side="left", expand=True, fill="x")

    def _create_section_label(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"), bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(anchor="w", pady=(5, 2))

    # --- Logical Functions ---

    def _sel_conv(self):
        self.conv_file = filedialog.askopenfilename()
        if self.conv_file: self.lbl_conv.config(text=os.path.basename(self.conv_file), fg=COLORS["fg_text"])

    def _sel_split(self):
        self.split_file = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if self.split_file:
            reader = PdfReader(self.split_file)
            total = len(reader.pages)
            self.lbl_split.config(text=f"File: {os.path.basename(self.split_file)} | Total Pages: {total}", fg=COLORS["fg_text"])

    def _add_merge_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        for f in files:
            self.merge_files.append(f)
            self.merge_listbox.insert("end", os.path.basename(f))
        self.lbl_merge_count.config(text=f"Files attached: {len(self.merge_files)}")

    def _clear_merge_list(self):
        self.merge_files = []
        self.merge_listbox.delete(0, "end")
        self.lbl_merge_count.config(text="Files attached: 0")

    def _perform_conversion(self):
        if not self.conv_file: return show_msg(self, "Error", "Select file", True)
        ext = os.path.splitext(self.conv_file)[1].lower()
        target = self.target_ext.get().lower()
        if ext == target: return show_msg(self, "Info", "Formats are identical", False)
        
        out = self.conv_file.replace(ext, target)
        try:
            if ext in ['.jpg', '.png', '.webp'] and target in ['.jpg', '.png', '.webp']:
                img = Image.open(self.conv_file)
                if target in ['.jpg', '.jpeg']: img = img.convert("RGB")
                img.save(out)
            elif ext == ".pdf" and target == ".docx":
                cv = Converter(self.conv_file)
                cv.convert(out); cv.close()
            show_msg(self, "Success", f"Converted: {os.path.basename(out)}")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _split_range(self):
        if not self.split_file: return show_msg(self, "Error", "Select PDF", True)
        range_str = self.e_range.get().strip()
        if not re.match(r"^[0-9,\-\s]+$", range_str): return show_msg(self, "Error", "Invalid range", True)
        
        try:
            reader = PdfReader(self.split_file)
            writer = PdfWriter()
            for part in range_str.split(','):
                if '-' in part:
                    s, e = map(int, part.split('-'))
                    for i in range(s-1, e): writer.add_page(reader.pages[i])
                else: writer.add_page(reader.pages[int(part)-1])
            
            base = os.path.splitext(os.path.basename(self.split_file))[0]
            out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{base}_split_{range_str.replace(' ','')}.pdf")
            if out:
                with open(out, "wb") as f: writer.write(f)
                show_msg(self, "Success", "Saved split PDF")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _split_all_to_zip(self):
        if not self.split_file: return show_msg(self, "Error", "Select PDF", True)
        zip_path = filedialog.asksaveasfilename(defaultextension=".zip", initialfile=f"{os.path.splitext(os.path.basename(self.split_file))[0]}_all_pages.zip")
        if not zip_path: return
        
        try:
            reader = PdfReader(self.split_file)
            base_name = os.path.splitext(os.path.basename(self.split_file))[0]
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for i in range(len(reader.pages)):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    temp_pdf = f"temp_page_{i+1}.pdf"
                    with open(temp_pdf, "wb") as f: writer.write(f)
                    zf.write(temp_pdf, arcname=f"{base_name}_page_{i+1}.pdf")
                    os.remove(temp_pdf)
            show_msg(self, "Success", "All pages zipped!")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _perform_merge(self):
        if len(self.merge_files) < 2: return show_msg(self, "Error", "Add at least 2 files", True)
        now = datetime.now().strftime("%Y%m%d_%H%M")
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"mergedfile_{now}.pdf")
        if out:
            try:
                writer = PdfWriter()
                for f in self.merge_files:
                    reader = PdfReader(f)
                    for page in reader.pages: writer.add_page(page)
                with open(out, "wb") as f: writer.write(f)
                show_msg(self, "Success", "PDFs Merged!")
            except Exception as e: show_msg(self, "Error", str(e), True)

    def _gen_qr(self):
        data = self.e_code.get()
        out = filedialog.asksaveasfilename(defaultextension=".png")
        if out: qrcode.make(data).save(out); show_msg(self, "Success", "QR Saved")

    def _gen_barcode(self):
        data = self.e_code.get()
        out = filedialog.asksaveasfilename(defaultextension=".png")
        if out:
            import barcode
            from barcode.writer import ImageWriter
            try:
                # Use robust 'get' method
                code = barcode.get('code128', data, writer=ImageWriter())
                code.save(out.replace(".png", ""))
                show_msg(self, "Success", "Barcode Saved")
            except Exception as e: show_msg(self, "Error", str(e), True)
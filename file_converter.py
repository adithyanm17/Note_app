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
        self.geometry("850x750")
        self.configure(bg=COLORS["bg_main"])
        
        self.conv_file = None
        self.split_file = None
        self.merge_files = []
        
        self._setup_ui()

    def _setup_ui(self):
        # Header
        header = tk.Frame(self, bg=COLORS["bg_sec"], pady=15)
        header.pack(fill="x")
        tk.Label(header, text="Universal File Utilities", font=("Segoe UI", 16, "bold"), 
                 bg=COLORS["bg_sec"], fg=COLORS["fg_text"]).pack()

        # Main Grid Container (2 Columns)
        main_container = tk.Frame(self, bg=COLORS["bg_main"], padx=20, pady=10)
        main_container.pack(fill="both", expand=True)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)

        # --- ROW 1, COL 0: FORMAT CONVERTER ---
        conv_wrap = self._create_card(main_container, "🔄 Format Converter", 0, 0)
        self.lbl_conv = tk.Label(conv_wrap, text="No file selected", bg=COLORS["white"], fg=COLORS["fg_sub"], font=("Segoe UI", 8))
        self.lbl_conv.pack(anchor="w", pady=(0, 5))
        
        c_row = tk.Frame(conv_wrap, bg=COLORS["white"])
        c_row.pack(fill="x")
        ttk.Button(c_row, text="Select", width=10, command=self._sel_conv).pack(side="left")
        self.target_ext = ttk.Combobox(c_row, values=[".pdf", ".docx", ".jpg", ".png", ".webp"], state="readonly", width=8)
        self.target_ext.set(".pdf")
        self.target_ext.pack(side="right")
        ttk.Button(conv_wrap, text="Convert Now", command=self._perform_conversion).pack(fill="x", pady=(10, 0))

        # --- ROW 1, COL 1: PDF SPLITTER (Single File Output) ---
        split_wrap = self._create_card(main_container, "✂️ Split PDF", 0, 1)
        self.lbl_split = tk.Label(split_wrap, text="No PDF selected", bg=COLORS["white"], fg=COLORS["fg_sub"], font=("Segoe UI", 8))
        self.lbl_split.pack(anchor="w", pady=(0, 5))
        ttk.Button(split_wrap, text="Select PDF", command=self._sel_split).pack(anchor="w")
        
        tk.Label(split_wrap, text="Range (e.g. 10-15):", bg=COLORS["white"], font=("Segoe UI", 8)).pack(anchor="w", pady=(5, 0))
        self.e_range = ttk.Entry(split_wrap)
        self.e_range.pack(fill="x", pady=2)
        
        s_btns = tk.Frame(split_wrap, bg=COLORS["white"])
        s_btns.pack(fill="x", pady=(5, 0))
        # Updated: This now creates one single PDF for the range
        ttk.Button(s_btns, text="Range to PDF", command=self._split_range_to_pdf).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(s_btns, text="All to ZIP", command=self._split_all_to_zip).pack(side="left", expand=True, fill="x")

        # --- ROW 2, COL 0: PDF MERGE ---
        merge_wrap = self._create_card(main_container, "🔗 Merge PDFs", 1, 0)
        self.merge_listbox = tk.Listbox(merge_wrap, height=4, font=("Segoe UI", 8), bg="#fcfcfc", bd=1)
        self.merge_listbox.pack(fill="x", pady=5)
        m_btns = tk.Frame(merge_wrap, bg=COLORS["white"])
        m_btns.pack(fill="x")
        ttk.Button(m_btns, text="Add", width=8, command=self._add_merge_files).pack(side="left", padx=2)
        ttk.Button(m_btns, text="Clear", width=8, command=self._clear_merge_list).pack(side="left")
        ttk.Button(merge_wrap, text="Merge PDFs", command=self._perform_merge).pack(fill="x", pady=(10, 0))

        # --- ROW 2, COL 1: CODE GENERATOR ---
        gen_wrap = self._create_card(main_container, "🏷️ Code Generator", 1, 1)
        tk.Label(gen_wrap, text="Data for Code:", bg=COLORS["white"], font=("Segoe UI", 8)).pack(anchor="w")
        self.e_code = ttk.Entry(gen_wrap)
        self.e_code.pack(fill="x", pady=5)
        g_btns = tk.Frame(gen_wrap, bg=COLORS["white"])
        g_btns.pack(fill="x", pady=(5, 0))
        ttk.Button(g_btns, text="QR Code", command=self._gen_qr).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(g_btns, text="Barcode", command=self._gen_barcode).pack(side="left", expand=True, fill="x", padx=2)

    def _create_card(self, parent, title, row, col):
        frame = tk.Frame(parent, bg=COLORS["white"], bd=1, relief="solid", padx=15, pady=15)
        frame.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
        tk.Label(frame, text=title, font=("Segoe UI", 10, "bold"), bg=COLORS["white"], fg=COLORS["accent"]).pack(anchor="w", pady=(0, 10))
        return frame

    # --- Logical Handlers ---

    def _sel_conv(self):
        self.conv_file = filedialog.askopenfilename()
        if self.conv_file: self.lbl_conv.config(text=os.path.basename(self.conv_file))

    def _sel_split(self):
        self.split_file = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if self.split_file:
            reader = PdfReader(self.split_file)
            self.lbl_split.config(text=f"{os.path.basename(self.split_file)} ({len(reader.pages)} pgs)")

    def _split_range_to_pdf(self):
        """Splits a range into a single combined PDF file."""
        if not self.split_file: return show_msg(self, "Error", "Select PDF", True)
        range_in = self.e_range.get().strip()
        if not re.match(r"^[0-9,\-\s]+$", range_in): return show_msg(self, "Error", "Invalid range", True)

        try:
            reader = PdfReader(self.split_file)
            writer = PdfWriter()
            
            # Extract pages for the requested range
            for part in range_in.split(','):
                if '-' in part:
                    s, e = map(int, part.split('-'))
                    for i in range(s-1, e): 
                        writer.add_page(reader.pages[i])
                else: 
                    writer.add_page(reader.pages[int(part)-1])

            base = os.path.splitext(os.path.basename(self.split_file))[0]
            out_name = f"{base}_pages_{range_in.replace(' ','')}.pdf"
            out_path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=out_name)
            
            if out_path:
                with open(out_path, "wb") as f: 
                    writer.write(f)
                show_msg(self, "Success", "Range split into a single PDF!")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _split_all_to_zip(self):
        """Splits every page into individual PDFs inside a ZIP archive."""
        if not self.split_file: return show_msg(self, "Error", "Select PDF", True)
        base = os.path.splitext(os.path.basename(self.split_file))[0]
        zip_path = filedialog.asksaveasfilename(defaultextension=".zip", initialfile=f"{base}_all_pages.zip")
        if not zip_path: return

        try:
            reader = PdfReader(self.split_file)
            with zipfile.ZipFile(zip_path, 'w') as zf:
                for i in range(len(reader.pages)):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    temp_file = f"temp_{i}.pdf"
                    with open(temp_file, "wb") as f: 
                        writer.write(f)
                    zf.write(temp_file, arcname=f"{base}_page_{i+1}.pdf")
                    os.remove(temp_file)
            show_msg(self, "Success", "All pages zipped individually!")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _perform_merge(self):
        if len(self.merge_files) < 2: return show_msg(self, "Error", "Add 2+ files", True)
        now = datetime.now().strftime("%Y%m%d_%H%M")
        out = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"mergedfile_{now}.pdf")
        if out:
            try:
                writer = PdfWriter()
                for f in self.merge_files:
                    reader = PdfReader(f)
                    for page in reader.pages: 
                        writer.add_page(page)
                with open(out, "wb") as f: 
                    writer.write(f)
                show_msg(self, "Success", "PDFs Merged!")
            except Exception as e: show_msg(self, "Error", str(e), True)

    def _add_merge_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        for f in files:
            self.merge_files.append(f)
            self.merge_listbox.insert("end", os.path.basename(f))

    def _clear_merge_list(self):
        self.merge_files.clear()
        self.merge_listbox.delete(0, "end")

    def _perform_conversion(self):
        if not self.conv_file: return
        ext = os.path.splitext(self.conv_file)[1].lower()
        target = self.target_ext.get().lower()
        if ext == target: return show_msg(self, "Note", "Already same format", False)
        out = self.conv_file.replace(ext, target)
        try:
            if ext in ['.jpg', '.png', '.webp'] and target in ['.jpg', '.png', '.webp']:
                img = Image.open(self.conv_file)
                if target in ['.jpg', '.jpeg']: img = img.convert("RGB")
                img.save(out)
            elif ext == ".pdf" and target == ".docx":
                cv = Converter(self.conv_file)
                cv.convert(out); cv.close()
            show_msg(self, "Success", f"Converted to {target}")
        except Exception as e: show_msg(self, "Error", str(e), True)

    def _gen_qr(self):
        data = self.e_code.get().strip()
        if not data: return
        out = filedialog.asksaveasfilename(defaultextension=".png")
        if out: qrcode.make(data).save(out); show_msg(self, "Success", "QR Saved")

    def _gen_barcode(self):
        data = self.e_code.get().strip()
        if not data: return
        out = filedialog.asksaveasfilename(defaultextension=".png")
        if out:
            try:
                import barcode
                from barcode.writer import ImageWriter
                code = barcode.get('code128', data, writer=ImageWriter())
                code.save(out.replace(".png", ""))
                show_msg(self, "Success", "Barcode Saved")
            except Exception as e: show_msg(self, "Error", str(e), True)
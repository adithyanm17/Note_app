import os
import glob
import json
from tkinter import filedialog
from ui_shared import show_msg

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image as PDFImage
    from reportlab.lib.styles import getSampleStyleSheet
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

def run_pdf_export(parent, mode, db, current_project, current_note_id, plain_text_content):
    if not HAS_PDF: return show_msg(parent, "Error", "Install 'reportlab' first.", True)
    path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
    if not path: return
    
    try:
        doc = SimpleDocTemplate(path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        def add_note_text(raw_content, title_prefix=""):
            try:
                data = json.loads(raw_content)
                text = data.get("text", "")
            except:
                text = raw_content
            if title_prefix:
                story.append(Paragraph(title_prefix, styles['Heading1']))
                story.append(Spacer(1, 12))
            for line in text.split('\n'):
                if line.strip():
                    story.append(Paragraph(line, styles['BodyText']))
                    story.append(Spacer(1, 6))

        def add_images(note_id):
            app_data_path = os.path.dirname(db.db_path)
            pattern = os.path.join(app_data_path, f"wb_{note_id}_*.png")
            paths = sorted(glob.glob(pattern))
            if paths:
                story.append(Spacer(1, 10))
                story.append(Paragraph("Sketches:", styles['Heading3']))
                for p in paths:
                    try:
                        story.append(PDFImage(p, width=400, height=300))
                        story.append(Spacer(1, 10))
                    except: pass

        if mode.startswith("current"):
            if not current_note_id: return show_msg(parent, "Error", "No note selected!")
            add_note_text(plain_text_content)
            if mode == "current_full": add_images(current_note_id)
        elif mode == "notebook_full":
            notes = db.get_all_notes_content(current_project)
            for nid, title, content in notes:
                add_note_text(content, title_prefix=title)
                add_images(nid)
                story.append(PageBreak())

        doc.build(story)
        show_msg(parent, "Success", "PDF Exported Successfully!")
    except Exception as e:
        show_msg(parent, "Error", str(e), True)
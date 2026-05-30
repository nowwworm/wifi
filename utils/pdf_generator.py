import os
import httpx
from datetime import datetime
from fpdf import FPDF
from database.models import Edit

# Directories
FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

REGULAR_FONT_PATH = os.path.join(FONTS_DIR, "Arial.ttf")
BOLD_FONT_PATH = os.path.join(FONTS_DIR, "Arial-Bold.ttf")

async def ensure_fonts():
    """Ensures Arial fonts copied from the host system exist in the fonts directory."""
    if not os.path.exists(REGULAR_FONT_PATH) or not os.path.exists(BOLD_FONT_PATH):
        raise FileNotFoundError(
            f"Required Arial fonts not found in {FONTS_DIR}. "
            "Please make sure fonts/Arial.ttf and fonts/Arial-Bold.ttf are present."
        )

class EditsPDF(FPDF):
    def header(self):
        # Select Arial bold 14
        self.set_font("Arial", "B", 14)
        # Title
        self.cell(0, 10, "Правки по проекту feo2sport", border=0, ln=1, align="L")
        self.set_font("Arial", "", 9)
        self.cell(0, 5, f"Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M')}", border=0, ln=1, align="L")
        # Line break
        self.ln(5)
        # Draw a horizontal line
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font("Arial", "", 8)
        # Page number
        self.cell(0, 10, f"Страница {self.page_no()}/{{nb}}", border=0, align="C")

async def generate_edits_pdf(edits: list[Edit], output_path: str):
    """
    Generates a PDF file containing the list of edits, including text and images.
    """
    # 1. Make sure fonts are available
    await ensure_fonts()
    
    # 2. Initialize PDF
    pdf = EditsPDF()
    pdf.alias_nb_pages()
    
    # Add fonts
    pdf.add_font("Arial", "", REGULAR_FONT_PATH)
    pdf.add_font("Arial", "B", BOLD_FONT_PATH)
    
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Всего правок в отчёте: {len(edits)}", ln=1)
    pdf.ln(5)
    
    for i, edit in enumerate(edits, 1):
        # Keep track of Y to check if image fits or not
        pdf.set_font("Arial", "B", 10)
        client_name = f"@{edit.client_username}" if edit.client_username else f"ID: {edit.client_id}"
        date_str = edit.created_at.strftime('%d.%m.%Y %H:%M')
        
        pdf.cell(0, 6, f"{i}. Правка от {client_name} ({date_str})", ln=1)
        
        # Text Content
        pdf.set_font("Arial", "", 10)
        if edit.text_content:
            pdf.multi_cell(0, 5, edit.text_content)
        else:
            pdf.cell(0, 5, "[Без текста]", ln=1)
            
        pdf.ln(3)
        
        # Image screenshot (if exists)
        if edit.image_path and os.path.exists(edit.image_path):
            # Calculate height to keep aspect ratio if width is 150mm
            from PIL import Image as PILImage
            try:
                with PILImage.open(edit.image_path) as img:
                    width, height = img.size
                
                display_width = 150
                display_height = (height / width) * display_width
                
                # Check if image fits on the page. If not, add a new page.
                # Page height is 297mm, margin is 15mm, footer is 15mm, remaining is ~267mm.
                if pdf.get_y() + display_height > 250:
                    pdf.add_page()
                
                pdf.image(edit.image_path, x=15, w=display_width)
                pdf.ln(5)
            except Exception as img_err:
                pdf.set_font("Arial", "", 8)
                pdf.cell(0, 5, f"[Ошибка загрузки изображения: {str(img_err)}]", ln=1)
                pdf.ln(3)
                
        # Draw a separator line between edits
        pdf.ln(2)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(5)
        
    pdf.output(output_path)

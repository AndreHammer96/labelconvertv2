from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject

def split_pdf_labels(input_pdf, output_pdf, width_mm=100, height_mm=150):
    """Divide páginas com várias etiquetas em 1 etiqueta por página (formato 100x150mm)"""
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    # Conversão de mm para pontos (1 pt = 1/72 inch, 25.4 mm por inch)
    width_pt = width_mm * 72 / 25.4
    height_pt = height_mm * 72 / 25.4

    for page_number, page in enumerate(reader.pages):
        # Pega as dimensões da página original
        original_width = float(page.mediabox.width)
        original_height = float(page.mediabox.height)

        # Assumindo 4 etiquetas (2 colunas x 2 linhas)
        cols = 2
        rows = 2
        label_width = original_width / cols
        label_height = original_height / rows

        for row in range(rows):
            for col in range(cols):
                x0 = col * label_width
                y0 = original_height - (row + 1) * label_height
                x1 = x0 + label_width
                y1 = y0 + label_height

                # Cria recorte
                page.cropbox = RectangleObject((x0, y0, x1, y1))

                # Adiciona nova página com tamanho 100x150 mm
                new_page = page
                new_page.mediabox = RectangleObject((0, 0, width_pt, height_pt))
                writer.add_page(new_page)

        print(f"Página {page_number+1} processada com {cols*rows} etiquetas")

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"✅ Novo PDF salvo em: {output_pdf}")

# --- Exemplo de uso:
split_pdf_labels(
    input_pdf=r"C:\Projetos\labelconvertv2\backend\exemplo.pdf",
    output_pdf=r"C:\Projetos\labelconvertv2\backend\etiquetas_1porpagina.pdf"
)

from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject
from pathlib import Path

def split_pdf_by_position(input_pdf, output_pdf, cols=2, rows=2, width_mm=100, height_mm=150):
    """Divide cada página em recortes fixos por posição (colunas × linhas)."""
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    # Conversão mm → pontos
    mm_to_pt = lambda mm: mm * 72 / 25.4
    label_width_pt = mm_to_pt(width_mm)
    label_height_pt = mm_to_pt(height_mm)

    for page_num, page in enumerate(reader.pages, start=1):
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Divide por coordenadas fixas
        cell_width = page_width / cols
        cell_height = page_height / rows

        print(f"📄 Página {page_num}: {page_width:.0f}x{page_height:.0f}pt "
              f"({cols}x{rows} = {cell_width:.0f}x{cell_height:.0f}pt cada)")

        for row in range(rows):
            for col in range(cols):
                x0 = col * cell_width
                x1 = (col + 1) * cell_width
                y1 = page_height - row * cell_height
                y0 = y1 - cell_height

                crop_box = RectangleObject((x0, y0, x1, y1))

                # Cria uma cópia da página e aplica o recorte
                new_page = page
                new_page.cropbox = crop_box
                new_page.mediabox = crop_box

                # Cria uma nova página com tamanho 100x150mm
                writer.add_page(new_page)

                print(f"  → Etiqueta {row*cols + col + 1}: "
                      f"x={x0:.0f}-{x1:.0f}, y={y0:.0f}-{y1:.0f}")

    # Grava o PDF final
    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"\n✅ Novo PDF gerado: {output_pdf}")

# ======= EXEMPLO DE USO =======

if __name__ == "__main__":
    input_path = Path(r"C:\Projetos\labelconvertv2\backend\exemplo.pdf")
    output_path = Path(r"C:\Projetos\labelconvertv2\backend\etiquetas_1porpagina.pdf")
    split_pdf_by_position(input_path, output_path)

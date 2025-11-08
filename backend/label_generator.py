# label_generator.py — fallback agora não atribui dados (deixa em branco)

import fitz
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from reportlab.lib.colors import black, white
from io import BytesIO
from pathlib import Path
from backend.label_matcher import match_pdf_with_excel, extract_products_from_excel

DEBUG = True


def crop_page_into_4_bytes(pdf_path: Path):
    import io
    doc = fitz.open(pdf_path)
    pages_bytes = []

    for page in doc:
        rect = page.rect
        half_w = rect.width / 2
        half_h = rect.height / 2

        # ordem dos quadrantes (ajuste se necessário para seu layout)
        quadrants = [
            fitz.Rect(0, half_h, half_w, rect.height),            # top-left
            fitz.Rect(half_w, half_h, rect.width, rect.height),   # top-right
            fitz.Rect(0, 0, half_w, half_h),                      # bottom-left
            fitz.Rect(half_w, 0, rect.width, half_h),             # bottom-right
        ]

        for q in quadrants:
            buf = io.BytesIO()
            single_doc = fitz.open()
            single_page = single_doc.new_page(width=q.width, height=q.height)
            single_page.show_pdf_page(fitz.Rect(0, 0, q.width, q.height), doc, page.number, clip=q)
            single_doc.save(buf)
            single_doc.close()
            pages_bytes.append(buf.getvalue())

    doc.close()
    return pages_bytes


def text_of_pdf_bytes(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texts = []
    for p in doc:
        texts.append(p.get_text("text"))
    doc.close()
    return "\n".join(texts).strip()


def make_overlay_bytes(product_name: str, quantity: str, width_pts, height_pts):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width_pts, height_pts))
    rect_height = 10 * mm
    c.setFillColor(white)
    c.rect(0, 0, width_pts, rect_height, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    name = (product_name or "")[:80]
    c.drawString(4 * mm, 3 * mm, f"{name} — QTD: {quantity}" if name else "")
    c.showPage()
    c.save()
    return buffer.getvalue()


def scale_and_merge_bytes(base_pdf_bytes: bytes, overlay_pdf_bytes: bytes, width_pts, height_pts):
    base_reader = PdfReader(BytesIO(base_pdf_bytes))
    overlay_reader = PdfReader(BytesIO(overlay_pdf_bytes))
    base_page = base_reader.pages[0]
    overlay_page = overlay_reader.pages[0]

    base_page.mediabox.lower_left = (0, 0)
    base_page.mediabox.upper_right = (width_pts, height_pts)
    base_page.cropbox.lower_left = (0, 0)
    base_page.cropbox.upper_right = (width_pts, height_pts)

    # mescla overlay (que pode estar vazio)
    base_page.merge_page(overlay_page)
    return base_page


def generate_combined_pdf(pdf_path: Path, xlsx_path: Path, output_path: Path):
    """
    Novo fluxo:
    - lẽ Excel (dict)
    - obtém fallback sequence (match_pdf_with_excel) apenas como referência
    - corta PDF em crops
    - para cada crop tenta encontrar order_sn no texto do crop (melhor)
      -> se encontrar: atribui produto (e remove do pool remaining)
      -> se não encontrar: NÃO atribui nada (fallback = vazio), e NÃO consome ordem
    - escreve PDF final
    """
    print("\n🧩 Lendo produtos do Excel...")
    products_dict = extract_products_from_excel(xlsx_path)
    print(f"📦 Produtos no Excel: {len(products_dict)}")

    print("🧩 Obtendo sequência de fallback (somente referência)...")
    fallback_matches = match_pdf_with_excel(pdf_path, xlsx_path)
    fallback_order_sn_list = [m["order_sn"] for m in fallback_matches if m.get("order_sn")]

    print("📦 Recortando PDF (em memória)...")
    cropped_bytes = crop_page_into_4_bytes(pdf_path)
    print(f"✂️  Total de cortes: {len(cropped_bytes)}")

    remaining_order_sns = set(products_dict.keys())
    assignments = []

    # 1) buscar por texto do crop (detecção robusta)
    for i, cb in enumerate(cropped_bytes):
        crop_text = text_of_pdf_bytes(cb).upper() if cb else ""
        found_sn = None

        # procurar dentro dos remaining_order_sns para evitar duplicatas
        for sn in list(remaining_order_sns):
            if sn and sn.upper() in crop_text:
                found_sn = sn
                break

        if found_sn:
            product_name = products_dict.get(found_sn, {}).get("product", "❌ Nome não encontrado")
            quantity = products_dict.get(found_sn, {}).get("quantity", "?")
            assignments.append({"index": i, "order_sn": found_sn, "product_name": product_name, "quantity": quantity, "source": "crop_text"})
            remaining_order_sns.remove(found_sn)
            if DEBUG:
                print(f"[FOUND BY TEXT] crop={i} -> {found_sn} | {product_name} | q={quantity}")
            continue

        # NÃO USAR fallback para preencher: mark as no match (leave blank)
        assignments.append({"index": i, "order_sn": None, "product_name": "", "quantity": "", "source": "fallback-empty"})
        if DEBUG:
            # mostrar qual seria o fallback (apenas informativo), mas não usar/consumir
            fb_sn = fallback_order_sn_list[i] if i < len(fallback_order_sn_list) else None
            print(f"[FALLBACK-EMPTY] crop={i} -> would-be {fb_sn} (not assigned)")

    # relatório resumido
    found_by_text = sum(1 for a in assignments if a["source"] == "crop_text")
    empty_fallbacks = sum(1 for a in assignments if a["source"] == "fallback-empty")
    print(f"\n🔎 Resumo: found_by_text={found_by_text}, fallback_empty={empty_fallbacks}")

    # montar PDF final
    writer = PdfWriter()
    width_pts = 100 * mm
    height_pts = 150 * mm

    for a in assignments:
        idx = a["index"]
        product_name = a["product_name"]
        quantity = a["quantity"]
        if DEBUG:
            print(f"[MAP] crop={idx} -> order_sn={a['order_sn']} | product='{(product_name or '')[:40]}' | q={quantity} | src={a['source']}")
        overlay_bytes = make_overlay_bytes(product_name, quantity, width_pts, height_pts)
        page_obj = scale_and_merge_bytes(cropped_bytes[idx], overlay_bytes, width_pts, height_pts)
        writer.add_page(page_obj)

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"\n🎉 Arquivo gerado: {output_path}")
    return assignments


if __name__ == "__main__":
    base_dir = Path(r"C:\Projetos\labelconvertv2\backend")
    pdf_path = base_dir / "exemplo.pdf"
    xlsx_path = base_dir / "exemplo.xlsx"
    output_path = base_dir / "etiquetas_final.pdf"

    generate_combined_pdf(pdf_path, xlsx_path, output_path)

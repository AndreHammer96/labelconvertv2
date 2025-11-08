import fitz
import pandas as pd
import re
from pathlib import Path

# ==============================================================
# 1️⃣ Extrai sequência de pedidos do PDF (1 pedido por etiqueta)
# ==============================================================

def extract_orders_sequence_from_pdf(pdf_path: Path):
    """
    Retorna uma lista na ordem de leitura contendo todos os order_sn encontrados
    no PDF, tentando produzir 1 order_sn por etiqueta (várias por página).
    A ordem extraída é a ordem textual (split por 'Pedido:'), que normalmente
    acompanha top-left, top-right, bottom-left, bottom-right.
    """
    doc = fitz.open(pdf_path)
    orders = []
    shopee_pattern = re.compile(r"\b25[A-Z0-9]{8,15}\b")  # mais tolerante

    for page in doc:
        text = page.get_text("text")
        parts = re.split(r"Pedido\s*[:\n]", text, flags=re.IGNORECASE)
        # parts[0] = tudo antes do primeiro 'Pedido:' na página
        # cada parts[i>0] corresponde a um bloco *após* cada ocorrência de 'Pedido:'
        for part in parts[1:]:
            # procurar o primeiro código shopee no trecho
            m = shopee_pattern.search(part.upper())
            if m:
                orders.append(m.group(0))
            else:
                # fallback: pegar primeira sequência alfanumérica longa
                alt = re.search(r"[A-Z0-9]{6,}", part.upper())
                orders.append(alt.group(0) if alt else None)

    doc.close()
    return orders


# ==============================================================
# 2️⃣ Extrai produtos e quantidades do Excel
# ==============================================================

def extract_products_from_excel(xlsx_path: Path):
    """Lê o Excel e cria dicionário {order_sn: {"product": nome, "quantity": qtd}}"""
    df = pd.read_excel(xlsx_path)
    products = {}

    for _, row in df.iterrows():
        order_sn = str(row.get("order_sn", "")).strip()
        info = str(row.get("product_info", ""))

        name_match = re.search(r"Parent SKU Reference No.:\s*(.*?)(;|$)", info, flags=re.IGNORECASE)
        if not name_match:
            name_match = re.search(r"Reference No.:\s*(.*?)(;|$)", info, flags=re.IGNORECASE)

        qty_match = re.search(r"Quantity:\s*(\d+)", info, flags=re.IGNORECASE)

        product_name = name_match.group(1).strip() if name_match else "❌ Nome não encontrado"
        quantity = qty_match.group(1).strip() if qty_match else "?"

        if order_sn:
            products[order_sn] = {"product": product_name, "quantity": quantity}

    return products


# ==============================================================
# 3️⃣ Faz o mapeamento 1:1 entre etiquetas (sequence) e Excel
# ==============================================================

def match_pdf_with_excel(pdf_path: Path, xlsx_path: Path):
    """
    Gera lista ordenada de dicionários, um por etiqueta detectada no PDF,
    no mesmo order em que foram lidos do PDF (split por 'Pedido:').
    Cada item contém: index (0-based), order_sn, product_name, quantity
    """
    order_sequence = extract_orders_sequence_from_pdf(pdf_path)
    products = extract_products_from_excel(xlsx_path)

    result = []
    for idx, order_sn in enumerate(order_sequence):
        product_data = products.get(order_sn, {"product": "❌ Não encontrado", "quantity": "?"})
        result.append({
            "index": idx,
            "order_sn": order_sn,
            "product_name": product_data["product"],
            "quantity": product_data["quantity"]
        })
    return result


# ==============================================================
# 4️⃣ Teste local (debug)
# ==============================================================

if __name__ == "__main__":
    pdf_path = Path(r"C:\Projetos\labelconvertv2\backend\exemplo.pdf")
    xlsx_path = Path(r"C:\Projetos\labelconvertv2\backend\exemplo.xlsx")

    matches = match_pdf_with_excel(pdf_path, xlsx_path)
    print(f"Total etiquetas (detectadas): {len(matches)}\n")
    for i, item in enumerate(matches, start=1):
        print(f"{i:03} | Pedido: {item['order_sn']} | Produto: {item['product_name']} | Qtd: {item['quantity']}")

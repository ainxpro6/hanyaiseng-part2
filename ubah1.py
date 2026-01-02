import pdfplumber
import pandas as pd
import re

def extract_and_process_pdf(pdf_path):
    print("Memulai metode 'Grid' untuk ekstraksi data raw...")

    KOLOM_BOUNDARIES = [(0, 350), (350, 470), (470, 540), (540, 595)]
    all_rows_structured = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            current_boundaries = list(KOLOM_BOUNDARIES)
            if page.width != 595:
                current_boundaries[-1] = (540, page.width)

            h_lines = sorted(set([edge["top"] for edge in page.horizontal_edges] + [0, page.height]))

            for top, bottom in zip(h_lines[:-1], h_lines[1:]):
                row_data = []
                for x0, x1 in current_boundaries:
                    cell_crop = page.crop((x0, top, x1, bottom))
                    text = cell_crop.extract_text(x_tolerance=2, y_tolerance=2)
                    row_data.append(text.strip() if text else "")
                if any(row_data):
                    all_rows_structured.append(row_data)

    if not all_rows_structured:
        raise Exception("Tidak ada data yang bisa diekstrak.")

    df_raw = pd.DataFrame(all_rows_structured, columns=["Nama Produk", "SKU", "Slot", "Qty"])
    df_raw = df_raw[~df_raw["Nama Produk"].str.match(r"(?i)^nama produk$")].reset_index(drop=True)

    return df_raw


def clean_data(df_raw):
    print("Pembersihan data...")

    junk_rows_strict = [
        "Jumlah Pesanan", "Jumlah produk", "Picking List",
        "Halaman:", "Dicetak Oleh", "Tanggal Cetak", 
        "Daftar Pengambilan"
    ]

    records = []
    current = {"Nama Produk": "", "Varian": "", "SKU": "", "Qty": 0}

    for _, row in df_raw.iterrows():
        nama = str(row.get("Nama Produk", "")).strip()
        sku = str(row.get("SKU", "")).strip()
        qty = str(row.get("Qty", "")).strip()

        nama = re.sub(r"\d{2}[-/]\d{2}[-/]\d{4}\s+\d{2}:\d{2}:\d{2}", "", nama).strip()

        if re.search(r"(?i)buyer notes|catatan pembeli", nama):
            split_nama = re.split(r"(?i)(?:buyer notes|catatan pembeli)[:\s]*", nama)
            nama = split_nama[0].strip() 
            if not nama: 
                continue

        if any(kw.lower() in nama.lower() for kw in junk_rows_strict):
            continue

        match_varian_line = re.match(r"(?i)^(variant|varian|variation)[:\s]+(.+)", nama)
        if match_varian_line:
            current["Varian"] = match_varian_line.group(2).strip()
            continue
        
        qty_match = re.search(r"\d+", qty)
        if sku and qty_match:

            if nama and "nama produk" not in nama.lower():
                if current["Nama Produk"]:
                    current["Nama Produk"] += " " + nama
                else:
                    current["Nama Produk"] = nama

            regex_varian = r"(?i)(?:variant|varian|variation)\s*[:]\s*(.+)"
            match_embedded = re.search(regex_varian, current["Nama Produk"])
            
            if match_embedded:
                extracted_varian = match_embedded.group(1).strip()
                if not current["Varian"]:
                    current["Varian"] = extracted_varian
                current["Nama Produk"] = re.sub(regex_varian, "", current["Nama Produk"]).strip()

            sku_cleaned = re.sub(r"(?i)defa\w*", "", sku)
            sku_cleaned = sku_cleaned.replace("\n", "").strip()
            sku_cleaned = re.sub(r"^.\s", "", sku_cleaned)[:25] 
            sku_cleaned = re.sub(r"[a-z]", "", sku_cleaned)
            sku_cleaned = sku_cleaned.replace(",", "").replace(".", "").strip()

            qty_clean = int(qty_match.group(0))

            current["SKU"] = sku_cleaned
            current["Qty"] = qty_clean

            final_nama = " ".join(current["Nama Produk"].split())
            current["Nama Produk"] = final_nama[:90]

            if current["SKU"]:
                records.append(current.copy())

            current = {"Nama Produk": "", "Varian": "", "SKU": "", "Qty": 0}
            continue

        if nama:
            if "nama produk" in nama.lower() or "sku" in nama.lower():
                continue
            if current["Nama Produk"]:
                current["Nama Produk"] += " " + nama
            else:
                current["Nama Produk"] = nama

    return records


def main(file_path):
    raw_data_df = extract_and_process_pdf(file_path)
    cleaned_data = clean_data(raw_data_df)
    return cleaned_data





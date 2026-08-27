"""CSV 상품 데이터에서 인식된 상품의 매장 정보를 조회한다."""

import csv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = Path(
    os.environ.get(
        "INVENTORY_CSV",
        str(BASE_DIR / "convenience_store_inventory.csv"),
    )
)


def lookup_stock(product_name: str):
    """상품명을 CSV와 비교해 화면 표시용 매장 정보를 반환한다."""
    if not product_name or not CSV_PATH.exists():
        return None

    query = product_name.casefold().strip()
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            csv_name = (row.get("product_name") or "").casefold().strip()
            if csv_name and (csv_name in query or query in csv_name):
                row["store"] = "현재 매장"
                row["stock"] = row.get("stock_quantity", "")
                row["description"] = (
                    f"{row.get('category', '')} 상품, "
                    f"가격 {row.get('price', '')}원, "
                    f"행사 {row.get('event_type', '단품')}"
                )
                return row
    return None
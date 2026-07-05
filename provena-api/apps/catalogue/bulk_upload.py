"""Parse and validate bulk product upload files (CSV, XLSX, XLS)."""

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

MAX_ROWS = 500
MAX_SIZE_BYTES = 5 * 1024 * 1024

_URL_VALIDATOR = URLValidator()

REQUIRED_COLUMNS = {"product_name", "variant_name", "sku", "price"}


# ---------------------------------------------------------------------------
# Format detection and parsing
# ---------------------------------------------------------------------------


def _detect_format(content: bytes) -> str:
    if content[:4] == b"PK\x03\x04":
        return "xlsx"
    if content[:4] == b"\xd0\xcf\x11\xe0":
        return "xls"
    return "csv"


def _parse_xlsx(content: bytes) -> list[dict[str, str]]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []
    raw_rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not raw_rows:
        return []
    headers = [str(h).strip() if h is not None else "" for h in raw_rows[0]]
    result = []
    for row in raw_rows[1:]:
        result.append(
            {headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)}
        )
    return result


def _parse_xls(content: bytes) -> list[dict[str, str]]:
    import xlrd

    wb = xlrd.open_workbook(file_contents=content)
    ws = wb.sheet_by_index(0)
    if ws.nrows < 1:
        return []
    headers = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]
    result = []
    for r in range(1, ws.nrows):
        result.append({headers[c]: str(ws.cell_value(r, c)).strip() for c in range(ws.ncols)})
    return result


def _parse_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_upload(content: bytes) -> list[dict[str, str]]:
    """Return a list of row dicts from the uploaded file content."""
    fmt = _detect_format(content)
    try:
        if fmt == "xlsx":
            return _parse_xlsx(content)
        if fmt == "xls":
            return _parse_xls(content)
        return _parse_csv(content)
    except Exception as exc:
        raise ValueError(
            "File could not be read as CSV or Excel. Please use the template."
        ) from exc


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _str(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def validate_and_group(
    rows: list[dict[str, str]],
    existing_skus: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Returns (products, errors).

    products: [{name, description, category, image_url, variants: [...]}]
    errors:   [{row, column, message}]

    Products are only populated when there are no errors.
    """
    errors: list[dict[str, Any]] = []
    seen_skus: set[str] = set()
    products_dict: dict[str, dict[str, Any]] = {}

    for i, row in enumerate(rows, start=2):  # row 1 is header
        product_name = _str(row, "product_name")
        variant_name = _str(row, "variant_name")
        sku = _str(row, "sku")
        price_raw = _str(row, "price")
        description = _str(row, "description")
        category = _str(row, "category")
        compare_raw = _str(row, "compare_at_price")
        weight_raw = _str(row, "weight_grams")
        image_url = _str(row, "image_url")

        row_errors: list[dict[str, Any]] = []

        if not product_name:
            row_errors.append({"row": i, "column": "product_name", "message": "Required."})
        if not variant_name:
            row_errors.append({"row": i, "column": "variant_name", "message": "Required."})
        if not sku:
            row_errors.append({"row": i, "column": "sku", "message": "Required."})

        price: Decimal | None = None
        if not price_raw:
            row_errors.append({"row": i, "column": "price", "message": "Required."})
        else:
            try:
                price = Decimal(price_raw)
                if price <= 0:
                    row_errors.append(
                        {"row": i, "column": "price", "message": "Must be greater than zero."}
                    )
                    price = None
            except InvalidOperation:
                row_errors.append(
                    {"row": i, "column": "price", "message": "Must be a valid number."}
                )

        compare_at_price: Decimal | None = None
        if compare_raw:
            try:
                compare_at_price = Decimal(compare_raw)
                if price and compare_at_price <= price:
                    row_errors.append(
                        {
                            "row": i,
                            "column": "compare_at_price",
                            "message": "Must be greater than price.",
                        }
                    )
                    compare_at_price = None
            except InvalidOperation:
                row_errors.append(
                    {"row": i, "column": "compare_at_price", "message": "Must be a valid number."}
                )

        weight_grams: int | None = None
        if weight_raw:
            try:
                weight_grams = int(Decimal(weight_raw))
                if weight_grams < 0:
                    row_errors.append(
                        {
                            "row": i,
                            "column": "weight_grams",
                            "message": "Must be a non-negative integer.",
                        }
                    )
                    weight_grams = None
            except (InvalidOperation, ValueError):
                row_errors.append(
                    {"row": i, "column": "weight_grams", "message": "Must be a whole number."}
                )

        if image_url:
            try:
                _URL_VALIDATOR(image_url)
            except ValidationError:
                row_errors.append(
                    {"row": i, "column": "image_url", "message": "Must be a valid URL."}
                )

        if sku:
            if sku in seen_skus:
                row_errors.append(
                    {"row": i, "column": "sku", "message": f"Duplicate SKU '{sku}' in file."}
                )
            elif sku in existing_skus:
                row_errors.append(
                    {"row": i, "column": "sku", "message": f"SKU '{sku}' is already in use."}
                )
            else:
                seen_skus.add(sku)

        errors.extend(row_errors)

        if not row_errors and product_name:
            if product_name not in products_dict:
                products_dict[product_name] = {
                    "name": product_name,
                    "description": description,
                    "category": category or None,
                    "image_url": image_url or None,
                    "variants": [],
                }
            else:
                if not products_dict[product_name]["description"] and description:
                    products_dict[product_name]["description"] = description
                if not products_dict[product_name]["image_url"] and image_url:
                    products_dict[product_name]["image_url"] = image_url

            products_dict[product_name]["variants"].append(
                {
                    "name": variant_name,
                    "sku": sku,
                    "price": str(price),
                    "compare_at_price": str(compare_at_price) if compare_at_price else None,
                    "weight_grams": weight_grams or 0,
                }
            )

    return list(products_dict.values()), errors

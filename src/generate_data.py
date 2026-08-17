"""Create a reproducible synthetic accounts-payable dataset for analysis."""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path


RANDOM_SEED = 20260815
INVOICE_COUNT = 5000
REFERENCE_DATE = date(2026, 8, 1)

SUPPLIERS = [
    ("Caspian Office Supplies", "Azerbaijan"),
    ("Baku Tech Services", "Azerbaijan"),
    ("Nordic Industrial Parts", "Sweden"),
    ("Atlas Logistics", "Türkiye"),
    ("Caucasus Travel Services", "Georgia"),
    ("Euro Energy Solutions", "Germany"),
    ("Silk Road Consulting", "Kazakhstan"),
    ("Blue Horizon Software", "United Kingdom"),
    ("Crescent Facilities", "Azerbaijan"),
    ("Global Safety Equipment", "Netherlands"),
    ("Araz Catering", "Azerbaijan"),
    ("Dijon Business Travel", "France"),
]

DEPARTMENTS = ["Finance", "Operations", "IT", "Procurement", "HSE", "Human Resources"]
PAYMENT_METHODS = ["Bank Transfer", "Corporate Card", "Cheque"]
CURRENCY_OPTIONS = [("AZN", 0.52), ("USD", 0.28), ("EUR", 0.20)]


def weighted_currency() -> str:
    return random.choices(
        [currency for currency, _ in CURRENCY_OPTIONS],
        weights=[weight for _, weight in CURRENCY_OPTIONS],
        k=1,
    )[0]


def main() -> None:
    random.seed(RANDOM_SEED)
    repository_root = Path(__file__).resolve().parents[1]
    output_path = repository_root / "data" / "raw" / "invoices_raw.csv"
    sample_path = repository_root / "data" / "sample" / "invoices_sample.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_path.parent.mkdir(parents=True, exist_ok=True)

    start_date = date(2024, 1, 1)
    fieldnames = [
        "invoice_id", "supplier", "country", "invoice_date", "due_date", "payment_date",
        "invoice_amount", "currency", "department", "po_number", "invoice_status", "payment_method",
    ]

    rows: list[dict[str, str | float]] = []
    for index in range(1, INVOICE_COUNT + 1):
        supplier, country = random.choice(SUPPLIERS)
        invoice_date = start_date + timedelta(days=random.randint(0, 910))
        due_date = invoice_date + timedelta(days=random.choice([15, 30, 30, 45, 60]))
        amount = round(random.lognormvariate(7.1, 0.85), 2)
        status = random.choices(["Paid", "Outstanding"], weights=[0.83, 0.17], k=1)[0]
        payment_date = ""
        if status == "Paid":
            payment_date = (due_date + timedelta(days=random.randint(-15, 35))).isoformat()

        rows.append({
            "invoice_id": f"INV-{index:06d}",
            "supplier": supplier,
            "country": country,
            "invoice_date": invoice_date.isoformat(),
            "due_date": due_date.isoformat(),
            "payment_date": payment_date,
            "invoice_amount": amount,
            "currency": weighted_currency(),
            "department": random.choice(DEPARTMENTS),
            "po_number": f"PO-{random.randint(1000, 1999)}",
            "invoice_status": status,
            "payment_method": random.choices(PAYMENT_METHODS, weights=[0.84, 0.12, 0.04], k=1)[0],
        })

    # Add controlled duplicate-risk cases for the duplicate-check workflow.
    for duplicate_index in range(35):
        original = rows[duplicate_index * 19]
        copied = original.copy()
        copied["invoice_id"] = f"INV-DUP-{duplicate_index + 1:03d}"
        copied["invoice_date"] = (
            date.fromisoformat(str(original["invoice_date"])) + timedelta(days=random.choice([1, 2, 3]))
        ).isoformat()
        rows.append(copied)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with sample_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows[:100])

    print(f"Created {len(rows):,} invoice records and a 100-row sample")


if __name__ == "__main__":
    main()

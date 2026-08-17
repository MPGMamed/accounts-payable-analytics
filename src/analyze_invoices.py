"""Clean invoice data, calculate accounts-payable KPIs, and create dashboard outputs."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


REFERENCE_DATE = pd.Timestamp("2026-08-01")


def overdue_bucket(days_overdue: float) -> str:
    if days_overdue <= 0:
        return "Not overdue"
    if days_overdue <= 30:
        return "1-30 days"
    if days_overdue <= 60:
        return "31-60 days"
    if days_overdue <= 90:
        return "61-90 days"
    return "90+ days"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_path = root / "data" / "raw" / "invoices_raw.csv"
    processed_dir = root / "data" / "processed"
    tables_dir = root / "outputs" / "tables"
    charts_dir = root / "outputs" / "charts"
    for directory in (processed_dir, tables_dir, charts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    invoices = pd.read_csv(raw_path, parse_dates=["invoice_date", "due_date", "payment_date"])
    invoices = invoices.drop_duplicates(subset="invoice_id").copy()
    invoices["invoice_amount"] = pd.to_numeric(invoices["invoice_amount"], errors="coerce")
    invoices = invoices.dropna(subset=["invoice_amount", "invoice_date", "due_date"])
    invoices = invoices[invoices["invoice_amount"] > 0].copy()
    invoices["payment_days"] = (invoices["payment_date"] - invoices["invoice_date"]).dt.days
    invoices["days_overdue"] = (REFERENCE_DATE - invoices["due_date"]).dt.days.clip(lower=0)
    invoices["is_overdue"] = (invoices["invoice_status"].eq("Outstanding") & (invoices["due_date"] < REFERENCE_DATE))
    invoices["aging_bucket"] = invoices["days_overdue"].map(overdue_bucket)
    invoices["is_late_paid"] = invoices["payment_date"] > invoices["due_date"]

    duplicate_key = ["supplier", "invoice_amount", "po_number"]
    invoices["duplicate_candidate"] = invoices.duplicated(duplicate_key, keep=False)
    invoices.to_csv(processed_dir / "invoices_clean.csv", index=False)

    paid = invoices[invoices["invoice_status"].eq("Paid")]
    outstanding = invoices[invoices["invoice_status"].eq("Outstanding")]
    overdue = invoices[invoices["is_overdue"]]
    kpis = pd.DataFrame([
        ("Total invoices", len(invoices)),
        ("Total invoice value", round(invoices["invoice_amount"].sum(), 2)),
        ("Outstanding value", round(outstanding["invoice_amount"].sum(), 2)),
        ("Overdue value", round(overdue["invoice_amount"].sum(), 2)),
        ("Average payment days", round(paid["payment_days"].mean(), 1)),
        ("Late payment rate", round(paid["is_late_paid"].mean() * 100, 1)),
        ("Duplicate candidates", int(invoices["duplicate_candidate"].sum())),
    ], columns=["metric", "value"])
    kpis.to_csv(tables_dir / "kpi_summary.csv", index=False)

    supplier_summary = invoices.groupby("supplier", as_index=False).agg(
        invoice_count=("invoice_id", "count"),
        invoice_value=("invoice_amount", "sum"),
        overdue_value=("invoice_amount", lambda values: values[invoices.loc[values.index, "is_overdue"]].sum()),
    ).sort_values("invoice_value", ascending=False)
    supplier_summary.to_csv(tables_dir / "supplier_summary.csv", index=False)

    department_summary = invoices.groupby("department", as_index=False).agg(
        invoice_count=("invoice_id", "count"), invoice_value=("invoice_amount", "sum")
    ).sort_values("invoice_value", ascending=False)
    department_summary.to_csv(tables_dir / "department_summary.csv", index=False)

    aging = overdue.groupby("aging_bucket", as_index=False, observed=False)["invoice_amount"].sum()
    bucket_order = ["1-30 days", "31-60 days", "61-90 days", "90+ days"]
    aging["aging_bucket"] = pd.Categorical(aging["aging_bucket"], categories=bucket_order, ordered=True)
    aging = aging.sort_values("aging_bucket")
    aging.to_csv(tables_dir / "aging_summary.csv", index=False)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 5))
    top_suppliers = supplier_summary.head(8).sort_values("invoice_value")
    ax.barh(top_suppliers["supplier"], top_suppliers["invoice_value"], color="#1f77b4")
    ax.set_title("Top Suppliers by Invoice Value")
    ax.set_xlabel("Invoice value")
    fig.tight_layout()
    fig.savefig(charts_dir / "top_suppliers.png", dpi=160)
    fig.savefig(charts_dir / "top_suppliers.svg")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(aging["aging_bucket"].astype(str), aging["invoice_amount"], color="#d62728")
    ax.set_title("Overdue Invoice Aging")
    ax.set_xlabel("Days overdue")
    ax.set_ylabel("Outstanding value")
    fig.tight_layout()
    fig.savefig(charts_dir / "overdue_aging.png", dpi=160)
    fig.savefig(charts_dir / "overdue_aging.svg")
    plt.close(fig)

    print("Analysis complete. Review outputs/tables and outputs/charts.")


if __name__ == "__main__":
    main()

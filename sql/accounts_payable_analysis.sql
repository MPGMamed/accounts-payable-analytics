-- PostgreSQL-compatible accounts payable analysis queries.

-- 1. Payment performance by supplier
SELECT
    supplier,
    COUNT(*) AS invoice_count,
    ROUND(SUM(invoice_amount), 2) AS invoice_value,
    ROUND(AVG(payment_date - invoice_date), 1) AS average_payment_days,
    ROUND(100.0 * AVG(CASE WHEN payment_date > due_date THEN 1 ELSE 0 END), 1) AS late_payment_rate
FROM invoices_clean
WHERE invoice_status = 'Paid'
GROUP BY supplier
ORDER BY invoice_value DESC;

-- 2. Outstanding invoice aging
SELECT
    CASE
        WHEN DATE '2026-08-01' - due_date <= 30 THEN '1-30 days'
        WHEN DATE '2026-08-01' - due_date <= 60 THEN '31-60 days'
        WHEN DATE '2026-08-01' - due_date <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END AS aging_bucket,
    COUNT(*) AS invoice_count,
    ROUND(SUM(invoice_amount), 2) AS outstanding_value
FROM invoices_clean
WHERE invoice_status = 'Outstanding'
  AND due_date < DATE '2026-08-01'
GROUP BY aging_bucket
ORDER BY aging_bucket;

-- 3. Potential duplicate invoice records
SELECT
    supplier,
    po_number,
    invoice_amount,
    COUNT(*) AS records_flagged,
    STRING_AGG(invoice_id, ', ' ORDER BY invoice_id) AS invoice_ids
FROM invoices_clean
GROUP BY supplier, po_number, invoice_amount
HAVING COUNT(*) > 1
ORDER BY records_flagged DESC, supplier;

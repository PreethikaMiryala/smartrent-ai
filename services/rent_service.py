"""
SmartRent AI - Rent Invoicing and Payment Processing Service
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
import database


def generate_monthly_invoices(month_year: str, due_day: int = 5) -> Tuple[int, List[str]]:
    """
    Generates rent invoices for all active tenants for a given month_year (YYYY-MM).
    Applies any pre-approved reward discounts automatically.
    Returns (created_count, skipped_messages).
    """
    conn = database.get_db_connection()
    c = conn.cursor()

    c.execute("""
    SELECT t.id as tenant_id, t.room_id, r.room_number, r.monthly_rent, u.full_name
    FROM tenants t
    JOIN rooms r ON t.room_id = r.id
    JOIN users u ON t.user_id = u.id
    WHERE t.status = 'Active';
    """)
    active_tenants = c.fetchall()

    created_count = 0
    skipped_messages = []

    # Calculate due date
    year, month = map(int, month_year.split("-"))
    due_date = f"{year:04d}-{month:02d}-{due_day:02d}"

    for t in active_tenants:
        tenant_id = t["tenant_id"]
        room_id = t["room_id"]
        base_rent = float(t["monthly_rent"])
        name = t["full_name"]
        room_num = t["room_number"]

        # Check if already generated
        c.execute("SELECT id FROM rent_records WHERE tenant_id = ? AND month_year = ?;", (tenant_id, month_year))
        existing = c.fetchone()
        if existing:
            skipped_messages.append(f"{name} ({room_num}) already has an invoice for {month_year}.")
            continue

        # Check for pre-approved reward discount
        c.execute("""
        SELECT id, discount_percentage, discount_amount 
        FROM rewards 
        WHERE tenant_id = ? AND month_year = ? AND status = 'Approved';
        """, (tenant_id, month_year))
        reward = c.fetchone()

        discount_pct = 0.0
        discount_amt = 0.0
        reward_id = None

        if reward:
            discount_pct = float(reward["discount_percentage"])
            discount_amt = float(reward["discount_amount"])
            reward_id = reward["id"]

        final_rent = max(0.0, base_rent - discount_amt)
        balance = final_rent

        c.execute("""
        INSERT INTO rent_records (
            tenant_id, room_id, month_year, base_rent, discount_percentage,
            discount_amount, final_rent, paid_amount, balance, status, due_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, 'Pending', ?);
        """, (tenant_id, room_id, month_year, base_rent, discount_pct, discount_amt, final_rent, balance, due_date))
        rent_record_id = c.lastrowid

        # If a reward was applied, update reward status to 'Applied'
        if reward_id:
            c.execute("UPDATE rewards SET status = 'Applied', rent_record_id = ? WHERE id = ?;", (rent_record_id, reward_id))

        created_count += 1

    conn.commit()
    conn.close()
    return created_count, skipped_messages


def record_payment(
    rent_record_id: int,
    amount: float,
    payment_date: str,
    payment_method: str,
    transaction_reference: str = "",
    notes: str = "",
    recorded_by: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Records a full or partial rent payment, updates rent record balance and status.
    """
    if amount <= 0:
        return False, "Payment amount must be greater than zero."

    conn = database.get_db_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM rent_records WHERE id = ?;", (rent_record_id,))
    record = c.fetchone()
    if not record:
        conn.close()
        return False, "Rent invoice record not found."

    tenant_id = record["tenant_id"]
    current_paid = float(record["paid_amount"])
    final_rent = float(record["final_rent"])
    current_balance = float(record["balance"])

    if amount > current_balance:
        # Allow overpayment with a warning or cap to current balance
        amount = current_balance

    new_paid = round(current_paid + amount, 2)
    new_balance = round(max(0.0, final_rent - new_paid), 2)

    # Determine status
    if new_balance == 0.0:
        new_status = "Paid"
    elif new_paid > 0.0:
        new_status = "Partially Paid"
    else:
        new_status = "Pending"

    # Insert payment record
    c.execute("""
    INSERT INTO payments (
        rent_record_id, tenant_id, amount, payment_date,
        payment_method, transaction_reference, notes, recorded_by
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (rent_record_id, tenant_id, amount, payment_date, payment_method, transaction_reference, notes, recorded_by))

    # Update rent record
    c.execute("""
    UPDATE rent_records 
    SET paid_amount = ?, balance = ?, status = ?
    WHERE id = ?;
    """, (new_paid, new_balance, new_status, rent_record_id))

    conn.commit()
    conn.close()
    return True, f"Successfully recorded payment of ₹{amount:,.2f}. Status: {new_status}."


def check_and_update_overdue_statuses():
    """Checks all pending or partially paid invoices past their due date and marks them overdue."""
    today_str = date.today().isoformat()
    conn = database.get_db_connection()
    c = conn.cursor()

    c.execute("""
    UPDATE rent_records
    SET status = 'Overdue'
    WHERE due_date < ? AND balance > 0 AND status = 'Pending';
    """, (today_str,))

    conn.commit()
    conn.close()

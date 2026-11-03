"""
SmartRent AI - Reward Calculation and Discount Approval Service
"""
import json
from typing import Dict, Any, List, Optional, Tuple
import database
from config import DEFAULT_REWARD_TIERS, DEFAULT_MAX_DISCOUNT_PERCENT


def get_configured_reward_tiers() -> List[Dict[str, Any]]:
    """Fetch reward tiers from system settings or return defaults."""
    raw = database.get_setting("reward_tiers_json", "")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return DEFAULT_REWARD_TIERS


def get_configured_max_discount() -> float:
    """Fetch max allowed discount percentage."""
    raw = database.get_setting("max_discount_percent", "")
    try:
        return float(raw)
    except Exception:
        return DEFAULT_MAX_DISCOUNT_PERCENT


def calculate_discount_for_score(score: float, base_rent: float) -> Dict[str, Any]:
    """
    Calculate discount percentage, discount amount, and reward points for a score.
    Respects configured tiers and maximum discount limit.
    """
    tiers = get_configured_reward_tiers()
    max_cap = get_configured_max_discount()

    discount_pct = 0.0
    for tier in tiers:
        if tier["min"] <= score <= tier["max"]:
            discount_pct = float(tier["discount_pct"])
            break

    # Apply ceiling cap
    discount_pct = min(discount_pct, max_cap)
    discount_amount = round((discount_pct / 100.0) * base_rent, 2)
    reward_points = int(score)

    return {
        "score": score,
        "discount_percentage": discount_pct,
        "discount_amount": discount_amount,
        "reward_points": reward_points,
        "is_eligible": discount_pct > 0
    }


def approve_reward_and_apply_to_rent(reward_id: int, owner_comments: str = "") -> Tuple[bool, str]:
    """
    Owner approves reward. Automatically updates rent record with discount if not already applied.
    Ensures discount is NEVER applied twice for the same monthly rent invoice.
    """
    conn = database.get_db_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM rewards WHERE id = ?;", (reward_id,))
    reward = c.fetchone()
    if not reward:
        conn.close()
        return False, "Reward record not found."

    if reward["status"] in ("Approved", "Applied"):
        conn.close()
        return False, "Reward has already been approved/applied."

    tenant_id = reward["tenant_id"]
    month_year = reward["month_year"]
    discount_pct = reward["discount_percentage"]
    discount_amt = reward["discount_amount"]

    # Locate rent record for this tenant and month
    c.execute("SELECT * FROM rent_records WHERE tenant_id = ? AND month_year = ?;", (tenant_id, month_year))
    rent_record = c.fetchone()

    if rent_record:
        # Check if a discount was already applied to this rent record
        if rent_record["discount_amount"] > 0:
            conn.close()
            return False, f"A discount of ₹{rent_record['discount_amount']} is already applied to invoice {month_year}."

        base_rent = rent_record["base_rent"]
        new_final = max(0.0, base_rent - discount_amt)
        new_balance = max(0.0, new_final - rent_record["paid_amount"])
        new_status = "Paid" if new_balance == 0.0 and rent_record["paid_amount"] > 0 else (
            "Partially Paid" if rent_record["paid_amount"] > 0 else "Pending"
        )

        c.execute("""
        UPDATE rent_records 
        SET discount_percentage = ?, discount_amount = ?, final_rent = ?, balance = ?, status = ?
        WHERE id = ?;
        """, (discount_pct, discount_amt, new_final, new_balance, new_status, rent_record["id"]))

        # Mark reward as Applied
        c.execute("""
        UPDATE rewards 
        SET status = 'Applied', rent_record_id = ?, owner_comments = ?, approved_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (rent_record["id"], owner_comments, reward_id))
        applied_note = f"Discount of ₹{discount_amt} ({discount_pct}%) successfully applied to invoice {month_year}."
    else:
        # Rent record not yet generated for this month, save as Approved
        c.execute("""
        UPDATE rewards 
        SET status = 'Approved', owner_comments = ?, approved_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (owner_comments, reward_id))
        applied_note = f"Reward approved! Discount of ₹{discount_amt} will apply when {month_year} rent invoice is generated."

    conn.commit()
    conn.close()
    return True, applied_note


def reject_reward(reward_id: int, owner_comments: str) -> Tuple[bool, str]:
    """Owner rejects a discount recommendation with feedback comments."""
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE rewards SET status = 'Rejected', owner_comments = ? WHERE id = ?;", (owner_comments, reward_id))
    conn.commit()
    conn.close()
    return True, "Reward recommendation marked as Rejected."

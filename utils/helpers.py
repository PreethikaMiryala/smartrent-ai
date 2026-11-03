"""
SmartRent AI - UI Helpers and Formatting Utilities
"""
from datetime import datetime, date
from typing import Optional
from config import CURRENCY_SYMBOL


def format_currency(amount: Optional[float]) -> str:
    """Format numeric amount into currency representation (e.g. ₹8,000.00)."""
    if amount is None:
        return f"{CURRENCY_SYMBOL}0.00"
    try:
        val = float(amount)
        return f"{CURRENCY_SYMBOL}{val:,.2f}"
    except (ValueError, TypeError):
        return f"{CURRENCY_SYMBOL}0.00"


def format_currency_short(amount: Optional[float]) -> str:
    """Format numeric amount into short currency representation (e.g. ₹8,000)."""
    if amount is None:
        return f"{CURRENCY_SYMBOL}0"
    try:
        val = float(amount)
        return f"{CURRENCY_SYMBOL}{int(val):,}"
    except (ValueError, TypeError):
        return f"{CURRENCY_SYMBOL}0"


def format_date(dt) -> str:
    """Format date/timestamp into readable string."""
    if not dt:
        return "N/A"
    if isinstance(dt, (date, datetime)):
        return dt.strftime("%d %b %Y")
    try:
        parsed = datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y")
    except Exception:
        # Fallback to splitting if YYYY-MM-DD
        if len(str(dt)) >= 10:
            return str(dt)[:10]
        return str(dt)


def get_current_month_str() -> str:
    """Returns current month string formatted as YYYY-MM."""
    return datetime.now().strftime("%Y-%m")


def get_month_options(past_months: int = 6, future_months: int = 1) -> list:
    """Generate a list of YYYY-MM strings for selection."""
    now = datetime.now()
    results = []
    # Future month
    for offset in range(future_months, -past_months - 1, -1):
        month = now.month + offset
        year = now.year
        while month > 12:
            month -= 12
            year += 1
        while month < 1:
            month += 12
            year -= 1
        results.append(f"{year:04d}-{month:02d}")
    return sorted(list(set(results)), reverse=True)


def calculate_score_category(score: float) -> str:
    """Classify cleanliness score into tiers."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Average"
    else:
        return "Needs Improvement"


def get_score_color(score: float) -> str:
    """Returns hexadecimal color code corresponding to a cleanliness score."""
    if score >= 90:
        return "#10b981"  # Emerald
    elif score >= 75:
        return "#06b6d4"  # Cyan
    elif score >= 60:
        return "#f59e0b"  # Amber
    else:
        return "#ef4444"  # Red


def render_status_badge(status: str) -> str:
    """Returns styled HTML badge for various statuses."""
    color_map = {
        # Payment Statuses
        "Paid": ("#065f46", "#d1fae5"),
        "Partially Paid": ("#92400e", "#fef3c7"),
        "Pending": ("#b45309", "#ffedd5"),
        "Overdue": ("#991b1b", "#fee2e2"),
        # Room Statuses
        "Vacant": ("#065f46", "#d1fae5"),
        "Occupied": ("#1e40af", "#dbeafe"),
        "Maintenance": ("#991b1b", "#fee2e2"),
        # Inspection Statuses
        "Inspected": ("#065f46", "#d1fae5"),
        "Pending Review": ("#92400e", "#fef3c7"),
        "Resubmission Requested": ("#991b1b", "#fee2e2"),
        # Damage Review Statuses
        "Verified": ("#991b1b", "#fee2e2"),
        "Not Damage": ("#065f46", "#d1fae5"),
        "Maintenance Scheduled": ("#1e40af", "#dbeafe"),
        # Maintenance Ticket Statuses
        "Submitted": ("#b45309", "#ffedd5"),
        "In Progress": ("#1e40af", "#dbeafe"),
        "Completed": ("#065f46", "#d1fae5"),
        "Cancelled": ("#4b5563", "#f3f4f6"),
        # Reward Statuses
        "Approved": ("#065f46", "#d1fae5"),
        "Rejected": ("#991b1b", "#fee2e2"),
        "Applied": ("#1e40af", "#dbeafe"),
    }

    text_color, bg_color = color_map.get(status, ("#374151", "#e5e7eb"))
    return (
        f'<span style="background-color: {bg_color}; color: {text_color}; '
        f'padding: 3px 10px; border-radius: 9999px; font-size: 0.82rem; '
        f'font-weight: 600; display: inline-block;">{status}</span>'
    )

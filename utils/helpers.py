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
        return "#2E7D32"  # Forest Green
    elif score >= 75:
        return "#AB7843"  # Caramel
    elif score >= 60:
        return "#C27803"  # Warm Amber
    else:
        return "#991B1B"  # Rustic Red


def render_status_badge(status: str) -> str:
    """Returns styled HTML badge for various statuses using the project palette."""
    color_map = {
        # Payment Statuses
        "Paid": ("#2B5329", "#EAF2EB", "#BCD6BF"),
        "Partially Paid": ("#4C2B08", "rgba(171, 120, 67, 0.2)", "#AB7843"),
        "Pending": ("#6D3914", "rgba(184, 149, 127, 0.22)", "#B8957F"),
        "Overdue": ("#7F1D1D", "#FEE2E2", "#FCA5A5"),
        # Room Statuses
        "Vacant": ("#2B5329", "#EAF2EB", "#BCD6BF"),
        "Occupied": ("#4C2B08", "rgba(109, 57, 20, 0.12)", "#6D3914"),
        "Maintenance": ("#7F1D1D", "#FEE2E2", "#FCA5A5"),
        # Inspection Statuses
        "Inspected": ("#2B5329", "#EAF2EB", "#BCD6BF"),
        "Pending Review": ("#6D3914", "rgba(184, 149, 127, 0.22)", "#B8957F"),
        "Resubmission Requested": ("#7F1D1D", "#FEE2E2", "#FCA5A5"),
        # Damage Review Statuses
        "Verified": ("#7F1D1D", "#FEE2E2", "#FCA5A5"),
        "Not Damage": ("#2B5329", "#EAF2EB", "#BCD6BF"),
        "Maintenance Scheduled": ("#4C2B08", "rgba(171, 120, 67, 0.2)", "#AB7843"),
        # Maintenance Ticket Statuses
        "Submitted": ("#6D3914", "rgba(184, 149, 127, 0.22)", "#B8957F"),
        "In Progress": ("#4C2B08", "rgba(171, 120, 67, 0.2)", "#AB7843"),
        "Completed": ("#2B5329", "#EAF2EB", "#BCD6BF"),
        "Cancelled": ("#5A4A42", "#EFE8E2", "#DDCFC6"),
        # Reward Statuses
        "Approved": ("#2B5329", "#EAF2EB", "#BCD6BF"),
        "Rejected": ("#7F1D1D", "#FEE2E2", "#FCA5A5"),
        "Applied": ("#4C2B08", "rgba(171, 120, 67, 0.2)", "#AB7843"),
    }

    text_color, bg_color, border_color = color_map.get(status, ("#35271E", "#EFE8E2", "#DDCFC6"))
    return (
        f'<span style="background-color: {bg_color}; color: {text_color}; '
        f'border: 1px solid {border_color}; '
        f'padding: 3px 11px; border-radius: 9999px; font-size: 0.8rem; '
        f'font-weight: 600; display: inline-block;">{status}</span>'
    )

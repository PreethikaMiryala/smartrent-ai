"""
SmartRent AI - Context-Aware Chatbot Service
"""
import json
from datetime import datetime
from typing import Generator, List, Dict, Any, Optional
import database
from services.groq_service import stream_groq_chat


def build_system_context(user: Dict[str, Any]) -> str:
    """
    Builds strict factual database context for the AI Assistant based on user role.
    Ensures tenants ONLY see their own data and owners have access to property-wide data.
    """
    role = user.get("role", "tenant")
    user_id = user.get("id")
    full_name = user.get("full_name", "User")
    current_month = datetime.now().strftime("%Y-%m")

    conn = database.get_db_connection()
    c = conn.cursor()

    context_lines = [
        f"You are SmartRent Assistant, the intelligent AI rental management co-pilot for SmartRent AI.",
        f"Today's date is {datetime.now().strftime('%d %B %Y')}. Active Billing Month: {current_month}.",
        f"You are speaking with: {full_name} (Role: {role.upper()}).",
        "STRICT PRIVACY & ACCURACY RULES:",
        "- Answer queries using ONLY the verified facts provided below from the SQLite database.",
        "- Do NOT invent, assume, or hallucinate rent amounts, tenant names, inspection results, or payments.",
        "- If the answer is not in the context, politely state that the information is not recorded in the system.",
        "- Format responses professionally with neat markdown, bullet points, and currency symbols (₹)."
    ]

    if role == "owner":
        context_lines.append("\n--- OWNER PROPERTY SUMMARY ---")
        metrics = database.get_dashboard_metrics(current_month)
        context_lines.append(
            f"Rooms Overview: Total: {metrics['total_rooms']}, Occupied: {metrics['occupied_rooms']}, "
            f"Vacant: {metrics['vacant_rooms']}. Total Active Tenants: {metrics['total_tenants']}."
        )
        context_lines.append(
            f"Financials ({current_month}): Expected Rent: ₹{metrics['expected_rent']:,.2f}, "
            f"Collected: ₹{metrics['collected_rent']:,.2f}, Pending: ₹{metrics['pending_rent']:,.2f}, "
            f"Discounts Awarded: ₹{metrics['discounts_awarded']:,.2f}."
        )

        # Rooms & Tenants
        c.execute("""
        SELECT r.room_number, r.monthly_rent, r.status as room_status, u.full_name, t.id as tenant_id
        FROM rooms r
        LEFT JOIN tenants t ON r.id = t.room_id AND t.status = 'Active'
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY r.room_number;
        """)
        rooms_data = c.fetchall()
        context_lines.append("\nRooms & Occupants:")
        for r in rooms_data:
            tenant_info = f"Occupied by {r['full_name']}" if r['full_name'] else f"Status: {r['room_status']}"
            context_lines.append(f"- Room {r['room_number']}: Base Rent ₹{r['monthly_rent']:,.2f} | {tenant_info}")

        # Rent Invoices for current month
        c.execute("""
        SELECT rr.*, u.full_name, r.room_number
        FROM rent_records rr
        JOIN tenants t ON rr.tenant_id = t.id
        JOIN users u ON t.user_id = u.id
        JOIN rooms r ON rr.room_id = r.id
        WHERE rr.month_year = ?;
        """, (current_month,))
        invoices = c.fetchall()
        context_lines.append(f"\nRent Status for {current_month}:")
        if invoices:
            for inv in invoices:
                context_lines.append(
                    f"- {inv['full_name']} ({inv['room_number']}): Base ₹{inv['base_rent']}, "
                    f"Discount ₹{inv['discount_amount']} ({inv['discount_percentage']}%), "
                    f"Final ₹{inv['final_rent']}, Paid ₹{inv['paid_amount']}, Balance ₹{inv['balance']} (Status: {inv['status']})"
                )
        else:
            context_lines.append(f"No rent invoices generated yet for {current_month}.")

        # Inspections for current month
        c.execute("""
        SELECT i.*, u.full_name, r.room_number
        FROM inspections i
        JOIN tenants t ON i.tenant_id = t.id
        JOIN users u ON t.user_id = u.id
        JOIN rooms r ON i.room_id = r.id
        WHERE i.month_year = ?;
        """, (current_month,))
        inspections = c.fetchall()
        context_lines.append(f"\nInspections for {current_month}:")
        submitted_tenant_ids = set()
        for insp in inspections:
            submitted_tenant_ids.add(insp['tenant_id'])
            context_lines.append(
                f"- {insp['full_name']} ({insp['room_number']}): Score: {insp['overall_score']}/100 ({insp['result_category']}) - "
                f"Reward Eligible: {'Yes' if insp['reward_eligible'] else 'No'}"
            )

        # Tenants who haven't submitted photographs
        c.execute("""
        SELECT t.id, u.full_name, r.room_number
        FROM tenants t
        JOIN users u ON t.user_id = u.id
        JOIN rooms r ON t.room_id = r.id
        WHERE t.status = 'Active';
        """)
        all_tenants = c.fetchall()
        not_submitted = [f"{t['full_name']} ({t['room_number']})" for t in all_tenants if t['id'] not in submitted_tenant_ids]
        if not_submitted:
            context_lines.append(f"\nTenants who have NOT yet submitted photos for {current_month}: {', '.join(not_submitted)}")

        # Damage Alerts
        c.execute("""
        SELECT da.*, r.room_number, u.full_name
        FROM damage_alerts da
        JOIN rooms r ON da.room_id = r.id
        JOIN tenants t ON da.tenant_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE da.status = 'Pending Review';
        """)
        alerts = c.fetchall()
        context_lines.append("\nPending Damage Alerts for Verification:")
        if alerts:
            for a in alerts:
                context_lines.append(
                    f"- {a['room_number']} ({a['full_name']}): Issue: {a['damage_category']} - '{a['description']}' "
                    f"(Severity: {a['severity']}, Confidence: {a['confidence']*100:.0f}%)"
                )
        else:
            context_lines.append("No pending damage alerts.")

        # Maintenance
        c.execute("""
        SELECT m.*, r.room_number, u.full_name
        FROM maintenance_requests m
        JOIN rooms r ON m.room_id = r.id
        JOIN tenants t ON m.tenant_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE m.status IN ('Submitted', 'In Progress');
        """)
        m_reqs = c.fetchall()
        context_lines.append("\nPending Maintenance Requests:")
        if m_reqs:
            for m in m_reqs:
                context_lines.append(f"- #{m['id']} {m['room_number']} ({m['full_name']}): [{m['priority']}] {m['title']} - {m['status']}")
        else:
            context_lines.append("No active maintenance tickets.")

    else:
        # Tenant role - ONLY tenant's private information
        c.execute("""
        SELECT t.*, r.room_number, r.monthly_rent, r.description as room_description
        FROM tenants t
        LEFT JOIN rooms r ON t.room_id = r.id
        WHERE t.user_id = ?;
        """, (user_id,))
        tenant = c.fetchone()

        if not tenant:
            context_lines.append("No active tenant record found for this profile.")
        else:
            t_id = tenant["id"]
            context_lines.append(f"\n--- YOUR TENANT PROFILE ---")
            context_lines.append(
                f"Assigned Room: {tenant['room_number']} | Base Monthly Rent: ₹{tenant['monthly_rent']:,.2f} | "
                f"Joining Date: {tenant['joining_date']}."
            )

            # Invoices
            c.execute("""
            SELECT * FROM rent_records 
            WHERE tenant_id = ? 
            ORDER BY month_year DESC LIMIT 3;
            """, (t_id,))
            tenant_invoices = c.fetchall()
            context_lines.append(f"\nYour Recent Invoices:")
            for inv in tenant_invoices:
                context_lines.append(
                    f"- Month {inv['month_year']}: Base ₹{inv['base_rent']}, Discount ₹{inv['discount_amount']} ({inv['discount_percentage']}%), "
                    f"Final Payable ₹{inv['final_rent']}, Paid ₹{inv['paid_amount']}, Remaining Balance: ₹{inv['balance']} (Status: {inv['status']})"
                )

            # Inspection Results
            c.execute("""
            SELECT * FROM inspections 
            WHERE tenant_id = ? 
            ORDER BY submission_date DESC LIMIT 2;
            """, (t_id,))
            tenant_inspections = c.fetchall()
            context_lines.append(f"\nYour Recent Inspections:")
            if tenant_inspections:
                for insp in tenant_inspections:
                    context_lines.append(
                        f"- Month {insp['month_year']}: Cleanliness Score: {insp['overall_score']}/100 ({insp['result_category']}). "
                        f"Reward Eligible: {'Yes' if insp['reward_eligible'] else 'No'}. "
                        f"Positive Observations: {insp['positive_observations']} | "
                        f"Areas for Improvement: {insp['areas_for_improvement']} | "
                        f"Recommendations: {insp['recommendations']}"
                    )
            else:
                context_lines.append("You have not submitted any room inspection photos yet.")

            # Rewards
            c.execute("SELECT * FROM rewards WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 3;", (t_id,))
            rewards = c.fetchall()
            context_lines.append(f"\nYour Rewards & Discount Status:")
            for rw in rewards:
                context_lines.append(
                    f"- Month {rw['month_year']}: Score {rw['cleanliness_score']}, "
                    f"Earned {rw['discount_percentage']}% discount (₹{rw['discount_amount']}), Status: {rw['status']}"
                )

            # Maintenance
            c.execute("SELECT * FROM maintenance_requests WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 3;", (t_id,))
            maint = c.fetchall()
            context_lines.append(f"\nYour Maintenance Requests:")
            for m in maint:
                context_lines.append(f"- #{m['id']}: {m['title']} [{m['priority']}] - Status: {m['status']}")

    conn.close()
    return "\n".join(context_lines)


def process_chat_message(
    user_message: str,
    user: Dict[str, Any],
    session_messages: List[Dict[str, str]]
) -> Generator[str, None, None]:
    """
    Constructs the prompt with database context, passes messages to Groq streaming service,
    and logs conversation in SQLite.
    """
    system_prompt = build_system_context(user)

    messages = [{"role": "system", "content": system_prompt}]
    # Add recent session history
    for msg in session_messages[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    full_response = ""
    for chunk in stream_groq_chat(messages=messages):
        full_response += chunk
        yield chunk

    # Save to chatbot_logs in database
    try:
        database.execute_query(
            "INSERT INTO chatbot_logs (user_id, role, query, response) VALUES (?, ?, ?, ?);",
            (user.get("id"), user.get("role", "tenant"), user_message, full_response),
            commit=True
        )
    except Exception:
        pass

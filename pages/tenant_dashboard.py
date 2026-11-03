"""
SmartRent AI - Tenant Personal Dashboard
"""
import streamlit as st
import pandas as pd
from datetime import datetime

import database
from utils.authentication import get_current_user, is_tenant
from utils.helpers import (
    format_currency,
    format_date,
    get_score_color,
    render_status_badge,
    get_current_month_str
)


def render_tenant_dashboard():
    if not is_tenant():
        st.error("⛔ Access Denied. This dashboard is for tenants only.")
        st.stop()

    user = get_current_user()
    tenant = database.get_tenant_by_user_id(user["id"])

    if not tenant:
        st.warning("⚠️ No active tenant assignment found for your user account. Please contact property management.")
        st.stop()

    current_month = get_current_month_str()
    st.title(f"👋 Welcome back, {user['full_name']}!")
    st.caption(f"Tenant Portal | Assigned Room: **{tenant['room_number']}** | Member since {format_date(tenant['joining_date'])}")

    # Top KPI Metrics for Tenant
    st.markdown("### 📌 At a Glance")
    k1, k2, k3, k4 = st.columns(4)

    # 1. Monthly Rent & Current Invoice
    invoices = database.get_tenant_rent_records(tenant["id"])
    curr_invoice = next((i for i in invoices if i["month_year"] == current_month), None)

    with k1:
        st.metric(
            label="Assigned Room Rent",
            value=format_currency(tenant["monthly_rent"]),
            delta=f"Room {tenant['room_number']}",
            delta_color="off"
        )

    with k2:
        if curr_invoice:
            st.metric(
                label=f"Current Invoice ({current_month})",
                value=format_currency(curr_invoice["final_rent"]),
                delta=f"Status: {curr_invoice['status']}",
                delta_color="normal" if curr_invoice['status'] == "Paid" else "inverse"
            )
        else:
            st.metric(label=f"Invoice ({current_month})", value="Not Generated", delta="Due around 5th")

    # 2. Latest Inspection Score & Reward Points
    inspections = database.get_tenant_inspections(tenant["id"])
    latest_insp = inspections[0] if inspections else None

    with k3:
        if latest_insp and latest_insp.get("overall_score"):
            st.metric(
                label="Latest Cleanliness Score",
                value=f"{latest_insp['overall_score']} / 100",
                delta=latest_insp["result_category"],
                delta_color="normal"
            )
        else:
            st.metric(label="Cleanliness Score", value="No Uploads Yet", delta="Upload room photos")

    # 3. Total Rewards & Active Discount
    rewards = database.get_tenant_rewards(tenant["id"])
    total_pts = sum(r.get("reward_points", 0) for r in rewards)
    latest_reward = rewards[0] if rewards else None

    with k4:
        st.metric(
            label="Cleanliness Reward Points",
            value=f"{total_pts} pts",
            delta=f"{latest_reward['discount_percentage']}% discount" if latest_reward else "0% discount",
            delta_color="normal" if latest_reward else "off"
        )

    st.markdown("---")

    # Main columns: Left = Room & Rent Details, Right = Cleanliness & AI Feedback
    col_left, col_right = st.columns([1.2, 1.3])

    with col_left:
        st.subheader("🏠 Your Room & Lease")
        st.markdown(f"""
        - **Room Number:** `{tenant['room_number']}`
        - **Base Rent:** `{format_currency(tenant['monthly_rent'])} / month`
        - **Description:** {tenant.get('room_description', 'Standard accommodation')}
        - **Lease Start Date:** {format_date(tenant['joining_date'])}
        - **Emergency Contact:** {tenant.get('emergency_contact', 'Not configured') or 'None'}
        """)

        st.markdown("#### 🧾 Payment History")
        if invoices:
            inv_df = pd.DataFrame([
                {
                    "Month": inv["month_year"],
                    "Base Rent": format_currency(inv["base_rent"]),
                    "Discount": f"{inv['discount_percentage']}% (-{format_currency(inv['discount_amount'])})",
                    "Final Rent": format_currency(inv["final_rent"]),
                    "Paid": format_currency(inv["paid_amount"]),
                    "Balance": format_currency(inv["balance"]),
                    "Status": inv["status"]
                }
                for inv in invoices[:5]
            ])
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
        else:
            st.info("No rent invoices generated yet.")

    with col_right:
        st.subheader("🤖 Latest AI Inspection Feedback")
        if latest_insp and latest_insp.get("overall_score"):
            score = latest_insp["overall_score"]
            color = get_score_color(score)
            st.markdown(f"""
            <div style="background-color: rgba(30, 41, 59, 0.05); padding: 16px; border-radius: 12px; border-left: 6px solid {color};">
                <h4 style="margin: 0; color: {color};">Score: {score} / 100 — {latest_insp['result_category']}</h4>
                <p style="margin-top: 6px; font-size: 0.88rem; color: #6b7280;">Inspection Date: {format_date(latest_insp['submission_date'])}</p>
                <p><strong>🌟 Positive Habits:</strong><br>{latest_insp.get('positive_observations', 'Well maintained overall.')}</p>
                <p><strong>🔍 Areas for Improvement:</strong><br>{latest_insp.get('areas_for_improvement', 'None detected.')}</p>
                <p><strong>💡 Cleaning Recommendations:</strong><br>{latest_insp.get('recommendations', 'Continue regular vacuuming and surface wiping.')}</p>
            </div>
            """, unsafe_allow_html=True)

            # Show category breakdown
            cat_scores = database.get_cleanliness_scores(latest_insp["id"])
            if cat_scores:
                st.markdown("##### Category Breakdown")
                for cs in cat_scores:
                    st.write(f"**{cs['category']}**: `{cs['score']}/100` — *{cs.get('notes', '')}*")
        else:
            st.info("You haven't submitted your room photographs for this month. Upload room photos to earn up to 10% rent discount!")

    st.markdown("---")

    # Maintenance Status Section
    st.subheader("🛠️ Active Maintenance Requests")
    maint_list = database.get_tenant_maintenance_requests(tenant["id"])
    if maint_list:
        for m in maint_list[:3]:
            st.markdown(f"- **[{m['priority']}] {m['title']}** — Status: `{m['status']}` ({format_date(m['created_at'])})")
            if m.get("owner_notes"):
                st.caption(f"  *Owner update:* {m['owner_notes']}")
    else:
        st.write("No active maintenance tickets.")


if __name__ == "__main__" or True:
    render_tenant_dashboard()

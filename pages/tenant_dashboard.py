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
        st.error("Access restricted to active tenants.")
        st.stop()
        return

    user = get_current_user()
    if not user:
        st.error("Please select an active tenant account.")
        st.stop()
        return

    tenant = database.get_tenant_by_user_id(user["id"])

    if not tenant:
        st.warning("No active tenant assignment found for your user account.")
        st.stop()

    current_month = get_current_month_str()
    st.title(f"Welcome, {user['full_name']}")
    st.caption(f"Tenant Account | Assigned Unit: Room {tenant['room_number']} | Lease Commenced: {format_date(tenant['joining_date'])}")

    st.subheader("Account Overview")
    k1, k2, k3, k4 = st.columns(4)

    # 1. Monthly Rent & Current Invoice
    invoices = database.get_tenant_rent_records(tenant["id"])
    curr_invoice = next((i for i in invoices if i["month_year"] == current_month), None)

    with k1:
        st.metric(
            label="Base Monthly Rent",
            value=format_currency(tenant["monthly_rent"]),
            delta=f"Unit {tenant['room_number']}",
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
            st.metric(label=f"Invoice ({current_month})", value="Not Generated", delta="Due 5th of Month")

    # 2. Latest Inspection Score & Reward Points
    inspections = database.get_tenant_inspections(tenant["id"])
    latest_insp = inspections[0] if inspections else None

    with k3:
        if latest_insp and latest_insp.get("overall_score"):
            st.metric(
                label="Cleanliness Score",
                value=f"{latest_insp['overall_score']} / 100",
                delta=latest_insp.get("result_category", "Standard"),
                delta_color="normal"
            )
        else:
            st.metric(label="Cleanliness Score", value="Pending", delta="Upload room photos")

    # 3. Total Rewards & Active Discount
    rewards = database.get_tenant_rewards(tenant["id"])
    total_pts = sum(r.get("reward_points", 0) for r in rewards)
    latest_reward = rewards[0] if rewards else None

    with k4:
        st.metric(
            label="Reward Points",
            value=f"{total_pts} pts",
            delta=f"{latest_reward['discount_percentage']}% discount" if latest_reward else "0% discount",
            delta_color="normal" if latest_reward else "off"
        )

    st.html('<div style="height: 1px; background-color: #E3D7CE; margin: 24px 0;"></div>')

    # Main columns: Left = Room & Rent Details, Right = Cleanliness & AI Feedback
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("Unit & Lease Information")
        unit_html = f"""<div style="background: #FFFFFF; border: 1px solid #E3D7CE; border-left: 4px solid #AB7843; border-radius: 12px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(53,39,30,0.04); margin-bottom: 24px;">
            <div style="margin-bottom: 8px; color: #35271E;"><strong style="color: #6D3914;">Assigned Unit:</strong> Unit {tenant['room_number']}</div>
            <div style="margin-bottom: 8px; color: #35271E;"><strong style="color: #6D3914;">Base Rent:</strong> {format_currency(tenant['monthly_rent'])} / month</div>
            <div style="margin-bottom: 8px; color: #35271E;"><strong style="color: #6D3914;">Description:</strong> {tenant.get('room_description', 'Standard residential unit')}</div>
            <div style="margin-bottom: 8px; color: #35271E;"><strong style="color: #6D3914;">Lease Start Date:</strong> {format_date(tenant['joining_date'])}</div>
            <div style="color: #35271E;"><strong style="color: #6D3914;">Emergency Contact:</strong> {tenant.get('emergency_contact', 'Not configured') or 'None on record'}</div>
        </div>"""
        st.html(unit_html)

        st.subheader("Payment History")
        if invoices:
            inv_df = pd.DataFrame([
                {
                    "Billing Month": inv["month_year"],
                    "Base": format_currency(inv["base_rent"]),
                    "Discount": f"{inv['discount_percentage']}% (-{format_currency(inv['discount_amount'])})",
                    "Net Due": format_currency(inv["final_rent"]),
                    "Paid": format_currency(inv["paid_amount"]),
                    "Balance": format_currency(inv["balance"]),
                    "Status": inv["status"]
                }
                for inv in invoices[:5]
            ])
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
        else:
            st.info("No rent invoices generated on record.")

    with col_right:
        st.subheader("Latest AI Inspection Feedback")
        if latest_insp and latest_insp.get("overall_score"):
            score = latest_insp["overall_score"]
            color = get_score_color(score)
            feedback_html = f"""<div style="background-color: #FFFFFF; border: 1px solid #E3D7CE; border-left: 5px solid {color}; padding: 18px 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(53,39,30,0.04); margin-bottom: 18px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 1.3rem; font-weight: 800; color: {color};">Score: {score} / 100</span>
                    <span style="font-size: 0.78rem; font-weight: 700; color: #4C2B08; background-color: rgba(184, 149, 127, 0.22); border: 1px solid #B8957F; padding: 3px 12px; border-radius: 9999px;">{latest_insp['result_category']}</span>
                </div>
                <div style="font-size: 0.8rem; color: #8C7465; margin-bottom: 14px;">Evaluated on: {format_date(latest_insp['submission_date'])}</div>
                <div style="margin-bottom: 12px;">
                    <div style="font-weight: 700; color: #6D3914; font-size: 0.88rem; margin-bottom: 2px;">Positive Observations:</div>
                    <div style="font-size: 0.88rem; color: #35271E; line-height: 1.45;">{latest_insp.get('positive_observations', 'Well maintained overall.')}</div>
                </div>
                <div style="margin-bottom: 12px;">
                    <div style="font-weight: 700; color: #AB7843; font-size: 0.88rem; margin-bottom: 2px;">Areas for Improvement:</div>
                    <div style="font-size: 0.88rem; color: #35271E; line-height: 1.45;">{latest_insp.get('areas_for_improvement', 'None detected.')}</div>
                </div>
                <div>
                    <div style="font-weight: 700; color: #4C2B08; font-size: 0.88rem; margin-bottom: 2px;">Cleaning Recommendations:</div>
                    <div style="font-size: 0.88rem; color: #35271E; line-height: 1.45;">{latest_insp.get('recommendations', 'Continue regular dusting and maintenance.')}</div>
                </div>
            </div>"""
            st.html(feedback_html)

            # Show category breakdown
            cat_scores = database.get_cleanliness_scores(latest_insp["id"])
            if cat_scores:
                st.markdown("##### Category Breakdown")
                for cs in cat_scores:
                    cs_col = get_score_color(cs['score'])
                    cat_html = f"""<div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 14px; background: #FFFFFF; border: 1px solid #E3D7CE; border-radius: 8px; margin-bottom: 6px;">
                        <span style="font-weight: 600; color: #35271E; font-size: 0.88rem;">{cs['category']}</span>
                        <span style="font-weight: 800; color: {cs_col}; font-size: 0.95rem;">{cs['score']} / 100</span>
                    </div>"""
                    st.html(cat_html)
        else:
            st.info("No room inspection submitted for this billing cycle. Upload photos to unlock rent discounts.")

    st.html('<div style="height: 1px; background-color: #E3D7CE; margin: 24px 0;"></div>')

    # Maintenance Status Section
    st.subheader("Active Maintenance Requests")
    maint_list = database.get_tenant_maintenance_requests(tenant["id"])
    if maint_list:
        for m in maint_list[:3]:
            prio_color = "#991B1B" if m["priority"] == "Urgent" else ("#C27803" if m["priority"] == "High" else "#6D3914")
            m_notes = f'<div style="font-size: 0.82rem; color: #6D3914; margin-top: 6px; background: rgba(184, 149, 127, 0.12); padding: 6px 10px; border-radius: 6px;"><strong>Update:</strong> {m["owner_notes"]}</div>' if m.get("owner_notes") else ''
            ticket_html = f"""<div style="background: #FFFFFF; border: 1px solid #E3D7CE; border-left: 4px solid {prio_color}; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(53,39,30,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #35271E; font-size: 0.92rem;">{m['title']}</strong>
                    {render_status_badge(m['status'])}
                </div>
                <div style="font-size: 0.82rem; color: #8C7465; margin-top: 4px;">Priority: <strong style="color: {prio_color};">{m['priority']}</strong> | Reported: {format_date(m['created_at'])}</div>
                {m_notes}
            </div>"""
            st.html(ticket_html)
    else:
        st.write("No active maintenance tickets on record.")


if __name__ == "__main__" or True:
    render_tenant_dashboard()

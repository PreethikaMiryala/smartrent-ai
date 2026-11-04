"""
SmartRent AI - Owner / Administrator Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import database
from utils.authentication import is_owner
from utils.helpers import (
    format_currency,
    format_date,
    get_score_color,
    render_status_badge,
    get_month_options,
    get_current_month_str
)


def render_owner_dashboard():
    if not is_owner():
        st.error("Access Denied. This dashboard is only accessible to Property Owners.")
        st.stop()

    # Top Header & Month Filter
    col_title, col_month = st.columns([3, 1])
    with col_title:
        st.title("Property Management Dashboard")
        st.caption("Real-time overview of rooms, tenant occupancy, financial cashflow, AI inspections, and property health.")

    months = get_month_options(past_months=5, future_months=1)
    current_m = get_current_month_str()
    default_idx = months.index(current_m) if current_m in months else 0

    with col_month:
        selected_month = st.selectbox("Billing Cycle", options=months, index=default_idx)

    # Fetch real SQLite metrics
    metrics = database.get_dashboard_metrics(selected_month)

    # Row 1: KPI Metric Cards
    st.markdown("### Key Performance Indicators")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        st.metric(
            label="Total Rooms",
            value=metrics["total_rooms"],
            delta=f"{metrics['occupied_rooms']} Occupied | {metrics['vacant_rooms']} Vacant",
            delta_color="normal"
        )

    with kpi_col2:
        collection_pct = (
            (metrics["collected_rent"] / metrics["expected_rent"] * 100) 
            if metrics["expected_rent"] > 0 else 0
        )
        st.metric(
            label=f"Rent Collected ({selected_month})",
            value=format_currency(metrics["collected_rent"]),
            delta=f"{collection_pct:.1f}% collected",
            delta_color="normal"
        )

    with kpi_col3:
        st.metric(
            label="Pending / Unpaid Rent",
            value=format_currency(metrics["pending_rent"]),
            delta=f"-{format_currency(metrics['discounts_awarded'])} AI Discounts",
            delta_color="inverse"
        )

    with kpi_col4:
        st.metric(
            label="Cleanliness Average",
            value=f"{metrics['avg_cleanliness']} / 100",
            delta=f"{metrics['pending_damage_alerts']} Damage Alert{'s' if metrics['pending_damage_alerts'] != 1 else ''}",
            delta_color="off" if metrics['pending_damage_alerts'] == 0 else "inverse"
        )

    st.markdown("---")

    # Row 2: Visual Charts (Plotly)
    c_left, c_mid, c_right = st.columns([1.2, 1.2, 1.2])

    with c_left:
        st.subheader("Room Occupancy")
        occ_labels = ["Occupied", "Vacant", "Maintenance"]
        # Fetch room status counts
        rooms = database.get_all_rooms()
        occ_counts = [
            sum(1 for r in rooms if r["status"] == "Occupied"),
            sum(1 for r in rooms if r["status"] == "Vacant"),
            sum(1 for r in rooms if r["status"] == "Maintenance")
        ]
        fig_occ = px.pie(
            names=occ_labels,
            values=occ_counts,
            hole=0.55,
            color=occ_labels,
            color_discrete_map={
                "Occupied": "#6D3914",
                "Vacant": "#AB7843",
                "Maintenance": "#B8957F"
            }
        )
        fig_occ.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260, showlegend=True)
        st.plotly_chart(fig_occ, use_container_width=True)

    with c_right:
        st.subheader("Cleanliness Scores")
        inspections = database.get_all_inspections(selected_month)
        if inspections and any(i.get("overall_score") for i in inspections):
            clean_df = pd.DataFrame([
                {"Tenant": i["tenant_name"], "Score": i["overall_score"], "Room": i["room_number"]}
                for i in inspections if i.get("overall_score")
            ])
            fig_clean = px.bar(
                clean_df,
                x="Room",
                y="Score",
                color="Score",
                text="Score",
                range_y=[0, 100],
                color_continuous_scale=[[0, "#B8957F"], [0.5, "#AB7843"], [1, "#6D3914"]]
            )
            fig_clean.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260)
            st.plotly_chart(fig_clean, use_container_width=True)
        else:
            st.info(f"No completed inspections for {selected_month} yet.")

    with c_mid:
        st.subheader("Cashflow Breakdown")
        cash_labels = ["Collected", "Pending", "Discounts"]
        cash_vals = [
            metrics["collected_rent"],
            metrics["pending_rent"],
            metrics["discounts_awarded"]
        ]
        fig_cash = px.bar(
            x=cash_labels,
            y=cash_vals,
            color=cash_labels,
            color_discrete_map={
                "Collected": "#6D3914",
                "Pending": "#4C2B08",
                "Discounts": "#AB7843"
            }
        )
        fig_cash.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=260,
            showlegend=False,
            yaxis_title=f"Amount ({database.get_setting('currency', '₹')})"
        )
        st.plotly_chart(fig_cash, use_container_width=True)

    st.markdown("---")

    # Row 3: Actionable Feeds (Recent Payments, Recent Inspections, Maintenance Alerts)
    col_act1, col_act2 = st.columns(2)

    with col_act1:
        st.subheader("Recent Payment Transactions")
        payments = database.get_all_payments()
        if payments:
            pay_df = pd.DataFrame([
                {
                    "Date": format_date(p["payment_date"]),
                    "Tenant": p["tenant_name"],
                    "Room": p["room_number"],
                    "Amount": format_currency(p["amount"]),
                    "Method": p["payment_method"],
                    "Ref": p.get("transaction_reference", "-") or "-"
                }
                for p in payments[:6]
            ])
            st.dataframe(pay_df, use_container_width=True, hide_index=True)
        else:
            st.info("No recorded payment transactions yet.")

    with col_act2:
        st.subheader("Pending Maintenance & Damage Alerts")
        alerts = database.get_all_damage_alerts()
        unverified_alerts = [a for a in alerts if a["status"] == "Pending Review"]
        
        maint_reqs = database.get_all_maintenance_requests()
        open_maint = [m for m in maint_reqs if m["status"] in ("Submitted", "In Progress")]

        if unverified_alerts or open_maint:
            for a in unverified_alerts[:3]:
                st.warning(
                    f"Damage Alert: {a['room_number']} ({a['tenant_name']}) - "
                    f"**{a['damage_category']}**: {a['description']} (Severity: {a['severity']})"
                )
            for m in open_maint[:3]:
                st.info(
                    f"Maintenance #{m['id']}: {m['room_number']} ({m['tenant_name']}) - "
                    f"**[{m['priority']}] {m['title']}** (Status: {m['status']})"
                )
        else:
            st.success("No pending damage alerts or unresolved maintenance tickets.")


if __name__ == "__main__" or True:
    render_owner_dashboard()

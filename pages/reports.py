"""
SmartRent AI - Analytics, Reports & CSV Data Export Module
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

import database
from utils.authentication import is_owner
from utils.helpers import format_currency, format_date, get_month_options, get_current_month_str


def render_reports():
    if not is_owner():
        st.error("⛔ Access Denied. Reports are accessible only to Property Owners.")
        st.stop()

    st.title("📈 Analytics & Property Financial Reports")
    st.caption("Deep-dive analytics, tenant cleanliness trends, income tracking, and exportable CSV ledgers.")

    tab_financial, tab_cleanliness, tab_maintenance, tab_exports = st.tabs([
        "💰 Financial & Rent Analytics",
        "🧹 Cleanliness Trends",
        "🔧 Maintenance & Damage Reports",
        "📥 Data Export Center (CSV)"
    ])

    with tab_financial:
        st.subheader("Monthly Rental Cashflow")
        all_invoices = database.get_all_rent_records()
        
        if all_invoices:
            df_inv = pd.DataFrame(all_invoices)
            
            # Monthly summary aggregation
            monthly_agg = df_inv.groupby("month_year").agg({
                "base_rent": "sum",
                "discount_amount": "sum",
                "final_rent": "sum",
                "paid_amount": "sum",
                "balance": "sum"
            }).reset_index().sort_values("month_year")

            fig_cash = go.Figure()
            fig_cash.add_trace(go.Bar(
                x=monthly_agg["month_year"],
                y=monthly_agg["final_rent"],
                name="Billed Rent (₹)",
                marker_color="#6D3914"
            ))
            fig_cash.add_trace(go.Bar(
                x=monthly_agg["month_year"],
                y=monthly_agg["paid_amount"],
                name="Collected (₹)",
                marker_color="#AB7843"
            ))
            fig_cash.add_trace(go.Bar(
                x=monthly_agg["month_year"],
                y=monthly_agg["balance"],
                name="Outstanding Balance (₹)",
                marker_color="#4C2B08"
            ))
            fig_cash.update_layout(
                barmode="group",
                title="Monthly Billed vs Collected vs Outstanding Rent",
                xaxis_title="Billing Month",
                yaxis_title="Amount (₹)",
                height=350,
                margin=dict(t=40, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_cash, use_container_width=True)

            # Collection efficiency metrics
            total_billed = df_inv["final_rent"].sum()
            total_collected = df_inv["paid_amount"].sum()
            total_discounts = df_inv["discount_amount"].sum()
            eff_rate = (total_collected / total_billed * 100) if total_billed > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Cumulative Billed", format_currency(total_billed))
            m2.metric("Cumulative Collected", format_currency(total_collected))
            m3.metric("Collection Efficiency", f"{eff_rate:.1f}%")
            m4.metric("Total Cleanliness Savings Given", format_currency(total_discounts))

        else:
            st.info("No rent records available for analytics.")

    with tab_cleanliness:
        st.subheader("Tenant Cleanliness Performance")
        inspections = database.get_all_inspections()

        if inspections:
            df_insp = pd.DataFrame(inspections)
            df_scored = df_insp[df_insp["overall_score"].notnull()]

            if not df_scored.empty:
                col_c1, col_c2 = st.columns(2)

                with col_c1:
                    fig_dist = px.histogram(
                        df_scored,
                        x="overall_score",
                        nbins=10,
                        title="Distribution of Cleanliness Scores",
                        labels={"overall_score": "Score (out of 100)"},
                        color_discrete_sequence=["#AB7843"]
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)

                with col_c2:
                    # Category breakdown pie
                    cat_counts = df_scored["result_category"].value_counts().reset_index()
                    cat_counts.columns = ["Category", "Count"]
                    fig_pie = px.pie(
                        cat_counts,
                        names="Category",
                        values="Count",
                        title="Score Tiers Share",
                        color="Category",
                        color_discrete_map={
                            "Excellent": "#2E7D32",
                            "Good": "#AB7843",
                            "Average": "#6D3914",
                            "Needs Improvement": "#991B1B"
                        }
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                # Tenant rankings table
                st.markdown("##### Cleanliness Leaderboard")
                t_rank = df_scored.groupby(["tenant_name", "room_number"]).agg({
                    "overall_score": ["count", "mean", "max"]
                }).reset_index()
                t_rank.columns = ["Tenant", "Room", "Inspections Completed", "Average Score", "Best Score"]
                t_rank["Average Score"] = t_rank["Average Score"].round(1)
                t_rank = t_rank.sort_values("Average Score", ascending=False)
                st.dataframe(t_rank, use_container_width=True, hide_index=True)
            else:
                st.info("No completed inspections recorded yet.")
        else:
            st.info("No inspection data available.")

    with tab_maintenance:
        st.subheader("Property Upkeep & Maintenance Breakdown")
        m_reqs = database.get_all_maintenance_requests()
        d_alerts = database.get_all_damage_alerts()

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            if m_reqs:
                df_m = pd.DataFrame(m_reqs)
                cat_m = df_m["category"].value_counts().reset_index()
                cat_m.columns = ["Issue Category", "Tickets"]
                fig_mcat = px.bar(cat_m, x="Issue Category", y="Tickets", color="Issue Category", title="Maintenance by Category")
                fig_mcat.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig_mcat, use_container_width=True)
            else:
                st.info("No maintenance tickets recorded.")

        with col_m2:
            if d_alerts:
                df_d = pd.DataFrame(d_alerts)
                dam_cat = df_d["damage_category"].value_counts().reset_index()
                dam_cat.columns = ["Damage Type", "Alerts"]
                fig_dam = px.pie(dam_cat, names="Damage Type", values="Alerts", title="AI Detected Damage Types")
                fig_dam.update_layout(height=300)
                st.plotly_chart(fig_dam, use_container_width=True)
            else:
                st.info("No damage alerts recorded.")

    with tab_exports:
        st.subheader("📥 Download Property Data Ledgers (CSV)")
        st.caption("Export clean datasets for accounting, auditing, and tax documentation.")

        c_exp1, c_exp2 = st.columns(2)

        with c_exp1:
            st.markdown("##### 1. Rent Invoices & Balances")
            invoices = database.get_all_rent_records()
            if invoices:
                df_inv_exp = pd.DataFrame(invoices)
                csv_inv = df_inv_exp.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Download Rent Invoices (CSV)",
                    data=csv_inv,
                    file_name=f"smartrent_invoices_{get_current_month_str()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("##### 2. Payment Transaction History")
            payments = database.get_all_payments()
            if payments:
                df_pay_exp = pd.DataFrame(payments)
                csv_pay = df_pay_exp.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Download Payments Ledger (CSV)",
                    data=csv_pay,
                    file_name=f"smartrent_payments_{get_current_month_str()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with c_exp2:
            st.markdown("##### 3. AI Cleanliness Inspections")
            inspections = database.get_all_inspections()
            if inspections:
                df_insp_exp = pd.DataFrame(inspections)
                # Drop raw json for clean export
                if "ai_analysis_raw" in df_insp_exp.columns:
                    df_insp_exp = df_insp_exp.drop(columns=["ai_analysis_raw"])
                csv_insp = df_insp_exp.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Download Inspection Reports (CSV)",
                    data=csv_insp,
                    file_name=f"smartrent_inspections_{get_current_month_str()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("##### 4. Maintenance Tickets")
            maintenance = database.get_all_maintenance_requests()
            if maintenance:
                df_maint_exp = pd.DataFrame(maintenance)
                csv_maint = df_maint_exp.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Download Maintenance Tickets (CSV)",
                    data=csv_maint,
                    file_name=f"smartrent_maintenance_{get_current_month_str()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )


if __name__ == "__main__" or True:
    render_reports()

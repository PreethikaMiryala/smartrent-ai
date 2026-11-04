"""
SmartRent AI - Rent Invoicing and Payment Management
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
import database
from services.rent_service import generate_monthly_invoices, record_payment, check_and_update_overdue_statuses
from utils.authentication import is_owner, is_tenant, get_current_user
from utils.helpers import (
    format_currency,
    format_date,
    render_status_badge,
    get_month_options,
    get_current_month_str
)
from config import PAYMENT_METHODS


def render_rent_payments():
    user = get_current_user()
    if not user:
        st.error("Please log in to view rent records.")
        st.stop()
        return

    # Automatically refresh overdue status
    check_and_update_overdue_statuses()

    st.title("Rent & Payments")

    if is_owner():
        _render_owner_rent_view(user)
    else:
        _render_tenant_rent_view(user)


def _render_owner_rent_view(user):
    st.caption("Generate monthly invoices, record tenant payments, track balances, and view transaction history.")

    # Top Month Filter & Invoice Generator
    months = get_month_options(past_months=6, future_months=1)
    current_m = get_current_month_str()
    default_idx = months.index(current_m) if current_m in months else 0

    c_filter, c_btn = st.columns([2, 1.5])
    with c_filter:
        selected_month = st.selectbox("Billing Cycle Filter", options=["All Months"] + months, index=1)
    with c_btn:
        st.write("") # spacing
        with st.popover("Generate Monthly Invoices"):
            st.write("Generate rent invoices for all active tenants.")
            inv_month = st.selectbox("Target Month", options=months, index=default_idx, key="inv_m_select")
            due_day = st.number_input("Due Date (Day of Month)", min_value=1, max_value=28, value=5)
            if st.button("Generate Invoices Now", type="primary", use_container_width=True):
                created, skipped = generate_monthly_invoices(inv_month, due_day=due_day)
                if created > 0:
                    st.success(f"Generated {created} invoices for {inv_month} with approved discounts applied.")
                else:
                    st.info(f"No new invoices created. {', '.join(skipped) if skipped else 'All active tenants already have invoices.'}")
                st.rerun()

    # Query invoices
    month_filter = None if selected_month == "All Months" else selected_month
    invoices = database.get_all_rent_records(month_filter)

    # Invoices Financial Summary
    total_expected = sum(i["final_rent"] for i in invoices)
    total_collected = sum(i["paid_amount"] for i in invoices)
    total_balance = sum(i["balance"] for i in invoices)
    total_discounts = sum(i["discount_amount"] for i in invoices)

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Final Rent Billed", format_currency(total_expected))
    sc2.metric("Collected", format_currency(total_collected))
    sc3.metric("Outstanding Balance", format_currency(total_balance))
    sc4.metric("Discounts Awarded", format_currency(total_discounts))

    st.markdown("---")

    tab_invoices, tab_payments = st.tabs(["Invoices & Collection", "Payment Transaction Ledger"])

    with tab_invoices:
        # Search & Status Filter
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            q_search = st.text_input("Search invoice by tenant name or room", "")
        with col_s2:
            st_filter = st.selectbox("Filter Payment Status", ["All", "Pending", "Partially Paid", "Paid", "Overdue"])

        filtered_inv = invoices
        if st_filter != "All":
            filtered_inv = [i for i in filtered_inv if i["status"] == st_filter]
        if q_search.strip():
            qs = q_search.strip().lower()
            filtered_inv = [
                i for i in filtered_inv 
                if qs in i["tenant_name"].lower() or qs in i["room_number"].lower()
            ]

        if not filtered_inv:
            st.info("No rent records match the selected filters.")
        else:
            for inv in filtered_inv:
                with st.expander(
                    f"Unit {inv['room_number']} — {inv['tenant_name']} | Month: {inv['month_year']} | "
                    f"Due: {format_currency(inv['final_rent'])} | Paid: {format_currency(inv['paid_amount'])} | Status: {inv['status']}",
                    expanded=False
                ):
                    col_det, col_rec = st.columns([2, 1.2])

                    with col_det:
                        st.markdown(f"""
                        - **Base Monthly Rent:** `{format_currency(inv['base_rent'])}`
                        - **AI Cleanliness Discount:** `{inv['discount_percentage']}%` (-{format_currency(inv['discount_amount'])})
                        - **Final Net Payable:** `{format_currency(inv['final_rent'])}`
                        - **Total Paid to Date:** `{format_currency(inv['paid_amount'])}`
                        - **Remaining Due Balance:** `{format_currency(inv['balance'])}`
                        - **Payment Due Date:** {format_date(inv['due_date'])}
                        """)

                        # Show payments for this invoice
                        prev_pays = database.get_payments_for_rent_record(inv["id"])
                        if prev_pays:
                            st.markdown("##### Payment Receipts for this Invoice:")
                            for p in prev_pays:
                                st.caption(
                                    f"• **{format_date(p['payment_date'])}**: Received **{format_currency(p['amount'])}** via "
                                    f"*{p['payment_method']}* (Ref: {p.get('transaction_reference', 'N/A') or 'N/A'})"
                                )

                    with col_rec:
                        if inv["balance"] > 0:
                            st.markdown("##### Record Payment")
                            with st.form(f"form_pay_{inv['id']}", clear_on_submit=True):
                                pay_amount = st.number_input(
                                    "Amount Received (₹)*",
                                    min_value=1.0,
                                    max_value=float(inv["balance"]),
                                    value=float(inv["balance"]),
                                    step=100.0,
                                    key=f"pay_amt_{inv['id']}"
                                )
                                pay_method = st.selectbox("Payment Method", PAYMENT_METHODS, key=f"pay_mth_{inv['id']}")
                                pay_date = st.date_input("Date Received", value=date.today(), key=f"pay_dt_{inv['id']}")
                                pay_ref = st.text_input("Ref / UTR / Cheque #", placeholder="e.g. UPI/39102831", key=f"pay_ref_{inv['id']}")
                                pay_notes = st.text_input("Notes", placeholder="e.g. Google Pay transaction", key=f"pay_nt_{inv['id']}")

                                btn_record = st.form_submit_button("Record Payment", type="primary", use_container_width=True)
                                if btn_record:
                                    success, msg = record_payment(
                                        rent_record_id=inv["id"],
                                        amount=float(pay_amount),
                                        payment_date=pay_date.isoformat(),
                                        payment_method=pay_method,
                                        transaction_reference=pay_ref.strip(),
                                        notes=pay_notes.strip(),
                                        recorded_by=user["id"]
                                    )
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        else:
                            st.success("Fully Paid. No outstanding balance.")

    with tab_payments:
        st.subheader("All Transaction Records")
        all_payments = database.get_all_payments()
        if all_payments:
            pay_df = pd.DataFrame([
                {
                    "Payment ID": f"#{p['id']}",
                    "Date": format_date(p["payment_date"]),
                    "Tenant": p["tenant_name"],
                    "Room": p["room_number"],
                    "Month": p["month_year"],
                    "Amount": format_currency(p["amount"]),
                    "Method": p["payment_method"],
                    "Reference": p.get("transaction_reference", "-") or "-",
                    "Notes": p.get("notes", "-") or "-"
                }
                for p in all_payments
            ])
            st.dataframe(pay_df, use_container_width=True, hide_index=True)
        else:
            st.info("No recorded payments in the system yet.")


def _render_tenant_rent_view(user):
    st.caption("Review your monthly rent invoices, payment receipts, cleanliness discounts, and outstanding balances.")

    tenant = database.get_tenant_by_user_id(user["id"])
    if not tenant:
        st.warning("No tenant assignment found.")
        st.stop()

    invoices = database.get_tenant_rent_records(tenant["id"])

    if not invoices:
        st.info("No rent invoices have been generated for your room yet.")
        return

    # Outstanding alert
    unpaid_total = sum(i["balance"] for i in invoices)
    if unpaid_total > 0:
        st.warning(f"You have an outstanding total balance of **{format_currency(unpaid_total)}** across your invoices.")
    else:
        st.success("All your rent invoices are up to date and fully paid.")

    st.markdown("### Invoices & Payment Statements")
    for inv in invoices:
        with st.expander(
            f"Month: {inv['month_year']} — Final Payable: {format_currency(inv['final_rent'])} | "
            f"Paid: {format_currency(inv['paid_amount'])} | Status: {inv['status']}",
            expanded=(inv["balance"] > 0)
        ):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"""
                - **Base Room Rent:** `{format_currency(inv['base_rent'])}`
                - **AI Cleanliness Discount:** `{inv['discount_percentage']}%` (-{format_currency(inv['discount_amount'])})
                - **Final Payable Rent:** `{format_currency(inv['final_rent'])}`
                - **Amount Paid:** `{format_currency(inv['paid_amount'])}`
                - **Outstanding Balance:** `{format_currency(inv['balance'])}`
                - **Due Date:** {format_date(inv['due_date'])}
                """)

                # Payments for this record
                payments = database.get_payments_for_rent_record(inv["id"])
                if payments:
                    st.markdown("##### Payment Receipts:")
                    for p in payments:
                        st.caption(
                            f"• {format_date(p['payment_date'])}: Paid **{format_currency(p['amount'])}** via "
                            f"{p['payment_method']} (Ref: {p.get('transaction_reference', 'N/A') or 'N/A'})"
                        )

            with c2:
                if inv["balance"] > 0:
                    st.info(f"Balance Due: **{format_currency(inv['balance'])}**")
                    st.caption("To settle this invoice, please pay via UPI or Bank Transfer and notify property management:")
                    st.code(f"UPI ID: rent@smartrent.ai\nAmount: {format_currency(inv['balance'])}")
                else:
                    st.success("This invoice is fully settled.")


if __name__ == "__main__" or True:
    render_rent_payments()

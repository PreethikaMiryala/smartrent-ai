"""
SmartRent AI - AI Tenant Reward & Rent Discount System
"""
import streamlit as st
import pandas as pd
import json

import database
from services.reward_service import (
    get_configured_reward_tiers,
    get_configured_max_discount,
    approve_reward_and_apply_to_rent,
    reject_reward
)
from utils.authentication import is_owner, is_tenant, get_current_user
from utils.helpers import format_currency, format_date, get_score_color, render_status_badge


def render_rewards():
    user = get_current_user()
    if not user:
        st.error("Please log in to access Rewards & Discounts.")
        st.stop()
        return

    st.title("Cleanliness Rewards & Rent Discounts")

    if is_owner():
        _render_owner_rewards(user)
    else:
        _render_tenant_rewards(user)


def _render_owner_rewards(user):
    st.caption("Approve or reject AI-recommended rent discounts for clean rooms, review reward history, and configure discount policies.")

    rewards = database.get_all_rewards()

    # Summary Metrics
    c1, c2, c3, c4 = st.columns(4)
    pending_r = [r for r in rewards if r["status"] == "Pending Approval"]
    approved_r = [r for r in rewards if r["status"] in ("Approved", "Applied")]
    total_savings = sum(r["discount_amount"] for r in approved_r)

    c1.metric("Pending Approvals", len(pending_r), delta="Action Needed" if pending_r else "All Processed")
    c2.metric("Approved / Applied Discounts", len(approved_r))
    c3.metric("Total Tenant Discounts Given", format_currency(total_savings))
    c4.metric("Max Configured Cap", f"{get_configured_max_discount()}%")

    st.markdown("---")

    tab_approval, tab_history, tab_config = st.tabs([
        f"Approval Queue ({len(pending_r)})",
        "Reward History Ledger",
        "Reward Policy Configuration"
    ])

    with tab_approval:
        st.subheader("Pending Discount Recommendations")
        if not pending_r:
            st.success("All AI discount recommendations have been processed.")
        else:
            for r in pending_r:
                score = r.get("cleanliness_score", 0.0)
                color = get_score_color(score)

                with st.expander(
                    f"Unit {r['room_number']} — {r['tenant_name']} | Month: {r['month_year']} | "
                    f"Score: {score}/100 | Discount: {r['discount_percentage']}% (-{format_currency(r['discount_amount'])})",
                    expanded=True
                ):
                    c_info, c_acts = st.columns([2, 1])
                    with c_info:
                        st.markdown(f"""
                        - **Tenant Name:** `{r['tenant_name']}` (Unit: `{r['room_number']}`)
                        - **Inspection Cleanliness Score:** <span style="color: {color}; font-weight: bold;">{score} / 100</span>
                        - **Reward Points:** `{r.get('reward_points', 0)} pts`
                        - **Recommended Discount:** `{r['discount_percentage']}%`
                        - **Rent Deduction Amount:** **{format_currency(r['discount_amount'])}**
                        - **Billing Month:** `{r['month_year']}`
                        """, unsafe_allow_html=True)

                    with c_acts:
                        st.markdown("##### Owner Action")
                        o_comm = st.text_input("Owner Comments (Optional)", placeholder="e.g. Approved for spotless maintenance", key=f"comm_{r['id']}")

                        btn_app, btn_rej = st.columns(2)
                        with btn_app:
                            if st.button("Approve", key=f"app_{r['id']}", type="primary", use_container_width=True):
                                success, msg = approve_reward_and_apply_to_rent(r["id"], owner_comments=o_comm.strip())
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with btn_rej:
                            if st.button("Reject", key=f"rej_{r['id']}", use_container_width=True):
                                success, msg = reject_reward(r["id"], owner_comments=o_comm.strip() or "Owner declined discount")
                                st.info(msg)
                                st.rerun()

    with tab_history:
        st.subheader("Historical Reward Records")
        if rewards:
            r_df = pd.DataFrame([
                {
                    "Reward ID": f"#{rw['id']}",
                    "Month": rw["month_year"],
                    "Tenant": rw["tenant_name"],
                    "Room": rw["room_number"],
                    "Cleanliness Score": f"{rw['cleanliness_score']}/100",
                    "Discount %": f"{rw['discount_percentage']}%",
                    "Deduction": format_currency(rw["discount_amount"]),
                    "Points": rw.get("reward_points", 0),
                    "Status": rw["status"],
                    "Owner Feedback": rw.get("owner_comments", "-") or "-"
                }
                for rw in rewards
            ])
            st.dataframe(r_df, use_container_width=True, hide_index=True)
        else:
            st.info("No reward records created yet.")

    with tab_config:
        st.subheader("Configure AI Cleanliness Reward Rules")
        st.caption("Customize the scoring brackets, discount percentages, and overall discount cap.")

        tiers = get_configured_reward_tiers()
        current_cap = get_configured_max_discount()

        with st.form("form_reward_config"):
            st.markdown("##### Cleanliness Score Brackets & Discounts")
            new_tiers = []
            for idx, tier in enumerate(tiers):
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    st.write(f"**Tier {idx+1}: {tier.get('label', '')}**")
                    st.caption(f"Score Range: {tier['min']} - {tier['max']}")
                with tc2:
                    new_pct = st.number_input(
                        f"Discount % ({tier['min']}-{tier['max']} pts)",
                        min_value=0.0,
                        max_value=50.0,
                        value=float(tier["discount_pct"]),
                        step=0.5,
                        key=f"tier_pct_{idx}"
                    )
                with tc3:
                    st.caption(f"Example: ₹8,000 rent saves {format_currency(8000 * new_pct / 100)}")

                new_tiers.append({
                    "min": tier["min"],
                    "max": tier["max"],
                    "discount_pct": new_pct,
                    "label": tier.get("label", "")
                })

            st.markdown("---")
            new_cap = st.number_input("Maximum Discount Cap Percentage (%)", min_value=1.0, max_value=50.0, value=float(current_cap), step=1.0)

            btn_save_config = st.form_submit_button("Save Policy Settings", use_container_width=True)
            if btn_save_config:
                database.set_setting("reward_tiers_json", json.dumps(new_tiers), "Configured reward discount tiers")
                database.set_setting("max_discount_percent", str(new_cap), "Maximum allowed rent discount percentage")
                st.success("Reward policy rules updated successfully.")
                st.rerun()


def _render_tenant_rewards(user):
    st.caption("Earn real rent discounts every month by keeping your living space tidy, hygienic, and well organized.")

    tenant = database.get_tenant_by_user_id(user["id"])
    if not tenant:
        st.warning("No tenant profile found.")
        st.stop()

    rewards = database.get_tenant_rewards(tenant["id"])

    # Tenant KPI
    total_pts = sum(r.get("reward_points", 0) for r in rewards)
    total_saved = sum(r["discount_amount"] for r in rewards if r["status"] in ("Approved", "Applied"))

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Reward Points", f"{total_pts} pts")
    k2.metric("Total Rent Money Saved", format_currency(total_saved))
    k3.metric("Eligible Discount Tiers", "Up to 10% / month")

    st.html('<div style="height: 1px; background-color: #E3D7CE; margin: 24px 0;"></div>')

    # Reward Structure Infobox
    st.markdown("### Scoring & Discount Policy")
    tiers = get_configured_reward_tiers()
    tier_cols = st.columns(len(tiers))
    for idx, t in enumerate(tiers):
        with tier_cols[idx]:
            st.html(f"""<div style="background-color: #FFFFFF; padding: 16px 14px; border-radius: 10px; text-align: center; border: 1px solid #E3D7CE; border-top: 3px solid #6D3914; box-shadow: 0 1px 2px rgba(53,39,30,0.03);">
                <div style="font-size: 1.35rem; font-weight: 800; color: #6D3914; letter-spacing: -0.02em;">{t['discount_pct']}% OFF</div>
                <div style="margin: 4px 0 2px; font-weight: 700; font-size: 0.9rem; color: #35271E;">{t['min']} – {t['max']} Score</div>
                <div style="color: #8C7465; font-size: 0.8rem; font-weight: 500;">{t.get('label', '')}</div>
            </div>""")

    st.html('<div style="height: 1px; background-color: #E3D7CE; margin: 24px 0;"></div>')

    st.markdown("### Reward & Discount History")
    if not rewards:
        st.info("You have not earned any rewards yet. Submit your room photographs during the monthly inspection to get rewarded.")
    else:
        for rw in rewards:
            with st.expander(
                f"Month: {rw['month_year']} — Discount: {rw['discount_percentage']}% ({format_currency(rw['discount_amount'])}) | Status: {rw['status']}",
                expanded=False
            ):
                st.markdown(f"""
                - **Cleanliness Score:** `{rw['cleanliness_score']} / 100`
                - **Reward Points Earned:** `{rw.get('reward_points', 0)} pts`
                - **Discount Rate:** `{rw['discount_percentage']}%`
                - **Rent Deduction:** `{format_currency(rw['discount_amount'])}`
                - **Approval Status:** `{rw['status']}`
                - **Owner Comments:** {rw.get('owner_comments', 'No comments') or 'No comments'}
                """)


if __name__ == "__main__" or True:
    render_rewards()

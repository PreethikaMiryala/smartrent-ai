"""
SmartRent AI - Property Damage Alerts Module (Owner)
"""
import streamlit as st
from pathlib import Path
from datetime import datetime

import database
from utils.authentication import is_owner
from utils.helpers import format_date, render_status_badge
from config import DAMAGE_CATEGORIES, MAINTENANCE_CATEGORIES


def render_damage_alerts():
    if not is_owner():
        st.error("⛔ Access Denied. Property Owners only.")
        st.stop()

    st.title("🚨 AI Property Damage Alerts")
    st.caption("AI detects potential cracks, dampness, broken fixtures, and wear. Owner human verification is strictly required.")

    alerts = database.get_all_damage_alerts()

    # Metrics summary
    c1, c2, c3, c4 = st.columns(4)
    total_a = len(alerts)
    pending_a = sum(1 for a in alerts if a["status"] == "Pending Review")
    verified_a = sum(1 for a in alerts if a["status"] == "Verified")
    dismissed_a = sum(1 for a in alerts if a["status"] == "Not Damage")

    c1.metric("Total Alerts", total_a)
    c2.metric("Pending Review", pending_a, delta="Requires Verification" if pending_a > 0 else "All Clear", delta_color="inverse")
    c3.metric("Verified Damage", verified_a)
    c4.metric("Dismissed / False Positives", dismissed_a)

    st.markdown("---")

    # Filter Bar
    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        status_filter = st.selectbox("Filter by Status", ["All", "Pending Review", "Verified", "Not Damage", "Maintenance Scheduled"])
    with f_col2:
        cat_filter = st.selectbox("Filter by Damage Category", ["All"] + DAMAGE_CATEGORIES)

    filtered_alerts = alerts
    if status_filter != "All":
        filtered_alerts = [a for a in filtered_alerts if a["status"] == status_filter]
    if cat_filter != "All":
        filtered_alerts = [a for a in filtered_alerts if a["damage_category"] == cat_filter]

    if not filtered_alerts:
        st.success("✅ No property damage alerts match the selected criteria.")
        return

    for alert in filtered_alerts:
        sev_color = "#ef4444" if alert["severity"] == "High" else ("#f59e0b" if alert["severity"] == "Medium" else "#3b82f6")
        
        with st.expander(
            f"🔍 **{alert['room_number']}** ({alert['tenant_name']}) — **{alert['damage_category']}** | "
            f"Severity: {alert['severity']} | Status: **{alert['status']}**",
            expanded=(alert["status"] == "Pending Review")
        ):
            c_img, c_det = st.columns([1, 2])

            with c_img:
                img_path = alert.get("image_ref")
                if img_path and Path(img_path).exists():
                    st.image(img_path, caption=f"Flagged Photograph ({alert['damage_category']})", use_container_width=True)
                else:
                    st.info("📷 Image preview not available or archived on disk.")

            with c_det:
                st.markdown(f"""
                - **Unit:** `{alert['room_number']}` | **Tenant:** `{alert['tenant_name']}`
                - **Damage Category:** `{alert['damage_category']}`
                - **AI Confidence Score:** `{alert['confidence']*100:.1f}%`
                - **Severity Level:** <span style="color: {sev_color}; font-weight: bold;">{alert['severity']}</span>
                - **Date Detected:** {format_date(alert['created_at'])}
                """, unsafe_allow_html=True)

                st.markdown(f"**AI Description & Findings:**\n{alert['description']}")
                
                if alert.get("previous_inspection_comparison"):
                    st.info(f"**Historical Comparison:** {alert['previous_inspection_comparison']}")

                if alert.get("recommended_action"):
                    st.markdown(f"**AI Recommended Action:** {alert['recommended_action']}")

                if alert.get("owner_comments"):
                    st.success(f"**Owner Notes:** {alert['owner_comments']}")

                st.markdown("---")

                # Action Controls
                st.markdown("##### 🛠️ Human Owner Verification & Resolution")
                act_col1, act_col2, act_col3 = st.columns(3)

                with act_col1:
                    with st.popover("✅ Verify as Damage"):
                        st.write("Confirm that this damage is genuine.")
                        v_notes = st.text_input("Owner Comments", placeholder="e.g. Confirmed on physical site inspection", key=f"v_nt_{alert['id']}")
                        if st.button("Confirm Verification", key=f"btn_v_{alert['id']}", type="primary"):
                            database.execute_query(
                                "UPDATE damage_alerts SET status = 'Verified', owner_comments = ? WHERE id = ?;",
                                (v_notes.strip(), alert["id"]),
                                commit=True
                            )
                            st.success("Alert verified as actual damage.")
                            st.rerun()

                with act_col2:
                    with st.popover("❌ Mark as Not Damage"):
                        st.write("Dismiss this alert as a false positive or harmless shadow/lighting.")
                        d_notes = st.text_input("Reason", placeholder="e.g. Normal shadow; wall is intact", key=f"d_nt_{alert['id']}")
                        if st.button("Dismiss Alert", key=f"btn_d_{alert['id']}"):
                            database.execute_query(
                                "UPDATE damage_alerts SET status = 'Not Damage', owner_comments = ? WHERE id = ?;",
                                (d_notes.strip(), alert["id"]),
                                commit=True
                            )
                            st.info("Alert dismissed.")
                            st.rerun()

                with act_col3:
                    with st.popover("🔧 Convert to Maintenance"):
                        st.write("Create a maintenance work order for this damage.")
                        m_title = st.text_input("Ticket Title", value=f"Repair {alert['damage_category']} in {alert['room_number']}", key=f"m_t_{alert['id']}")
                        m_cat = st.selectbox("Category", MAINTENANCE_CATEGORIES, key=f"m_c_{alert['id']}")
                        m_prio = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"], index=1, key=f"m_p_{alert['id']}")
                        m_desc = st.text_area("Work Description", value=alert["description"], key=f"m_d_{alert['id']}")

                        if st.button("Create Maintenance Order", key=f"btn_m_{alert['id']}", type="primary"):
                            # 1. Insert maintenance request
                            database.execute_query("""
                            INSERT INTO maintenance_requests (tenant_id, room_id, category, title, description, priority, status, image_path)
                            VALUES (?, ?, ?, ?, ?, ?, 'Submitted', ?);
                            """, (alert["tenant_id"], alert["room_id"], m_cat, m_title.strip(), m_desc.strip(), m_prio, alert.get("image_ref")), commit=True)
                            
                            # 2. Update damage alert status
                            database.execute_query(
                                "UPDATE damage_alerts SET status = 'Maintenance Scheduled', owner_comments = 'Maintenance work order created' WHERE id = ?;",
                                (alert["id"],),
                                commit=True
                            )
                            st.success("Maintenance ticket generated!")
                            st.rerun()


if __name__ == "__main__" or True:
    render_damage_alerts()

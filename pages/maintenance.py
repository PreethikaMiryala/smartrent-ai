"""
SmartRent AI - Property Maintenance Management Module
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from PIL import Image

import database
from config import (
    MAINTENANCE_CATEGORIES,
    MAINTENANCE_PRIORITIES,
    MAINTENANCE_STATUSES,
    MAINTENANCE_DIR
)
from utils.authentication import is_owner, is_tenant, get_current_user
from utils.helpers import format_date
from utils.image_utils import validate_image, save_image_to_disk


def render_maintenance():
    user = get_current_user()
    if not user:
        st.error("Please log in to access maintenance tickets.")
        st.stop()

    st.title("🛠️ Property Maintenance & Repair Requests")

    if is_owner():
        _render_owner_maintenance(user)
    else:
        _render_tenant_maintenance(user)


def _render_owner_maintenance(user):
    st.caption("Review tenant maintenance requests, dispatch technicians, log progress updates, and mark tickets as completed.")

    all_reqs = database.get_all_maintenance_requests()

    # Metric Bar
    open_reqs = [m for m in all_reqs if m["status"] in ("Submitted", "In Progress")]
    urgent_reqs = [m for m in open_reqs if m["priority"] in ("Urgent", "High")]
    completed_reqs = [m for m in all_reqs if m["status"] == "Completed"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Requests", len(all_reqs))
    c2.metric("Active / In Progress", len(open_reqs), delta="Pending Resolution" if open_reqs else "All Clear")
    c3.metric("Urgent / High Priority", len(urgent_reqs), delta_color="inverse")
    c4.metric("Resolved Tickets", len(completed_reqs))

    st.markdown("---")

    # Filters
    f1, f2 = st.columns([2, 1])
    with f1:
        st_filter = st.selectbox("Filter Status", ["All", "Submitted", "In Progress", "Completed", "Cancelled"])
    with f2:
        cat_filter = st.selectbox("Filter Category", ["All"] + MAINTENANCE_CATEGORIES)

    filtered = all_reqs
    if st_filter != "All":
        filtered = [m for m in filtered if m["status"] == st_filter]
    if cat_filter != "All":
        filtered = [m for m in filtered if m["category"] == cat_filter]

    if not filtered:
        st.info("No maintenance requests match the current filters.")
        return

    for m in filtered:
        prio_color = "#ef4444" if m["priority"] == "Urgent" else ("#f97316" if m["priority"] == "High" else "#3b82f6")
        
        with st.expander(
            f"🔧 **Ticket #{m['id']}** — **{m['room_number']}** ({m['tenant_name']}) | "
            f"**{m['title']}** | Priority: **{m['priority']}** | Status: **{m['status']}**",
            expanded=(m["status"] in ("Submitted", "In Progress"))
        ):
            c_info, c_action = st.columns([2, 1.2])

            with c_info:
                st.markdown(f"""
                - **Category:** `{m['category']}`
                - **Unit:** `{m['room_number']}` | **Tenant:** `{m['tenant_name']}`
                - **Priority:** <span style="color: {prio_color}; font-weight: bold;">{m['priority']}</span>
                - **Reported On:** {format_date(m['created_at'])}
                - **Current Status:** `{m['status']}`
                """, unsafe_allow_html=True)

                st.markdown(f"**Issue Description:**\n{m['description']}")

                if m.get("image_path") and Path(m["image_path"]).exists():
                    st.image(m["image_path"], caption="Tenant Attached Photograph", width=300)

                if m.get("owner_notes"):
                    st.info(f"**Work Log / Progress Notes:**\n{m['owner_notes']}")

                if m.get("resolved_at"):
                    st.success(f"**Resolved On:** {format_date(m['resolved_at'])}")

            with c_action:
                st.markdown("##### Manage Ticket")
                new_status = st.selectbox("Update Status", MAINTENANCE_STATUSES, 
                                          index=MAINTENANCE_STATUSES.index(m["status"]), 
                                          key=f"m_st_{m['id']}")
                notes_input = st.text_area("Technician / Progress Notes", value=m.get("owner_notes", "") or "", key=f"m_nt_{m['id']}")

                if st.button("Save Ticket Update", key=f"btn_up_{m['id']}", type="primary", use_container_width=True):
                    resolved_time = datetime.now().isoformat() if new_status == "Completed" and not m.get("resolved_at") else m.get("resolved_at")
                    database.execute_query("""
                    UPDATE maintenance_requests 
                    SET status = ?, owner_notes = ?, resolved_at = ?
                    WHERE id = ?;
                    """, (new_status, notes_input.strip(), resolved_time, m["id"]), commit=True)
                    st.success("Ticket updated!")
                    st.rerun()


def _render_tenant_maintenance(user):
    st.caption("Report property issues, plumbing problems, electrical faults, or required repairs for prompt resolution.")

    tenant = database.get_tenant_by_user_id(user["id"])
    if not tenant:
        st.warning("No tenant assignment found.")
        st.stop()

    tenant_id = tenant["id"]
    room_id = tenant["room_id"]
    room_num = tenant["room_number"]

    tab_submit, tab_my_tickets = st.tabs(["➕ Submit New Request", "📋 My Active & Past Tickets"])

    with tab_submit:
        st.subheader("Report a Problem in Your Room")
        with st.form("form_submit_maint", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                category = st.selectbox("Problem Category*", MAINTENANCE_CATEGORIES)
                title = st.text_input("Short Summary*", placeholder="e.g. Bathroom sink water tap is dripping")
            with f_col2:
                priority = st.selectbox("Urgency Level*", MAINTENANCE_PRIORITIES, index=1)
                maint_file = st.file_uploader("Attach Photograph (Optional)", type=["jpg", "jpeg", "png"])

            description = st.text_area("Detailed Description*", placeholder="Explain the issue, when it started, and where in the room it is located...")

            btn_submit = st.form_submit_button("🚀 Submit Maintenance Request", use_container_width=True, type="primary")

            if btn_submit:
                if not title.strip() or not description.strip():
                    st.error("Please provide both a summary title and detailed description.")
                else:
                    saved_path = None
                    if maint_file:
                        is_valid, msg = validate_image(maint_file)
                        if is_valid:
                            saved_path, _, _ = save_image_to_disk(
                                file_bytes=maint_file.getvalue(),
                                original_name=maint_file.name,
                                target_dir=MAINTENANCE_DIR,
                                prefix=f"maint_{tenant_id}"
                            )
                        else:
                            st.warning(f"Attached image ignored: {msg}")

                    database.execute_query("""
                    INSERT INTO maintenance_requests (tenant_id, room_id, category, title, description, priority, status, image_path)
                    VALUES (?, ?, ?, ?, ?, ?, 'Submitted', ?);
                    """, (tenant_id, room_id, category, title.strip(), description.strip(), priority, saved_path), commit=True)

                    st.success("🎉 Maintenance ticket created! The property manager will review and assign a technician.")
                    st.rerun()

    with tab_my_tickets:
        st.subheader("Your Maintenance History")
        my_requests = database.get_tenant_maintenance_requests(tenant_id)

        if not my_requests:
            st.info("You haven't submitted any maintenance requests yet.")
        else:
            for m in my_requests:
                with st.expander(
                    f"🔧 **#{m['id']}: {m['title']}** | Priority: **{m['priority']}** | Status: **{m['status']}**",
                    expanded=(m["status"] in ("Submitted", "In Progress"))
                ):
                    st.markdown(f"""
                    - **Category:** `{m['category']}`
                    - **Submitted On:** {format_date(m['created_at'])}
                    - **Status:** `{m['status']}`
                    """)
                    st.markdown(f"**Your Description:**\n{m['description']}")

                    if m.get("image_path") and Path(m["image_path"]).exists():
                        st.image(m["image_path"], caption="Attached Photograph", width=260)

                    if m.get("owner_notes"):
                        st.info(f"**Management Response / Status Update:**\n{m['owner_notes']}")

                    if m.get("resolved_at"):
                        st.success(f"**Resolved On:** {format_date(m['resolved_at'])}")


if __name__ == "__main__" or True:
    render_maintenance()

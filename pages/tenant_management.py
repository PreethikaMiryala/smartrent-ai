"""
SmartRent AI - Tenant Registration and Management Module (Owner)
"""
import streamlit as st
import pandas as pd
from datetime import date
import database
from utils.authentication import is_owner
from utils.helpers import format_currency, format_date


def render_tenant_management():
    if not is_owner():
        st.error("⛔ Access Denied. Property Owners only.")
        st.stop()

    st.title("👥 Tenant Management")
    st.caption("Register new tenants, assign rooms, manage contact information, and review tenant records.")

    tenants = database.get_all_tenants()
    rooms = database.get_all_rooms()

    # Summary Metrics
    c1, c2, c3 = st.columns(3)
    active_tenants = [t for t in tenants if t["status"] == "Active"]
    vacant_rooms = [r for r in rooms if r["status"] == "Vacant"]

    c1.metric("Total Tenants", len(tenants))
    c2.metric("Active Leases", len(active_tenants))
    c3.metric("Vacant Units Available", len(vacant_rooms))

    st.markdown("---")

    tab_directory, tab_register = st.tabs(["📋 Tenant Directory", "➕ Register New Tenant"])

    with tab_register:
        st.subheader("New Tenant Onboarding")
        st.caption("Create login credentials and allocate a rental unit.")

        with st.form("form_register_tenant", clear_on_submit=True):
            st.markdown("##### 1. Personal & Contact Information")
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                t_full_name = st.text_input("Full Name*", placeholder="e.g. Ramesh Chandra")
                t_email = st.text_input("Email Address", placeholder="e.g. ramesh@example.com")
            with p_col2:
                t_phone = st.text_input("Phone Number*", placeholder="e.g. +91 98765 12345")
                t_emergency = st.text_input("Emergency Contact", placeholder="e.g. +91 98111 22334 (Brother)")

            st.markdown("##### 2. Account Credentials for Tenant Portal")
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                t_username = st.text_input("Username*", placeholder="e.g. ramesh_c")
            with c_col2:
                t_password = st.text_input("Password*", type="password", placeholder="Minimum 6 characters")

            st.markdown("##### 3. Room Assignment & Lease Terms")
            r_col1, r_col2 = st.columns(2)
            
            # Filter rooms available or all
            room_options = {f"{r['room_number']} (Rent: {format_currency(r['monthly_rent'])}) - {r['status']}": r["id"] for r in rooms}
            room_options_with_none = {"None (Unassigned)": None, **room_options}

            with r_col1:
                selected_room_label = st.selectbox("Assign Room Unit", options=list(room_options_with_none.keys()))
                assigned_room_id = room_options_with_none[selected_room_label]
            with r_col2:
                t_join_date = st.date_input("Lease Start Date", value=date.today())

            t_notes = st.text_area("Administrative Notes", placeholder="e.g. Security deposit ₹15,000 received via cheque.")

            btn_submit = st.form_submit_button("🚀 Complete Registration", use_container_width=True)

            if btn_submit:
                if not t_full_name.strip() or not t_username.strip() or not t_password.strip():
                    st.error("Please fill in all required fields (Full Name, Username, and Password).")
                elif len(t_password.strip()) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    # Check username uniqueness
                    existing_user = database.get_user_by_username(t_username.strip().lower())
                    if existing_user:
                        st.error(f"Username '{t_username}' is already taken. Please choose another username.")
                    else:
                        # 1. Create User
                        user_id = database.create_user(
                            username=t_username.strip().lower(),
                            plain_password=t_password.strip(),
                            role="tenant",
                            full_name=t_full_name.strip(),
                            email=t_email.strip(),
                            phone=t_phone.strip()
                        )
                        # 2. Create Tenant Profile
                        database.create_tenant(
                            user_id=user_id,
                            room_id=assigned_room_id,
                            joining_date=t_join_date.isoformat(),
                            emergency_contact=t_emergency.strip(),
                            notes=t_notes.strip()
                        )
                        st.success(f"🎉 Tenant '{t_full_name}' successfully registered and assigned to unit!")
                        st.rerun()

    with tab_directory:
        st.subheader("Registered Tenant Records")

        # Search bar
        s_col1, s_col2 = st.columns([2, 1])
        with s_col1:
            t_search = st.text_input("🔍 Search tenants by name, username, room, or phone", "")
        with s_col2:
            t_status_filter = st.selectbox("Filter Status", ["All", "Active", "Inactive"])

        filtered_tenants = tenants
        if t_status_filter != "All":
            filtered_tenants = [t for t in filtered_tenants if t["status"] == t_status_filter]
        if t_search.strip():
            ts = t_search.strip().lower()
            filtered_tenants = [
                t for t in filtered_tenants
                if ts in t["full_name"].lower() 
                or ts in t["username"].lower() 
                or (t.get("room_number") and ts in t["room_number"].lower())
                or (t.get("phone") and ts in t["phone"].lower())
            ]

        if not filtered_tenants:
            st.info("No tenants found matching the search criteria.")
        else:
            for t in filtered_tenants:
                room_badge = f"Room {t['room_number']}" if t.get('room_number') else "Unassigned"
                with st.expander(f"👤 **{t['full_name']}** — `{room_badge}` | Status: **{t['status']}**", expanded=False):
                    c_det1, c_det2 = st.columns([2, 1])
                    with c_det1:
                        st.markdown(f"""
                        - **Username:** `{t['username']}`
                        - **Phone:** `{t.get('phone', 'N/A')}`
                        - **Email:** `{t.get('email', 'N/A')}`
                        - **Assigned Unit:** `{room_badge}` (Base Rent: {format_currency(t.get('monthly_rent'))})
                        - **Joining Date:** {format_date(t['joining_date'])}
                        - **Emergency Contact:** {t.get('emergency_contact', 'N/A') or 'None'}
                        - **Notes:** {t.get('notes', 'None') or 'None'}
                        """)

                    with c_det2:
                        st.markdown("**Manage Tenant**")
                        with st.popover(f"✏️ Edit Profile"):
                            st.write(f"Edit details for **{t['full_name']}**")
                            
                            # Build room selector options
                            r_choices = {"None (Unassigned)": None}
                            for rm in rooms:
                                r_choices[f"{rm['room_number']} ({rm['status']})"] = rm["id"]

                            curr_rm_label = next((k for k, v in r_choices.items() if v == t["room_id"]), "None (Unassigned)")
                            sel_rm_label = st.selectbox("Reassign Room", list(r_choices.keys()), 
                                                        index=list(r_choices.keys()).index(curr_rm_label),
                                                        key=f"edit_t_rm_{t['id']}")
                            
                            sel_st = st.selectbox("Lease Status", ["Active", "Inactive"], 
                                                  index=0 if t["status"] == "Active" else 1,
                                                  key=f"edit_t_st_{t['id']}")
                            
                            sel_emer = st.text_input("Emergency Contact", value=t.get("emergency_contact", "") or "", key=f"edit_t_em_{t['id']}")
                            sel_notes = st.text_area("Notes", value=t.get("notes", "") or "", key=f"edit_t_nt_{t['id']}")

                            if st.button("Save Changes", key=f"btn_save_t_{t['id']}", use_container_width=True):
                                new_rm_id = r_choices[sel_rm_label]
                                database.update_tenant(t["id"], new_rm_id, sel_st, sel_emer.strip(), sel_notes.strip())
                                st.success("Tenant record updated.")
                                st.rerun()


if __name__ == "__main__" or True:
    render_tenant_management()

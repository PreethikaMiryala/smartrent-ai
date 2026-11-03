"""
SmartRent AI - Room Management Module (Owner)
"""
import streamlit as st
import pandas as pd
import database
from utils.authentication import is_owner
from utils.helpers import format_currency, format_date, render_status_badge


def render_room_management():
    if not is_owner():
        st.error("⛔ Access Denied. Property Owners only.")
        st.stop()

    st.title("🚪 Room Management")
    st.caption("Manage rooms, rental pricing, tenant occupancy status, and room maintenance states.")

    rooms = database.get_all_rooms()

    # Metrics Summary Bar
    c1, c2, c3, c4 = st.columns(4)
    total_r = len(rooms)
    occ_r = sum(1 for r in rooms if r["status"] == "Occupied")
    vac_r = sum(1 for r in rooms if r["status"] == "Vacant")
    maint_r = sum(1 for r in rooms if r["status"] == "Maintenance")

    c1.metric("Total Rooms", total_r)
    c2.metric("Occupied", occ_r)
    c3.metric("Vacant", vac_r)
    c4.metric("Maintenance", maint_r)

    st.markdown("---")

    # Tabs: View Rooms, Add Room, Edit Room
    tab_list, tab_add = st.tabs(["📋 Room Directory", "➕ Add New Room"])

    with tab_add:
        st.subheader("Add a New Rental Unit")
        with st.form("form_add_room", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                new_room_number = st.text_input("Room Number / Name*", placeholder="e.g. Room 301, Unit B4")
                new_rent = st.number_input("Monthly Base Rent (₹)*", min_value=1000.0, max_value=500000.0, value=8000.0, step=500.0)
            with f_col2:
                new_status = st.selectbox("Initial Status", options=["Vacant", "Occupied", "Maintenance"], index=0)
                new_desc = st.text_area("Room Description", placeholder="e.g. Spacious 1BHK with private attached balcony and tiled flooring...")

            submit_add = st.form_submit_button("💾 Create Room", use_container_width=True)

            if submit_add:
                if not new_room_number.strip():
                    st.error("Please enter a valid room number.")
                else:
                    # Check duplicate room number
                    existing = any(r["room_number"].strip().lower() == new_room_number.strip().lower() for r in rooms)
                    if existing:
                        st.error(f"Room '{new_room_number}' already exists. Please choose a unique room number.")
                    else:
                        database.create_room(
                            room_number=new_room_number.strip(),
                            monthly_rent=float(new_rent),
                            description=new_desc.strip(),
                            status=new_status
                        )
                        st.success(f"🎉 Room '{new_room_number}' created successfully!")
                        st.rerun()

    with tab_list:
        st.subheader("All Property Units")
        
        # Search & Filter
        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            search_query = st.text_input("🔍 Search by room number or tenant name", "")
        with col_s2:
            status_filter = st.selectbox("Filter by Status", ["All", "Vacant", "Occupied", "Maintenance"])

        filtered_rooms = rooms
        if status_filter != "All":
            filtered_rooms = [r for r in filtered_rooms if r["status"] == status_filter]
        if search_query.strip():
            sq = search_query.strip().lower()
            filtered_rooms = [
                r for r in filtered_rooms 
                if sq in r["room_number"].lower() or (r.get("tenant_name") and sq in r["tenant_name"].lower())
            ]

        if not filtered_rooms:
            st.info("No rooms matching the criteria.")
        else:
            for r in filtered_rooms:
                with st.expander(f"🚪 **{r['room_number']}** — Rent: {format_currency(r['monthly_rent'])} | Status: {r['status']}", expanded=False):
                    c_info, c_action = st.columns([2, 1])
                    
                    with c_info:
                        st.markdown(f"**Description:** {r.get('description', 'No description provided')}")
                        if r.get("tenant_name"):
                            st.markdown(f"**Assigned Tenant:** `{r['tenant_name']}` (Phone: {r.get('tenant_phone', 'N/A')})")
                        else:
                            st.markdown("**Assigned Tenant:** *None (Available for leasing)*")
                        st.caption(f"Created: {format_date(r['created_at'])}")

                    with c_action:
                        st.markdown("**Actions**")
                        # Edit form
                        with st.popover(f"✏️ Edit {r['room_number']}"):
                            st.write(f"Edit details for **{r['room_number']}**")
                            e_num = st.text_input("Room Number", value=r["room_number"], key=f"e_num_{r['id']}")
                            e_rent = st.number_input("Monthly Rent (₹)", value=float(r["monthly_rent"]), step=500.0, key=f"e_rent_{r['id']}")
                            e_status = st.selectbox("Status", ["Vacant", "Occupied", "Maintenance"], 
                                                   index=["Vacant", "Occupied", "Maintenance"].index(r["status"]), 
                                                   key=f"e_st_{r['id']}")
                            e_desc = st.text_area("Description", value=r.get("description", "") or "", key=f"e_desc_{r['id']}")

                            if st.button("Update Room Details", key=f"btn_update_{r['id']}", use_container_width=True):
                                database.update_room(r["id"], e_num.strip(), float(e_rent), e_desc.strip(), e_status)
                                st.success("Room updated!")
                                st.rerun()

                        # Delete button
                        if r.get("tenant_name"):
                            st.button(
                                "🗑️ Delete",
                                key=f"del_disabled_{r['id']}",
                                disabled=True,
                                help="Cannot delete room while an active tenant is assigned. Reassign or vacate first."
                            )
                        else:
                            if st.button("🗑️ Delete Room", key=f"del_{r['id']}", type="secondary"):
                                database.delete_room(r["id"])
                                st.success(f"Room {r['room_number']} deleted.")
                                st.rerun()


if __name__ == "__main__" or True:
    render_room_management()

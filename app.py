"""
SmartRent AI - Intelligent Rental & Property Management System
Main Application Entry Point and Role-Based Router
"""
import streamlit as st
from datetime import datetime

# Page configuration MUST be first Streamlit call
st.set_page_config(
    page_title="SmartRent AI",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="expanded"
)

import database
from utils.authentication import (
    init_session_state,
    login_user,
    logout_user,
    get_current_user,
    is_authenticated,
    is_owner,
    is_tenant,
    verify_password
)
from services.groq_service import get_active_groq_api_key

# 1. Initialize Database on startup
database.init_db()

# 2. Initialize Session State
init_session_state()

# 3. Modern Custom CSS Styling
st.markdown("""
<style>
    /* Main body background & typography */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Metric card styling */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    [data-testid="stMetricValue"] {
        font-weight: 700;
        font-size: 1.8rem !important;
    }

    /* Expander modern borders */
    [data-testid="stExpander"] {
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 10px !important;
        margin-bottom: 10px;
        background-color: rgba(255, 255, 255, 0.02);
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 8px 16px;
        font-weight: 600;
    }

    /* Status badge pill */
    .role-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .role-owner {
        background-color: #dbeafe;
        color: #1e40af;
    }
    .role-tenant {
        background-color: #d1fae5;
        color: #065f46;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# Authentication Flow
# =========================================================================

def render_login_screen():
    col1, col2, col3 = st.columns([1, 1.8, 1])

    with col2:
        st.write("") # spacing
        st.write("")
        st.markdown("""
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="font-size: 2.5rem; margin-bottom: 4px;">🏡 SmartRent AI</h1>
            <p style="color: #64748b; font-size: 1.05rem;">Intelligent Rental, AI Inspection & Property Management System</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader("Sign In to Your Account")
            
            with st.form("login_form"):
                username_input = st.text_input("Username", placeholder="Enter your username")
                password_input = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_button = st.form_submit_button("Sign In ➔", type="primary", use_container_width=True)

                if submit_button:
                    if not username_input.strip() or not password_input.strip():
                        st.error("Please enter both username and password.")
                    else:
                        user = database.get_user_by_username(username_input.strip().lower())
                        if user and verify_password(password_input.strip(), user["password_hash"], user["salt"]):
                            login_user(user)
                            st.rerun()
                        else:
                            st.error("Invalid username or password. Please try again.")

            st.caption("🔒 Secure login with PBKDF2 HMAC SHA-256 authentication.")


# =========================================================================
# Main Router
# =========================================================================

if not is_authenticated():
    render_login_screen()
else:
    current_user = get_current_user()
    role = current_user.get("role", "tenant")

    # Sidebar: User profile badge & API connection badge
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 12px 14px; border-radius: 10px; background-color: rgba(148, 163, 184, 0.1); margin-bottom: 14px;">
            <div style="font-weight: 700; font-size: 1.05rem;">{current_user['full_name']}</div>
            <div style="margin-top: 4px;">
                <span class="role-badge role-{role}">{role.upper()}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Groq API status
        active_key = get_active_groq_api_key()
        if active_key:
            st.caption("🟢 **Groq AI Active** (`qwen/qwen3.8-27b`)")
        else:
            st.caption("🔴 **Groq AI Key Not Set** (Go to Settings)")

    # Define Navigation Structure using Streamlit 1.30+ Navigation API
    if is_owner():
        nav_pages = {
            "Overview": [
                st.Page("pages/owner_dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
                st.Page("pages/reports.py", title="Reports & Analytics", icon=":material/analytics:"),
            ],
            "Property & Tenants": [
                st.Page("pages/room_management.py", title="Room Units", icon=":material/meeting_room:"),
                st.Page("pages/tenant_management.py", title="Tenant Directory", icon=":material/group:"),
                st.Page("pages/rent_payments.py", title="Rent & Invoices", icon=":material/payments:"),
            ],
            "AI Operations": [
                st.Page("pages/ai_inspection.py", title="AI Inspections", icon=":material/auto_awesome:"),
                st.Page("pages/damage_alerts.py", title="Damage Alerts", icon=":material/warning:"),
                st.Page("pages/rewards.py", title="Rewards & Discounts", icon=":material/military_tech:"),
                st.Page("pages/maintenance.py", title="Maintenance Tickets", icon=":material/build:"),
                st.Page("pages/ai_assistant.py", title="SmartRent Assistant", icon=":material/chat:"),
            ],
            "Configuration": [
                st.Page("pages/settings.py", title="API & System Settings", icon=":material/settings:"),
            ]
        }
    else:
        # Tenant Navigation
        tenant_rec = database.get_tenant_by_user_id(current_user["id"])
        room_info = f"Room {tenant_rec['room_number']}" if tenant_rec and tenant_rec.get("room_number") else "Tenant"

        nav_pages = {
            "My Living Space": [
                st.Page("pages/tenant_dashboard.py", title=f"My Dashboard ({room_info})", icon=":material/home:", default=True),
                st.Page("pages/ai_inspection.py", title="Upload Room Photos", icon=":material/photo_camera:"),
                st.Page("pages/rewards.py", title="My Rewards & Discounts", icon=":material/military_tech:"),
            ],
            "Billing & Maintenance": [
                st.Page("pages/rent_payments.py", title="Rent & Payments", icon=":material/receipt_long:"),
                st.Page("pages/maintenance.py", title="Maintenance Requests", icon=":material/handyman:"),
                st.Page("pages/ai_assistant.py", title="SmartRent AI Assistant", icon=":material/support_agent:"),
            ]
        }

    # Sidebar Logout Button
    with st.sidebar:
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True, type="secondary"):
            logout_user()

    # Initialize and execute navigation
    selected_page = st.navigation(nav_pages)
    selected_page.run()

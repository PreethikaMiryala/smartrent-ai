"""
SmartRent AI - Intelligent Rental & Property Management System
Tenant Portal Application
"""
import streamlit as st
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SmartRent AI - Tenant Portal",
    page_icon=":material/home:",
    layout="wide",
    initial_sidebar_state="expanded"
)

import database
from utils.authentication import (
    init_session_state,
    login_user,
    get_current_user,
    is_authenticated,
    is_tenant
)
from services.groq_service import get_active_groq_api_key

# Initialize Database & Session
database.init_db()
init_session_state()

# Premium Warm Palette & Responsive Layout Styling (Mahogany, Almond, Cafe, Caramel, Espresso)
st.html("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    /* Global Typography & Palette */
    html, body, .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #35271E;
        background-color: #FBF9F7;
        letter-spacing: -0.01em;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        color: #35271E !important;
        letter-spacing: -0.02em !important;
    }

    p, span, div, label {
        color: #35271E;
    }

    /* -------------------------------------------------------------
       CRITICAL: Protect Material Icons so they never render as plain text
       (e.g. keyboard_double_arrow, dashboard, photo_camera)
       ------------------------------------------------------------- */
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    .material-symbols-outlined,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stSidebarCollapseButton"] button span,
    [data-testid="stSidebarNav"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"],
    [data-testid="stPageLink-Nav"] [data-testid="stIconMaterial"],
    i.material-icons,
    .material-icons {
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important;
        font-weight: normal !important;
        font-style: normal !important;
        font-size: 1.25rem !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-block !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-feature-settings: 'liga' !important;
        -webkit-font-smoothing: antialiased !important;
    }

    /* -------------------------------------------------------------
       Sidebar Layout & Responsive Spacing
       ------------------------------------------------------------- */
    [data-testid="stSidebar"] {
        background-color: #F3EFEA !important;
        border-right: 1px solid #E3D7CE !important;
        min-width: 285px !important;
        max-width: 325px !important;
    }

    [data-testid="stSidebarUserContent"] {
        padding: 1.25rem 1rem !important;
    }

    /* Navigation Item Spacing & Alignment */
    [data-testid="stSidebarNav"] {
        padding-top: 8px !important;
    }

    [data-testid="stSidebarNavItems"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 4px !important;
    }

    [data-testid="stSidebarNavItems"] li {
        margin-bottom: 3px !important;
    }

    [data-testid="stSidebarNavLink"] {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        padding: 9px 14px !important;
        border-radius: 8px !important;
        color: #35271E !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        transition: all 0.15s ease-in-out !important;
        text-decoration: none !important;
    }

    [data-testid="stSidebarNavLink"]:hover {
        background-color: rgba(184, 149, 127, 0.22) !important;
        color: #4C2B08 !important;
    }

    /* Active Nav Link: Cafe (#6D3914) with crisp white text */
    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background-color: #6D3914 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px rgba(76, 43, 8, 0.2) !important;
    }

    [data-testid="stSidebarNavLink"][aria-current="page"] span,
    [data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {
        color: #FFFFFF !important;
    }

    [data-testid="stSidebarNav"] h2,
    [data-testid="stSidebarNav"] [data-testid="stSidebarNavSectionHeader"] {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        color: #8C7465 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        margin-top: 14px !important;
        margin-bottom: 6px !important;
        padding-left: 8px !important;
    }

    /* -------------------------------------------------------------
       Metric Cards Styling (Warm Palette)
       ------------------------------------------------------------- */
    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E3D7CE !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px rgba(53, 39, 30, 0.04), 0 1px 2px rgba(53, 39, 30, 0.02) !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stMetric"]:hover {
        border-color: #AB7843 !important;
        box-shadow: 0 4px 8px -1px rgba(76, 43, 8, 0.08) !important;
    }

    [data-testid="stMetricValue"] {
        font-weight: 800 !important;
        font-size: 1.75rem !important;
        color: #35271E !important;
        letter-spacing: -0.02em !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        font-weight: 700 !important;
        color: #8C7465 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    /* -------------------------------------------------------------
       Expander & Container Styling
       ------------------------------------------------------------- */
    [data-testid="stExpander"] {
        border: 1px solid #E3D7CE !important;
        border-radius: 12px !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 1px 2px rgba(53, 39, 30, 0.03) !important;
        margin-bottom: 12px !important;
    }

    [data-testid="stExpander"] summary {
        color: #35271E !important;
        font-weight: 600 !important;
    }

    /* -------------------------------------------------------------
       Tabs Styling
       ------------------------------------------------------------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px !important;
        border-bottom: 2px solid #E3D7CE !important;
        padding-bottom: 2px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px !important;
        padding: 10px 18px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        color: #8C7465 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #6D3914 !important;
        background-color: rgba(184, 149, 127, 0.12) !important;
    }
    .stTabs [aria-selected="true"] {
        color: #6D3914 !important;
        border-bottom: 3px solid #6D3914 !important;
    }

    /* -------------------------------------------------------------
       Buttons: Cafe (#6D3914) & Espresso (#4C2B08)
       ------------------------------------------------------------- */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background-color: #6D3914 !important;
        color: #FFFFFF !important;
        border: 1px solid #4C2B08 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        padding: 8px 20px !important;
        box-shadow: 0 1px 2px rgba(53, 39, 30, 0.12) !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background-color: #4C2B08 !important;
        border-color: #35271E !important;
        box-shadow: 0 2px 5px rgba(53, 39, 30, 0.2) !important;
    }

    .stButton > button[kind="secondary"],
    .stFormSubmitButton > button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        background-color: #FFFFFF !important;
        color: #4C2B08 !important;
        border: 1px solid #B8957F !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button[kind="secondary"]:hover,
    .stFormSubmitButton > button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover {
        background-color: rgba(184, 149, 127, 0.15) !important;
        border-color: #AB7843 !important;
        color: #35271E !important;
    }

    /* Form Controls */
    input, textarea, [data-baseweb="select"] > div {
        border-color: #DDCFC6 !important;
        border-radius: 8px !important;
        color: #35271E !important;
    }
    input:focus, textarea:focus, [data-baseweb="select"]:focus-within > div {
        border-color: #AB7843 !important;
        box-shadow: 0 0 0 1px #AB7843 !important;
    }

    /* Popover button */
    [data-testid="stPopover"] > button {
        background-color: #FFFFFF !important;
        color: #4C2B08 !important;
        border: 1px solid #B8957F !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    [data-testid="stPopover"] > button:hover {
        border-color: #AB7843 !important;
        background-color: rgba(184, 149, 127, 0.15) !important;
    }

    /* Custom Role Badge */
    .role-badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background-color: rgba(171, 120, 67, 0.15);
        color: #4C2B08;
        border: 1px solid #B8957F;
    }
</style>
""")


# =========================================================================
# Automatic Tenant Profile Initialization (Default: Shiva Guptha)
# =========================================================================

if "user" not in st.session_state or st.session_state.user is None or st.session_state.user.get("role") != "tenant":
    default_tenant_user = database.get_user_by_username("shiva_guptha")
    if default_tenant_user:
        st.session_state.authenticated = True
        st.session_state.user = default_tenant_user

current_user = get_current_user()

# =========================================================================
# Sidebar: Tenant Overview & Quick Profile Switcher
# =========================================================================

with st.sidebar:
    st.html("""<div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #E3D7CE;">
        <div style="font-size: 1.25rem; font-weight: 800; color: #35271E; letter-spacing: -0.02em;">SmartRent AI</div>
        <div style="font-size: 0.78rem; color: #8C7465; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Tenant Portal</div>
    </div>""")

    # Tenant Profile Selector (Switch between Shiva, Preethika, Bunny)
    all_tenants = database.get_all_tenants()
    if all_tenants:
        tenant_options = {
            f"{t['full_name']} (Room {t.get('room_number', 'N/A')})": t['username']
            for t in all_tenants
        }
        current_username = current_user["username"] if current_user else "shiva_guptha"
        current_label = next((k for k, v in tenant_options.items() if v == current_username), list(tenant_options.keys())[0])

        selected_label = st.selectbox(
            "Active Tenant Account",
            options=list(tenant_options.keys()),
            index=list(tenant_options.keys()).index(current_label),
            help="Select tenant to view individual room data and inspection history"
        )

        selected_username = tenant_options[selected_label]
        if current_user is None or current_user["username"] != selected_username:
            new_user = database.get_user_by_username(selected_username)
            if new_user:
                st.session_state.authenticated = True
                st.session_state.user = new_user
                st.session_state.messages = []
                st.rerun()

    # User Profile Information Card
    tenant_rec = database.get_tenant_by_user_id(current_user["id"])
    room_info = f"Room {tenant_rec['room_number']}" if tenant_rec and tenant_rec.get("room_number") else "Tenant"

    profile_card_html = f"""<div style="padding: 12px 14px; border-radius: 10px; background-color: #FFFFFF; border: 1px solid #DDCFC6; border-left: 4px solid #AB7843; margin: 12px 0; box-shadow: 0 1px 2px rgba(53,39,30,0.04);">
        <div style="font-weight: 700; font-size: 0.95rem; color: #35271E;">{current_user['full_name']}</div>
        <div style="font-size: 0.82rem; color: #6D3914; margin-top: 2px;">Assigned Unit: <strong style="color: #4C2B08;">{room_info}</strong></div>
        <div style="margin-top: 8px;">
            <span class="role-badge">Active Resident</span>
        </div>
    </div>"""
    st.html(profile_card_html)

    # Groq AI Status
    active_key = get_active_groq_api_key()
    if active_key:
        st.html("""<div style="font-size: 0.78rem; color: #2E7D32; font-weight: 600; margin-top: 8px; display: flex; align-items: center; gap: 6px;">
            <span style="height: 7px; width: 7px; border-radius: 50%; background-color: #2E7D32; display: inline-block;"></span>
            AI Engine Active (qwen/qwen3.8-27b)
        </div>""")
    else:
        st.html("""<div style="font-size: 0.78rem; color: #AB7843; font-weight: 600; margin-top: 8px; display: flex; align-items: center; gap: 6px;">
            <span style="height: 7px; width: 7px; border-radius: 50%; background-color: #AB7843; display: inline-block;"></span>
            AI Key Not Configured
        </div>""")


# =========================================================================
# Navigation Router - Clean Minimalist Material Icons & Labels
# =========================================================================

nav_pages = {
    "Living Space": [
        st.Page("pages/tenant_dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
        st.Page("pages/ai_inspection.py", title="Room Inspection", icon=":material/photo_camera:"),
        st.Page("pages/rewards.py", title="Rewards & Discounts", icon=":material/loyalty:"),
    ],
    "Account & Services": [
        st.Page("pages/rent_payments.py", title="Rent & Invoices", icon=":material/receipt_long:"),
        st.Page("pages/maintenance.py", title="Maintenance Requests", icon=":material/build:"),
        st.Page("pages/ai_assistant.py", title="SmartRent Assistant", icon=":material/chat:"),
    ]
}

selected_page = st.navigation(nav_pages)
selected_page.run()

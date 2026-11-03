"""
SmartRent AI - System & Groq API Settings Module (Owner Only)
"""
import streamlit as st
import os

import database
from config import DEFAULT_GROQ_MODEL
from services.groq_service import (
    get_active_groq_api_key,
    test_groq_connection
)
from utils.authentication import is_owner


def render_settings():
    if not is_owner():
        st.error("⛔ Access Denied. Settings are restricted to Property Owners.")
        st.stop()

    st.title("⚙️ System & AI Settings")
    st.caption("Configure Groq AI credentials, property rules, and application preferences.")

    tab_api, tab_system, tab_about = st.tabs(["🔑 Groq API Configuration", "🛠️ Property Preferences", "ℹ️ System Info"])

    with tab_api:
        st.subheader("Groq AI API Configuration")
        st.markdown("""
        SmartRent AI connects directly to **Groq Cloud** using model **`qwen/qwen3.8-27b`** for:
        - Multimodal Room Cleanliness Inspection (Pillow + Vision API)
        - Potential Property Damage Detection & Comparisons
        - Real-Time Natural Language Chatbot Assistant
        """)

        current_key = get_active_groq_api_key()
        has_key = bool(current_key)

        # Connection Status Indicator
        if has_key:
            masked = current_key[:7] + "•" * 24 + current_key[-4:] if len(current_key) > 12 else "••••••••••••"
            st.success(f"🟢 **Status: Connected** | Active Key: `{masked}`")
        else:
            st.error("🔴 **Status: Disconnected** | No Groq API Key is currently active.")

        st.markdown("---")

        # API Key Configuration Form
        st.markdown("##### Update API Key")
        entered_key = st.text_input(
            "Groq API Key",
            value="",
            type="password",
            placeholder="gsk_...",
            help="Enter your Groq Cloud API key. Keys are held securely in memory session state."
        )

        btn_col1, btn_col2, btn_col3 = st.columns(3)

        with btn_col1:
            if st.button("🔌 Connect & Save Key", type="primary", use_container_width=True):
                if not entered_key.strip():
                    st.error("Please enter a valid API key string.")
                else:
                    st.session_state.groq_api_key = entered_key.strip()
                    st.success("API Key saved in session state!")
                    st.rerun()

        with btn_col2:
            key_to_test = entered_key.strip() if entered_key.strip() else current_key
            if st.button("🧪 Test Connection", use_container_width=True, disabled=not key_to_test):
                with st.spinner(f"Testing Groq API connection with model '{DEFAULT_GROQ_MODEL}'..."):
                    ok, msg = test_groq_connection(key_to_test)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")

        with btn_col3:
            if st.button("🚫 Disconnect Key", use_container_width=True, disabled=not has_key):
                st.session_state.groq_api_key = ""
                st.warning("Groq API key disconnected from current session.")
                st.rerun()

        st.info("💡 **Security Notice:** In adherence to security best practices, API keys are kept in Streamlit session state and are never written to SQLite, database logs, or shared with tenant accounts.")

    with tab_system:
        st.subheader("Application & Property Defaults")
        curr_retention = database.get_setting("photo_retention_months", "12")
        auto_app = database.get_setting("auto_approve_rewards", "false")

        with st.form("form_property_settings"):
            new_retention = st.selectbox(
                "Inspection Photograph Retention Period",
                options=["3 months", "6 months", "12 months", "24 months", "Indefinite"],
                index=2
            )
            new_auto = st.checkbox("Automatically apply AI rewards to rent invoices without owner review", value=(auto_app == "true"))

            btn_save_prop = st.form_submit_button("Save Preferences", type="primary")
            if btn_save_prop:
                database.set_setting("photo_retention_months", new_retention.split()[0], "Photo retention period")
                database.set_setting("auto_approve_rewards", "true" if new_auto else "false", "Auto approve rewards")
                st.success("Preferences updated!")
                st.rerun()

    with tab_about:
        st.subheader("SmartRent AI Platform Information")
        st.markdown(f"""
        - **Application:** SmartRent AI – Intelligent Rental & Property Management System
        - **AI Provider:** Groq Cloud
        - **Active AI Model:** `{DEFAULT_GROQ_MODEL}`
        - **Vision Capability:** Multimodal High-Resolution Analysis
        - **Database:** SQLite 3 (WAL mode enabled)
        - **Framework:** Streamlit Multi-Page Architecture
        - **Data Security:** PBKDF2 HMAC SHA-256 Authentication & Isolated Tenant Workspaces
        """)


if __name__ == "__main__" or True:
    render_settings()

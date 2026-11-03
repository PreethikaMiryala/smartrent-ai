"""
SmartRent AI - Context-Aware Chatbot Interface
"""
import streamlit as st
from services.chatbot import process_chat_message
from utils.authentication import get_current_user, is_owner, is_tenant
from services.groq_service import get_active_groq_api_key


def render_ai_assistant():
    user = get_current_user()
    if not user:
        st.error("Please log in to chat with the SmartRent AI Assistant.")
        st.stop()

    st.title("💬 SmartRent AI Assistant")
    role_label = "Property Owner" if is_owner() else "Tenant"
    st.caption(f"Role: **{role_label}** | Powered by Groq AI (`qwen/qwen3.8-27b`) with live SQLite database integration.")

    # Check API Key
    api_key = get_active_groq_api_key()
    if not api_key:
        st.warning("⚠️ Groq API key is not configured. Please enter your API key in Settings or ask the administrator.")

    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Quick Suggestion Chips based on Role
    st.markdown("##### 💡 Suggested Questions:")
    if is_owner():
        quick_prompts = [
            "How many rooms are currently occupied and vacant?",
            "Who has pending or overdue rent for this month?",
            "What is this month's total collected rental income?",
            "Which tenant has the highest cleanliness score?",
            "Are there any potential property damage alerts?",
            "Which tenants have not submitted inspection photographs yet?"
        ]
    else:
        quick_prompts = [
            "What is my monthly rent and current payment balance?",
            "Have I paid this month's rent?",
            "What was my latest room cleanliness score and AI feedback?",
            "Am I eligible for a rent discount this month?",
            "What specific improvements should I make to my room?",
            "Do I have any open maintenance requests?"
        ]

    # Render quick prompt buttons
    chip_cols = st.columns(min(len(quick_prompts), 3))
    selected_quick_prompt = None
    for idx, prompt_text in enumerate(quick_prompts):
        col_idx = idx % 3
        with chip_cols[col_idx]:
            if st.button(prompt_text, key=f"chip_{idx}", use_container_width=True):
                selected_quick_prompt = prompt_text

    st.markdown("---")

    # Render existing conversation messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User Input handling
    user_input = st.chat_input("Ask a question about rent, rooms, payments, cleanliness scores, or maintenance...")

    prompt_to_send = selected_quick_prompt if selected_quick_prompt else user_input

    if prompt_to_send:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt_to_send})
        with st.chat_message("user"):
            st.markdown(prompt_to_send)

        # Stream AI response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_reply = ""
            
            with st.spinner("Thinking..."):
                response_generator = process_chat_message(
                    user_message=prompt_to_send,
                    user=user,
                    session_messages=st.session_state.messages[:-1]
                )

                for chunk in response_generator:
                    full_reply += chunk
                    response_placeholder.markdown(full_reply + "▌")

                response_placeholder.markdown(full_reply)

        st.session_state.messages.append({"role": "assistant", "content": full_reply})
        if selected_quick_prompt:
            st.rerun()

    # Clear chat option
    if st.session_state.messages:
        st.write("")
        if st.button("🗑️ Clear Conversation History", type="secondary"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__" or True:
    render_ai_assistant()

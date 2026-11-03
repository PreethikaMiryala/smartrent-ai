# SmartRent AI – Intelligent Rental & Property Management System

**Technology Stack:** Python 3, Streamlit, SQLite, Groq AI (`qwen/qwen3.8-27b`), Pillow, Pandas, Plotly  
**Primary Users:** Property Owner & Tenants  

---

## 🌟 Key Features

1. **Role-Based Portals & Privacy Protection:**
   - **Owner / Administrator Portal:** Complete oversight over properties, room units, tenant leases, automated rent billing, cashflow analytics, inspection reports, damage alerts, and system settings.
   - **Tenant Portal:** Isolated dashboard showing individual assigned room details, lease terms, rent payment history, monthly image upload module, cleanliness feedback, reward points, and maintenance request tracker.
   - **Privacy Boundary:** Tenants can only view their own unit, financial statements, and inspection data.

2. **Multimodal AI Room Cleanliness Inspection:**
   - Powered by **Groq Cloud** using `qwen/qwen3.8-27b` multimodal vision model.
   - Evaluates:
     - Floor cleanliness & stains
     - Dust & visible dirt
     - Waste management & trash disposal
     - Bed & linen organization
     - Furniture & desk organization
     - Kitchen cleanliness (if applicable)
     - Bathroom hygiene & dryness (if applicable)
   - Generates score (0–100), category score breakdown, positive observations, improvement areas, and cleaning tips.

3. **AI Tenant Reward & Discount Engine:**
   - **Automatic Rent Discounts:**
     - `90–100 Score`: **10%** Rent Discount
     - `80–89 Score`: **5%** Rent Discount
     - `70–79 Score`: **2%** Rent Discount
     - `Below 70`: **0%** Discount
   - **Owner Approval Workflow:** Owner reviews and approves discounts before applying them to invoices.
   - **Financial Safety:** Built-in validation guarantees discounts are never applied twice to the same monthly invoice.

4. **AI Property Damage Detection & Alerts:**
   - Detects cracks, damaged paint, broken tiles, damp walls, leaking fixtures, and furniture wear.
   - Compares with previous inspection photographs.
   - Provides confidence scores and severity flags (Low / Medium / High).
   - Owner can verify damage, dismiss false positives, or convert an alert directly into a **Maintenance Work Order**.

5. **Context-Aware AI Assistant (Chatbot):**
   - Grounded directly in live SQLite database records (no hallucination).
   - Natural language streaming responses with quick question suggestion chips.
   - **Owner Queries:** Occupancy rates, pending payments, highest cleanliness performers, tenants missing photos.
   - **Tenant Queries:** Monthly rent, invoice status, latest cleanliness feedback, tips for room improvement.

6. **Full Rent Invoicing & Payment Ledger:**
   - Monthly invoice generation for all active tenants with approved discounts factored in.
   - Records full and partial payments across UPI, Bank Transfer, Cash, and Cheque.
   - Automated balance calculations and overdue status tracking.

7. **Reports & Analytics:**
   - Interactive Plotly charts for room occupancy, income cashflow, and cleanliness distributions.
   - One-click CSV exports for accounting and auditing.

8. **In-App Groq API Key Configuration:**
   - Password-type API key input with connection test and disconnect features.
   - Keys are kept securely in memory session state and never saved to the database.

---

## 🚀 How to Run the Application

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the Streamlit application
streamlit run app.py
```

---

## 🔑 Default Sign-In Credentials

Quick demo one-click login buttons are provided on the login page:

| Role | Username | Password | Notes |
|---|---|---|---|
| **Property Owner / Admin** | `admin` | `admin123` | Full access to all property features |
| **Tenant 1 (Room 101)** | `rahul_sharma` | `rahul123` | Active lease, 92.5 score, partial payment |
| **Tenant 2 (Room 102)** | `priya_patel` | `priya123` | Active lease, 94.0 score, fully paid |
| **Tenant 3 (Room 201)** | `amit_kumar` | `amit123` | Active lease, pending invoice & maintenance |

---

## 📁 Project Architecture

```text
Streamlit Project Rentals/
│
├── app.py                     # Main router with st.navigation & session authentication
├── database.py                # SQLite database schema, 12 tables, indexes & seed data
├── config.py                  # System constants, reward tiers, damage categories & paths
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (GROQ_API_KEY)
├── .gitignore                 # Safe git exclusion rules
│
├── pages/
│   ├── owner_dashboard.py     # Owner KPI dashboard & Plotly charts
│   ├── tenant_dashboard.py    # Personalized tenant overview & lease status
│   ├── room_management.py     # Add, edit, delete, and view rental units
│   ├── tenant_management.py   # Register tenants and assign units
│   ├── rent_payments.py       # Rent invoices, payments ledger & receipts
│   ├── ai_inspection.py       # Multi-image room upload & AI scoring report
│   ├── damage_alerts.py       # AI damage detection & owner verification
│   ├── rewards.py             # Reward approval queue, history & policy editor
│   ├── maintenance.py         # Tenant issue tickets & owner work orders
│   ├── reports.py             # Analytics charts & downloadable CSV exports
│   ├── ai_assistant.py        # Streamlit chatbot with streaming Qwen AI
│   └── settings.py            # In-app Groq API key manager & system config
│
├── services/
│   ├── groq_service.py        # Groq client, streaming handler & connection tester
│   ├── image_analysis.py      # Multimodal vision inspection pipeline
│   ├── chatbot.py             # Context engine querying SQLite for chatbot
│   ├── rent_service.py        # Rent invoicing, partial payment & balance calculations
│   └── reward_service.py      # Discount calculation & approval workflow
│
├── utils/
│   ├── authentication.py      # PBKDF2 HMAC SHA-256 password security & session
│   ├── image_utils.py         # Pillow validation, resizing & base64 encoder
│   └── helpers.py             # Currency (₹), date, and status badges
│
├── uploads/                   # Secure storage for room & maintenance images
└── data/
    └── smartrent.db           # SQLite persistent database file
```

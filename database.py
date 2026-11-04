"""
SmartRent AI - SQLite Database Initialization and Access Layer
"""
import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from config import DB_PATH, DEFAULT_REWARD_TIERS, DEFAULT_MAX_DISCOUNT_PERCENT
from utils.authentication import hash_password


def get_db_connection() -> sqlite3.Connection:
    """Creates a database connection with Row factory and foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initializes the complete database schema and seed data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('owner', 'tenant')),
        full_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Rooms Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        monthly_rent REAL NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'Vacant' CHECK(status IN ('Vacant', 'Occupied', 'Maintenance')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Tenants Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
        joining_date DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive')),
        emergency_contact TEXT,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Rent Records Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rent_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        room_id INTEGER NOT NULL REFERENCES rooms(id),
        month_year TEXT NOT NULL,
        base_rent REAL NOT NULL,
        discount_percentage REAL DEFAULT 0.0,
        discount_amount REAL DEFAULT 0.0,
        final_rent REAL NOT NULL,
        paid_amount REAL DEFAULT 0.0,
        balance REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Partially Paid', 'Paid', 'Overdue')),
        due_date DATE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tenant_id, month_year)
    );
    """)

    # 5. Payments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rent_record_id INTEGER NOT NULL REFERENCES rent_records(id) ON DELETE CASCADE,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id),
        amount REAL NOT NULL,
        payment_date DATE NOT NULL,
        payment_method TEXT NOT NULL,
        transaction_reference TEXT,
        notes TEXT,
        recorded_by INTEGER REFERENCES users(id),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Inspections Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        room_id INTEGER NOT NULL REFERENCES rooms(id),
        month_year TEXT NOT NULL,
        submission_date DATETIME NOT NULL,
        overall_score REAL,
        result_category TEXT CHECK(result_category IN ('Excellent', 'Good', 'Average', 'Needs Improvement')),
        positive_observations TEXT,
        areas_for_improvement TEXT,
        recommendations TEXT,
        reward_eligible INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Pending Review' CHECK(status IN ('Pending Review', 'Inspected', 'Resubmission Requested')),
        ai_analysis_raw TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 7. Inspection Images Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inspection_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
        image_type TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_size INTEGER,
        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 8. Cleanliness Scores Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cleanliness_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
        category TEXT NOT NULL,
        score REAL NOT NULL,
        max_score REAL DEFAULT 100,
        notes TEXT
    );
    """)

    # 9. Rewards Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        inspection_id INTEGER REFERENCES inspections(id) ON DELETE SET NULL,
        rent_record_id INTEGER REFERENCES rent_records(id) ON DELETE SET NULL,
        month_year TEXT NOT NULL,
        cleanliness_score REAL NOT NULL,
        discount_percentage REAL NOT NULL,
        discount_amount REAL NOT NULL,
        reward_points INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Pending Approval' CHECK(status IN ('Pending Approval', 'Approved', 'Rejected', 'Applied')),
        owner_comments TEXT,
        approved_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 10. Damage Alerts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS damage_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER REFERENCES inspections(id) ON DELETE SET NULL,
        room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        damage_category TEXT NOT NULL,
        description TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'Medium' CHECK(severity IN ('Low', 'Medium', 'High')),
        confidence REAL DEFAULT 0.8,
        image_ref TEXT,
        previous_inspection_comparison TEXT,
        recommended_action TEXT,
        status TEXT NOT NULL DEFAULT 'Pending Review' CHECK(status IN ('Pending Review', 'Verified', 'Not Damage', 'Maintenance Scheduled')),
        owner_comments TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11. Maintenance Requests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
        room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Urgent')),
        status TEXT NOT NULL DEFAULT 'Submitted' CHECK(status IN ('Submitted', 'In Progress', 'Completed', 'Cancelled')),
        image_path TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME,
        owner_notes TEXT
    );
    """)

    # 12. Chatbot Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chatbot_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        role TEXT NOT NULL,
        query TEXT NOT NULL,
        response TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 13. System Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL,
        description TEXT
    );
    """)

    conn.commit()

    # Seed initial data if users table is empty
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        seed_sample_data(conn)

    conn.close()


def seed_sample_data(conn: sqlite3.Connection):
    """Seed initial realistic rental data into the SQLite database."""
    cursor = conn.cursor()

    # 1. Create Default Owner
    admin_hash, admin_salt = hash_password("admin123")
    cursor.execute("""
    INSERT INTO users (username, password_hash, salt, role, full_name, email, phone)
    VALUES (?, ?, ?, 'owner', 'Vikramaditya Rao (Owner)', 'owner@smartrent.ai', '+91 98765 43210');
    """, ("admin", admin_hash, admin_salt))
    owner_user_id = cursor.lastrowid

    # 2. Create Rooms
    sample_rooms = [
        ("Room 101", 8000.0, "Spacious 1BHK with private attached bathroom and balcony", "Occupied"),
        ("Room 102", 7500.0, "Cozy studio with modern tiled flooring and kitchenette", "Occupied"),
        ("Room 103", 6000.0, "Single room with shared kitchen and fast Wi-Fi", "Vacant"),
        ("Room 201", 9000.0, "Deluxe corner 1BHK with panoramic view and modular wardrobe", "Occupied"),
        ("Room 202", 6500.0, "Standard 1RK under routine electrical maintenance", "Maintenance"),
        ("Room 203", 8500.0, "Executive studio room, freshly painted and cleaned", "Vacant"),
    ]
    room_ids = {}
    for r_num, rent, desc, st_val in sample_rooms:
        cursor.execute("""
        INSERT INTO rooms (room_number, monthly_rent, description, status)
        VALUES (?, ?, ?, ?);
        """, (r_num, rent, desc, st_val))
        room_ids[r_num] = cursor.lastrowid

    # 3. Create Tenants
    sample_tenants_data = [
        ("shiva_guptha", "shiva123", "Shiva Guptha", "shiva.g@example.com", "+91 91234 56789", "Room 101", "2026-06-01", "+91 99887 76655"),
        ("preethika_guptha", "preethika123", "Preethika Guptha", "preethika.g@example.com", "+91 92345 67890", "Room 102", "2026-08-15", "+91 98760 12345"),
        ("bunny", "bunny123", "Bunny", "bunny@example.com", "+91 93456 78901", "Room 201", "2026-09-01", "+91 94567 11223"),
    ]

    tenant_ids = {}
    for u_name, pwd, full_name, email, phone, room_num, join_date, emer in sample_tenants_data:
        h_pwd, s_pwd = hash_password(pwd)
        cursor.execute("""
        INSERT INTO users (username, password_hash, salt, role, full_name, email, phone)
        VALUES (?, ?, ?, 'tenant', ?, ?, ?);
        """, (u_name, h_pwd, s_pwd, full_name, email, phone))
        u_id = cursor.lastrowid

        r_id = room_ids[room_num]
        cursor.execute("""
        INSERT INTO tenants (user_id, room_id, joining_date, status, emergency_contact, notes)
        VALUES (?, ?, ?, 'Active', ?, 'Punctual tenant, respectful of property');
        """, (u_id, r_id, join_date, emer))
        tenant_ids[u_name] = cursor.lastrowid

    # 4. Create Rent Records & Payments for Current Month (2026-11) and Previous Month (2026-10)
    current_month = "2026-11"
    prev_month = "2026-10"

    # Preethika: Room 102 (₹7500). In Oct, paid on time with 5% discount (₹375). Final: ₹7125. Paid: ₹7125.
    # In Nov: Base ₹7500, earned 10% discount approved! Final ₹6750. Paid: ₹6750 (Paid)
    cursor.execute("""
    INSERT INTO rent_records (tenant_id, room_id, month_year, base_rent, discount_percentage, discount_amount, final_rent, paid_amount, balance, status, due_date)
    VALUES (?, ?, ?, 7500.0, 10.0, 750.0, 6750.0, 6750.0, 0.0, 'Paid', '2026-11-05');
    """, (tenant_ids["preethika_guptha"], room_ids["Room 102"], current_month))
    preethika_rent_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO payments (rent_record_id, tenant_id, amount, payment_date, payment_method, transaction_reference, notes, recorded_by)
    VALUES (?, ?, 6750.0, '2026-11-03', 'UPI', 'UPI/20261103/778921', 'Full payment received via PhonePe', ?);
    """, (preethika_rent_id, tenant_ids["preethika_guptha"], owner_user_id))

    # Shiva: Room 101 (₹8000). In Nov: Base ₹8000, 10% discount approved (₹800). Final ₹7200. Paid: ₹4000. Balance: ₹3200 (Partially Paid)
    cursor.execute("""
    INSERT INTO rent_records (tenant_id, room_id, month_year, base_rent, discount_percentage, discount_amount, final_rent, paid_amount, balance, status, due_date)
    VALUES (?, ?, ?, 8000.0, 10.0, 800.0, 7200.0, 4000.0, 3200.0, 'Partially Paid', '2026-11-05');
    """, (tenant_ids["shiva_guptha"], room_ids["Room 101"], current_month))
    shiva_rent_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO payments (rent_record_id, tenant_id, amount, payment_date, payment_method, transaction_reference, notes, recorded_by)
    VALUES (?, ?, 4000.0, '2026-11-02', 'Bank Transfer', 'IMPS-998822341', 'Partial installment paid, remaining promised by 10th', ?);
    """, (shiva_rent_id, tenant_ids["shiva_guptha"], owner_user_id))

    # Bunny: Room 201 (₹9000). In Nov: Base ₹9000, 0% discount. Final ₹9000. Paid: 0. Balance: ₹9000 (Pending)
    cursor.execute("""
    INSERT INTO rent_records (tenant_id, room_id, month_year, base_rent, discount_percentage, discount_amount, final_rent, paid_amount, balance, status, due_date)
    VALUES (?, ?, ?, 9000.0, 0.0, 0.0, 9000.0, 0.0, 9000.0, 'Pending', '2026-11-05');
    """, (tenant_ids["bunny"], room_ids["Room 201"], current_month))

    # 5. Create Sample Completed Inspection for Shiva Guptha (Room 101)
    cursor.execute("""
    INSERT INTO inspections (tenant_id, room_id, month_year, submission_date, overall_score, result_category, positive_observations, areas_for_improvement, recommendations, reward_eligible, status, ai_analysis_raw)
    VALUES (?, ?, ?, '2026-11-01 10:15:00', 92.5, 'Excellent',
    'Spotless tile flooring; neatly made bed with clean linen; zero dust visible on main shelves; trash bin cleared and covered properly.',
    'Slight moisture around bathroom washbasin edge.',
    'Wipe the silicone border around the sink dry after use to prevent water deposit stains.',
    1, 'Inspected', '{"overall_score": 92.5, "result": "Excellent"}');
    """, (tenant_ids["shiva_guptha"], room_ids["Room 101"], current_month))
    shiva_insp_id = cursor.lastrowid

    # Detailed scores for Shiva
    scores_shiva = [
        ("Floor Cleanliness", 96, "Tiled floor is polished and free of stains"),
        ("Dust & Visible Dirt", 92, "Shelves and surfaces are clean"),
        ("Waste Management", 95, "Dustbin emptied and fitted with fresh bag"),
        ("Bed Organization", 94, "Neat bedsheet, pillows arranged symmetrically"),
        ("Furniture Organization", 90, "Desk and chair organized"),
        ("Kitchen Cleanliness", 88, "Countertop wiped down"),
        ("Bathroom Cleanliness", 90, "Clean mirror and floor tiles"),
    ]
    for cat, sc, notes in scores_shiva:
        cursor.execute("""
        INSERT INTO cleanliness_scores (inspection_id, category, score, max_score, notes)
        VALUES (?, ?, ?, 100, ?);
        """, (shiva_insp_id, cat, sc, notes))

    # Create Shiva's Reward
    cursor.execute("""
    INSERT INTO rewards (tenant_id, inspection_id, rent_record_id, month_year, cleanliness_score, discount_percentage, discount_amount, reward_points, status, owner_comments, approved_at)
    VALUES (?, ?, ?, ?, 92.5, 10.0, 800.0, 95, 'Approved', 'Great job maintaining the room!', '2026-11-01 14:00:00');
    """, (tenant_ids["shiva_guptha"], shiva_insp_id, shiva_rent_id, current_month))

    # 6. Create Sample Completed Inspection for Preethika Guptha (Room 102)
    cursor.execute("""
    INSERT INTO inspections (tenant_id, room_id, month_year, submission_date, overall_score, result_category, positive_observations, areas_for_improvement, recommendations, reward_eligible, status, ai_analysis_raw)
    VALUES (?, ?, ?, '2026-11-01 12:30:00', 94.0, 'Excellent',
    'Exceptional kitchen hygiene, organized study table, sparkling clean bathroom floor and fixtures.',
    'Minor clutter on top shelf of wardrobe.',
    'Keep shoe rack orderly near the entrance door.',
    1, 'Inspected', '{"overall_score": 94.0, "result": "Excellent"}');
    """, (tenant_ids["preethika_guptha"], room_ids["Room 102"], current_month))
    preethika_insp_id = cursor.lastrowid

    scores_preethika = [
        ("Floor Cleanliness", 95, "Immaculate floor"),
        ("Dust & Visible Dirt", 95, "No dust on fan or tables"),
        ("Waste Management", 92, "Segregated waste bins"),
        ("Bed Organization", 92, "Folded blanket and clean linen"),
        ("Furniture Organization", 94, "Well positioned chairs and books"),
        ("Kitchen Cleanliness", 96, "Stove and basin clean"),
        ("Bathroom Cleanliness", 94, "Dry and sanitized"),
    ]
    for cat, sc, notes in scores_preethika:
        cursor.execute("""
        INSERT INTO cleanliness_scores (inspection_id, category, score, max_score, notes)
        VALUES (?, ?, ?, 100, ?);
        """, (preethika_insp_id, cat, sc, notes))

    cursor.execute("""
    INSERT INTO rewards (tenant_id, inspection_id, rent_record_id, month_year, cleanliness_score, discount_percentage, discount_amount, reward_points, status, owner_comments, approved_at)
    VALUES (?, ?, ?, ?, 94.0, 10.0, 750.0, 100, 'Applied', 'Outstanding cleanliness consistently', '2026-11-01 16:30:00');
    """, (tenant_ids["preethika_guptha"], preethika_insp_id, preethika_rent_id, current_month))

    # 7. Create Sample Damage Alert (for review)
    cursor.execute("""
    INSERT INTO damage_alerts (inspection_id, room_id, tenant_id, damage_category, description, severity, confidence, image_ref, previous_inspection_comparison, recommended_action, status, owner_comments)
    VALUES (?, ?, ?, 'Damp Walls', 'Minor paint dampness patch observed near the window frame on the north wall', 'Low', 0.82, 'uploads/sample_damp.jpg', 'Not present in October inspection photos; likely recent monsoon seepage', 'Inspect window sealant from the outside; apply water repellent coating', 'Pending Review', NULL);
    """, (shiva_insp_id, room_ids["Room 101"], tenant_ids["shiva_guptha"]))

    # 8. Create Sample Maintenance Request
    cursor.execute("""
    INSERT INTO maintenance_requests (tenant_id, room_id, category, title, description, priority, status, image_path, owner_notes)
    VALUES (?, ?, 'Plumbing', 'Bathroom Sink Slow Drainage', 'Water drains very slowly from the bathroom sink basin after washing hands.', 'Medium', 'In Progress', NULL, 'Plumber scheduled for tomorrow morning 11 AM');
    """, (tenant_ids["bunny"], room_ids["Room 201"]))

    cursor.execute("""
    INSERT INTO maintenance_requests (tenant_id, room_id, category, title, description, priority, status, image_path, resolved_at, owner_notes)
    VALUES (?, ?, 'Electrical', 'Ceiling Fan Regulator Humming', 'Fan regulator makes a mild buzzing noise on speed 3.', 'Low', 'Completed', NULL, '2026-10-25 15:00:00', 'Regulator replaced with brand new Anchor switch');
    """, (tenant_ids["shiva_guptha"], room_ids["Room 101"]))

    # 9. System Settings
    settings = [
        ("reward_tiers_json", json.dumps(DEFAULT_REWARD_TIERS), "Discount percentage tiers based on cleanliness score"),
        ("max_discount_percent", str(DEFAULT_MAX_DISCOUNT_PERCENT), "Cap on maximum allowed rent discount percentage"),
        ("auto_approve_rewards", "false", "Whether AI rewards are applied automatically or require owner review"),
        ("photo_retention_months", "12", "Number of months to retain historical inspection photographs"),
    ]
    for k, v, d in settings:
        cursor.execute("""
        INSERT OR REPLACE INTO system_settings (setting_key, setting_value, description)
        VALUES (?, ?, ?);
        """, (k, v, d))

    conn.commit()


# =========================================================================
# Query & Data Access Helper Functions
# =========================================================================

def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False, commit: bool = False):
    """Safe generic helper to execute queries with parameterized values."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            last_id = cursor.lastrowid
            return last_id
        if fetch_one:
            row = cursor.fetchone()
            return dict(row) if row else None
        if fetch_all:
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        return None
    finally:
        conn.close()


# --- User Queries ---
def get_user_by_username(username: str) -> Optional[dict]:
    return execute_query("SELECT * FROM users WHERE username = ?;", (username,), fetch_one=True)


def get_user_by_id(user_id: int) -> Optional[dict]:
    return execute_query("SELECT * FROM users WHERE id = ?;", (user_id,), fetch_one=True)


def create_user(username: str, plain_password: str, role: str, full_name: str, email: str = "", phone: str = "") -> int:
    h_pwd, salt = hash_password(plain_password)
    return execute_query(
        "INSERT INTO users (username, password_hash, salt, role, full_name, email, phone) VALUES (?, ?, ?, ?, ?, ?, ?);",
        (username, h_pwd, salt, role, full_name, email, phone),
        commit=True
    )


# --- Room Queries ---
def get_all_rooms() -> List[dict]:
    query = """
    SELECT r.*, 
           t.id as tenant_id, 
           u.full_name as tenant_name,
           u.phone as tenant_phone
    FROM rooms r
    LEFT JOIN tenants t ON r.id = t.room_id AND t.status = 'Active'
    LEFT JOIN users u ON t.user_id = u.id
    ORDER BY r.room_number ASC;
    """
    return execute_query(query, fetch_all=True)


def get_room_by_id(room_id: int) -> Optional[dict]:
    query = """
    SELECT r.*, 
           t.id as tenant_id, 
           u.full_name as tenant_name,
           u.phone as tenant_phone
    FROM rooms r
    LEFT JOIN tenants t ON r.id = t.room_id AND t.status = 'Active'
    LEFT JOIN users u ON t.user_id = u.id
    WHERE r.id = ?;
    """
    return execute_query(query, (room_id,), fetch_one=True)


def create_room(room_number: str, monthly_rent: float, description: str = "", status: str = "Vacant") -> int:
    return execute_query(
        "INSERT INTO rooms (room_number, monthly_rent, description, status) VALUES (?, ?, ?, ?);",
        (room_number, monthly_rent, description, status),
        commit=True
    )


def update_room(room_id: int, room_number: str, monthly_rent: float, description: str, status: str) -> bool:
    execute_query(
        "UPDATE rooms SET room_number = ?, monthly_rent = ?, description = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
        (room_number, monthly_rent, description, status, room_id),
        commit=True
    )
    return True


def delete_room(room_id: int) -> bool:
    execute_query("DELETE FROM rooms WHERE id = ?;", (room_id,), commit=True)
    return True


# --- Tenant Queries ---
def get_all_tenants() -> List[dict]:
    query = """
    SELECT t.*, 
           u.username, u.full_name, u.email, u.phone,
           r.room_number, r.monthly_rent, r.status as room_status
    FROM tenants t
    JOIN users u ON t.user_id = u.id
    LEFT JOIN rooms r ON t.room_id = r.id
    ORDER BY u.full_name ASC;
    """
    return execute_query(query, fetch_all=True)


def get_tenant_by_id(tenant_id: int) -> Optional[dict]:
    query = """
    SELECT t.*, 
           u.username, u.full_name, u.email, u.phone,
           r.room_number, r.monthly_rent, r.description as room_description
    FROM tenants t
    JOIN users u ON t.user_id = u.id
    LEFT JOIN rooms r ON t.room_id = r.id
    WHERE t.id = ?;
    """
    return execute_query(query, (tenant_id,), fetch_one=True)


def get_tenant_by_user_id(user_id: int) -> Optional[dict]:
    query = """
    SELECT t.*, 
           u.username, u.full_name, u.email, u.phone,
           r.room_number, r.monthly_rent, r.description as room_description
    FROM tenants t
    JOIN users u ON t.user_id = u.id
    LEFT JOIN rooms r ON t.room_id = r.id
    WHERE t.user_id = ?;
    """
    return execute_query(query, (user_id,), fetch_one=True)


def create_tenant(user_id: int, room_id: Optional[int], joining_date: str, emergency_contact: str = "", notes: str = "") -> int:
    t_id = execute_query(
        "INSERT INTO tenants (user_id, room_id, joining_date, status, emergency_contact, notes) VALUES (?, ?, ?, 'Active', ?, ?);",
        (user_id, room_id, joining_date, emergency_contact, notes),
        commit=True
    )
    if room_id:
        execute_query("UPDATE rooms SET status = 'Occupied' WHERE id = ?;", (room_id,), commit=True)
    return t_id


def update_tenant(tenant_id: int, room_id: Optional[int], status: str, emergency_contact: str, notes: str) -> bool:
    # Check old room
    old = get_tenant_by_id(tenant_id)
    execute_query(
        "UPDATE tenants SET room_id = ?, status = ?, emergency_contact = ?, notes = ? WHERE id = ?;",
        (room_id, status, emergency_contact, notes, tenant_id),
        commit=True
    )
    if old and old.get("room_id") and old["room_id"] != room_id:
        # Check if old room has other active tenants
        other = execute_query("SELECT id FROM tenants WHERE room_id = ? AND status = 'Active' AND id != ?;", (old["room_id"], tenant_id), fetch_one=True)
        if not other:
            execute_query("UPDATE rooms SET status = 'Vacant' WHERE id = ?;", (old["room_id"],), commit=True)
    if room_id and status == 'Active':
        execute_query("UPDATE rooms SET status = 'Occupied' WHERE id = ?;", (room_id,), commit=True)
    return True


# --- Rent & Payment Queries ---
def get_all_rent_records(month_year: Optional[str] = None) -> List[dict]:
    query = """
    SELECT rr.*, 
           u.full_name as tenant_name, u.phone as tenant_phone,
           r.room_number
    FROM rent_records rr
    JOIN tenants t ON rr.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    JOIN rooms r ON rr.room_id = r.id
    """
    params = ()
    if month_year:
        query += " WHERE rr.month_year = ?"
        params = (month_year,)
    query += " ORDER BY rr.month_year DESC, r.room_number ASC;"
    return execute_query(query, params, fetch_all=True)


def get_tenant_rent_records(tenant_id: int) -> List[dict]:
    query = """
    SELECT rr.*, r.room_number
    FROM rent_records rr
    JOIN rooms r ON rr.room_id = r.id
    WHERE rr.tenant_id = ?
    ORDER BY rr.month_year DESC;
    """
    return execute_query(query, (tenant_id,), fetch_all=True)


def get_rent_record_by_id(record_id: int) -> Optional[dict]:
    query = """
    SELECT rr.*, 
           u.full_name as tenant_name, u.email as tenant_email, u.phone as tenant_phone,
           r.room_number
    FROM rent_records rr
    JOIN tenants t ON rr.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    JOIN rooms r ON rr.room_id = r.id
    WHERE rr.id = ?;
    """
    return execute_query(query, (record_id,), fetch_one=True)


def get_payments_for_rent_record(record_id: int) -> List[dict]:
    query = """
    SELECT p.*, u.full_name as recorded_by_name
    FROM payments p
    LEFT JOIN users u ON p.recorded_by = u.id
    WHERE p.rent_record_id = ?
    ORDER BY p.payment_date DESC;
    """
    return execute_query(query, (record_id,), fetch_all=True)


def get_all_payments() -> List[dict]:
    query = """
    SELECT p.*, 
           u.full_name as tenant_name,
           r.room_number,
           rr.month_year
    FROM payments p
    JOIN tenants t ON p.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    JOIN rent_records rr ON p.rent_record_id = rr.id
    JOIN rooms r ON rr.room_id = r.id
    ORDER BY p.payment_date DESC;
    """
    return execute_query(query, fetch_all=True)


# --- Inspection Queries ---
def get_all_inspections(month_year: Optional[str] = None) -> List[dict]:
    query = """
    SELECT i.*, 
           u.full_name as tenant_name,
           r.room_number,
           (SELECT COUNT(*) FROM inspection_images WHERE inspection_id = i.id) as image_count
    FROM inspections i
    JOIN tenants t ON i.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    JOIN rooms r ON i.room_id = r.id
    """
    params = ()
    if month_year:
        query += " WHERE i.month_year = ?"
        params = (month_year,)
    query += " ORDER BY i.submission_date DESC;"
    return execute_query(query, params, fetch_all=True)


def get_inspection_by_id(inspection_id: int) -> Optional[dict]:
    query = """
    SELECT i.*, 
           u.full_name as tenant_name,
           r.room_number
    FROM inspections i
    JOIN tenants t ON i.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    JOIN rooms r ON i.room_id = r.id
    WHERE i.id = ?;
    """
    return execute_query(query, (inspection_id,), fetch_one=True)


def get_tenant_inspections(tenant_id: int) -> List[dict]:
    query = """
    SELECT i.*, r.room_number,
           (SELECT COUNT(*) FROM inspection_images WHERE inspection_id = i.id) as image_count
    FROM inspections i
    JOIN rooms r ON i.room_id = r.id
    WHERE i.tenant_id = ?
    ORDER BY i.submission_date DESC;
    """
    return execute_query(query, (tenant_id,), fetch_all=True)


def get_inspection_images(inspection_id: int) -> List[dict]:
    return execute_query(
        "SELECT * FROM inspection_images WHERE inspection_id = ? ORDER BY id ASC;",
        (inspection_id,),
        fetch_all=True
    )


def get_cleanliness_scores(inspection_id: int) -> List[dict]:
    return execute_query(
        "SELECT * FROM cleanliness_scores WHERE inspection_id = ? ORDER BY id ASC;",
        (inspection_id,),
        fetch_all=True
    )


# --- Rewards Queries ---
def get_all_rewards() -> List[dict]:
    query = """
    SELECT rw.*, 
           u.full_name as tenant_name,
           r.room_number,
           i.overall_score
    FROM rewards rw
    JOIN tenants t ON rw.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    LEFT JOIN inspections i ON rw.inspection_id = i.id
    LEFT JOIN rooms r ON i.room_id = r.id
    ORDER BY rw.created_at DESC;
    """
    return execute_query(query, fetch_all=True)


def get_tenant_rewards(tenant_id: int) -> List[dict]:
    query = """
    SELECT rw.*, 
           i.overall_score
    FROM rewards rw
    LEFT JOIN inspections i ON rw.inspection_id = i.id
    WHERE rw.tenant_id = ?
    ORDER BY rw.created_at DESC;
    """
    return execute_query(query, (tenant_id,), fetch_all=True)


# --- Damage Alerts Queries ---
def get_all_damage_alerts() -> List[dict]:
    query = """
    SELECT da.*, 
           u.full_name as tenant_name,
           r.room_number
    FROM damage_alerts da
    JOIN rooms r ON da.room_id = r.id
    JOIN tenants t ON da.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    ORDER BY da.created_at DESC;
    """
    return execute_query(query, fetch_all=True)


# --- Maintenance Queries ---
def get_all_maintenance_requests() -> List[dict]:
    query = """
    SELECT m.*, 
           u.full_name as tenant_name,
           r.room_number
    FROM maintenance_requests m
    JOIN tenants t ON m.tenant_id = t.id
    JOIN users u ON t.user_id = u.id
    JOIN rooms r ON m.room_id = r.id
    ORDER BY 
        CASE m.priority 
            WHEN 'Urgent' THEN 1 
            WHEN 'High' THEN 2 
            WHEN 'Medium' THEN 3 
            ELSE 4 
        END,
        m.created_at DESC;
    """
    return execute_query(query, fetch_all=True)


def get_tenant_maintenance_requests(tenant_id: int) -> List[dict]:
    query = """
    SELECT m.*, r.room_number
    FROM maintenance_requests m
    JOIN rooms r ON m.room_id = r.id
    WHERE m.tenant_id = ?
    ORDER BY m.created_at DESC;
    """
    return execute_query(query, (tenant_id,), fetch_all=True)


# --- System Settings Queries ---
def get_setting(key: str, default: str = "") -> str:
    res = execute_query("SELECT setting_value FROM system_settings WHERE setting_key = ?;", (key,), fetch_one=True)
    return res["setting_value"] if res else default


def set_setting(key: str, value: str, description: str = ""):
    execute_query(
        "INSERT OR REPLACE INTO system_settings (setting_key, setting_value, description) VALUES (?, ?, ?);",
        (key, value, description),
        commit=True
    )


# --- Dashboard KPI Aggregation ---
def get_dashboard_metrics(month_year: Optional[str] = None) -> Dict[str, Any]:
    """Calculates all essential metrics for the owner dashboard from real SQLite data."""
    if not month_year:
        month_year = datetime.now().strftime("%Y-%m")

    conn = get_db_connection()
    c = conn.cursor()

    # Room stats
    c.execute("SELECT COUNT(*) FROM rooms;")
    total_rooms = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Occupied';")
    occupied_rooms = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM rooms WHERE status = 'Vacant';")
    vacant_rooms = c.fetchone()[0]

    # Tenant stats
    c.execute("SELECT COUNT(*) FROM tenants WHERE status = 'Active';")
    total_tenants = c.fetchone()[0]

    # Financial stats for the selected month
    c.execute("""
    SELECT 
        COALESCE(SUM(base_rent), 0),
        COALESCE(SUM(discount_amount), 0),
        COALESCE(SUM(final_rent), 0),
        COALESCE(SUM(paid_amount), 0),
        COALESCE(SUM(balance), 0)
    FROM rent_records 
    WHERE month_year = ?;
    """, (month_year,))
    row = c.fetchone()
    expected_rent = row[2]  # final rent payable
    collected_rent = row[3]
    pending_rent = row[4]
    discounts_awarded = row[1]

    # Cleanliness average for the month
    c.execute("""
    SELECT COALESCE(AVG(overall_score), 0)
    FROM inspections
    WHERE month_year = ? AND overall_score IS NOT NULL;
    """, (month_year,))
    avg_cleanliness = round(c.fetchone()[0], 1)

    # Damage alerts count
    c.execute("SELECT COUNT(*) FROM damage_alerts WHERE status = 'Pending Review';")
    pending_damage_alerts = c.fetchone()[0]

    # Maintenance pending count
    c.execute("SELECT COUNT(*) FROM maintenance_requests WHERE status IN ('Submitted', 'In Progress');")
    pending_maintenance = c.fetchone()[0]

    conn.close()

    return {
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "vacant_rooms": vacant_rooms,
        "total_tenants": total_tenants,
        "expected_rent": expected_rent,
        "collected_rent": collected_rent,
        "pending_rent": pending_rent,
        "discounts_awarded": discounts_awarded,
        "avg_cleanliness": avg_cleanliness,
        "pending_damage_alerts": pending_damage_alerts,
        "pending_maintenance": pending_maintenance,
    }

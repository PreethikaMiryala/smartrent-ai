"""
SmartRent AI - System Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
INSPECTION_DIR = UPLOAD_DIR / "inspections"
MAINTENANCE_DIR = UPLOAD_DIR / "maintenance"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
INSPECTION_DIR.mkdir(parents=True, exist_ok=True)
MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Database path
DB_PATH = DATA_DIR / "smartrent.db"

# Groq AI settings
DEFAULT_GROQ_MODEL = "qwen/qwen3.8-27b"
ENV_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Currency and Locale
CURRENCY_SYMBOL = "₹"

# Default Cleanliness Categories for AI Inspection
CLEANLINESS_CATEGORIES = [
    "Floor Cleanliness",
    "Dust & Visible Dirt",
    "Waste Management",
    "Bed Organization",
    "Furniture Organization",
    "Kitchen Cleanliness",
    "Bathroom Cleanliness",
]

# Scoring categories definitions
SCORE_TIERS = {
    "Excellent": (90, 100),
    "Good": (75, 89),
    "Average": (60, 74),
    "Needs Improvement": (0, 59)
}

# Default Reward Structure (Score Range -> Discount %)
DEFAULT_REWARD_TIERS = [
    {"min": 90, "max": 100, "discount_pct": 10.0, "label": "Excellent (90-100%)"},
    {"min": 80, "max": 89, "discount_pct": 5.0, "label": "Good (80-89%)"},
    {"min": 70, "max": 79, "discount_pct": 2.0, "label": "Fair (70-79%)"},
    {"min": 0, "max": 69, "discount_pct": 0.0, "label": "Below 70%"},
]
DEFAULT_MAX_DISCOUNT_PERCENT = 15.0

# Damage Categories for AI Detection
DAMAGE_CATEGORIES = [
    "Wall Cracks",
    "Damaged Paint",
    "Broken Tiles",
    "Damaged Furniture",
    "Broken Windows",
    "Water Leakage",
    "Damp Walls",
    "Damaged Doors",
    "Broken Fixtures",
    "Other Issues",
]

# Maintenance Categories & Priorities
MAINTENANCE_CATEGORIES = [
    "Plumbing",
    "Electrical",
    "Water Leakage",
    "Broken Fixtures",
    "Wall / Paint Damage",
    "Appliance Repair",
    "Carpentry / Door / Window",
    "Other",
]

MAINTENANCE_PRIORITIES = ["Low", "Medium", "High", "Urgent"]
MAINTENANCE_STATUSES = ["Submitted", "In Progress", "Completed", "Cancelled"]

# Rent and Payment
PAYMENT_METHODS = ["UPI", "Bank Transfer", "Cash", "Credit Card", "Debit Card", "Cheque"]
PAYMENT_STATUSES = ["Paid", "Partially Paid", "Pending", "Overdue"]

# Image Upload Constraints
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGES_PER_INSPECTION = 8

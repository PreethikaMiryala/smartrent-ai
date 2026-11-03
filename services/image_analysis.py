"""
SmartRent AI - Multimodal Inspection & Damage Detection Service
"""
import json
import re
import base64
from typing import List, Dict, Any, Tuple, Optional
from groq import Groq

from config import (
    DEFAULT_GROQ_MODEL,
    CLEANLINESS_CATEGORIES,
    DAMAGE_CATEGORIES,
    SCORE_TIERS
)
from services.groq_service import get_active_groq_api_key
from utils.image_utils import encode_image_for_api
import database


def analyze_room_inspection(
    current_image_paths: List[str],
    image_types: List[str],
    tenant_name: str,
    room_number: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes room photographs using Groq's multimodal Qwen model (qwen/qwen3.8-27b).
    Strictly follows Groq SDK multimodal format supporting a maximum of 3 images per request.
    """
    if not current_image_paths:
        raise ValueError("At least one room photograph is required for inspection.")

    key = api_key if api_key else get_active_groq_api_key()
    if not key:
        raise ValueError("Groq API key is not configured. Please enter your API key in Settings.")

    # Limit to maximum 3 images per Groq model constraints
    active_paths = current_image_paths[:3]
    active_types = image_types[:3] if image_types else ["Room Photo"] * len(active_paths)

    client = Groq(api_key=key)

    # Detailed prompt instructing the model to evaluate cleanliness categories & property damages
    prompt_text = (
        "Analyze this room photograph for cleanliness, organization, and potential property damage. "
        "Return a cleanliness score out of 100, observations, recommendations, and suspected damage.\n\n"
        f"Inspection Context:\n"
        f"- Tenant Name: {tenant_name}\n"
        f"- Room Unit: {room_number}\n"
        f"- Photographs Provided: {len(active_paths)} (Types: {', '.join(active_types)})\n\n"
        "Categories to evaluate:\n"
        "- Floor Cleanliness (stains, sweeping, mopping)\n"
        "- Dust and Visible Dirt (shelves, fans, surfaces)\n"
        "- Waste Management (trash bins, garbage disposal)\n"
        "- Bed Organization (linen, sheets, pillows arranged)\n"
        "- Furniture Organization (desks, chairs, orderly placement)\n"
        "- Kitchen Cleanliness (countertop, sink, grease - if visible)\n"
        "- Bathroom Cleanliness (sanitary fixtures, dry tiles - if visible)\n\n"
        "Suspected Property Damage to look for:\n"
        "- Wall cracks, damaged/peeling paint, broken tiles, dampness/water leakage, broken window panes, broken furniture or fixtures.\n\n"
        "Return your analysis in valid JSON format matching this EXACT structure:\n"
        "{\n"
        '  "overall_score": <number 0-100>,\n'
        '  "result_category": "<Excellent | Good | Average | Needs Improvement>",\n'
        '  "category_scores": [\n'
        '    {"category": "Floor Cleanliness", "score": <0-100>, "notes": "<concise note>"},\n'
        '    {"category": "Dust and Visible Dirt", "score": <0-100>, "notes": "<concise note>"},\n'
        '    {"category": "Waste Management", "score": <0-100>, "notes": "<concise note>"},\n'
        '    {"category": "Bed Organization", "score": <0-100>, "notes": "<concise note>"},\n'
        '    {"category": "Furniture Organization", "score": <0-100>, "notes": "<concise note>"},\n'
        '    {"category": "Kitchen Cleanliness", "score": <0-100>, "notes": "<note or N/A>"},\n'
        '    {"category": "Bathroom Cleanliness", "score": <0-100>, "notes": "<note or N/A>"}\n'
        '  ],\n'
        '  "positive_observations": "<1-3 sentences highlighting positive habits>",\n'
        '  "areas_for_improvement": "<1-2 sentences on specific areas needing attention>",\n'
        '  "recommendations": "<actionable cleaning advice>",\n'
        '  "suspected_damage": [\n'
        '    {\n'
        '      "damage_category": "<Wall Cracks | Damaged Paint | Broken Tiles | Damaged Furniture | Broken Windows | Water Leakage | Damp Walls | Broken Fixtures | Other>",\n'
        '      "description": "<detailed observation>",\n'
        '      "severity": "<Low | Medium | High>",\n'
        '      "confidence": <number between 0.5 and 0.99>,\n'
        '      "image_index": 1,\n'
        '      "recommended_action": "<practical recommendation for owner>"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    # Build multimodal content list: text first, followed by base64-encoded image URLs
    user_content: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": prompt_text
        }
    ]

    for p in active_paths:
        b64_img = encode_image_for_api(p)
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_img}"
            }
        })

    # Call Groq SDK using the exact official pattern
    completion = client.chat.completions.create(
        model=DEFAULT_GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": user_content
            }
        ],
        temperature=0.6,
        max_completion_tokens=2048,
        top_p=0.95,
        reasoning_effort="default",
        stream=False
    )

    raw_response = completion.choices[0].message.content or ""
    parsed = _extract_json_response(raw_response)

    # Standardize result format
    overall_score = float(parsed.get("overall_score", 85.0))
    result_cat = parsed.get("result_category")
    if not result_cat:
        if overall_score >= 90:
            result_cat = "Excellent"
        elif overall_score >= 75:
            result_cat = "Good"
        elif overall_score >= 60:
            result_cat = "Average"
        else:
            result_cat = "Needs Improvement"

    # Normalize structure for downstream database storage
    structured_output = {
        "cleanliness": {
            "overall_score": overall_score,
            "result_category": result_cat,
            "category_scores": parsed.get("category_scores", []),
            "positive_observations": parsed.get("positive_observations", "Room is well maintained."),
            "areas_for_improvement": parsed.get("areas_for_improvement", "None noticed."),
            "recommendations": parsed.get("recommendations", "Keep up the regular cleaning."),
            "reward_eligible": (overall_score >= 70.0)
        },
        "damage_alerts": parsed.get("suspected_damage", []) or parsed.get("damage_alerts", []),
        "raw_response": raw_response
    }

    return structured_output


def _extract_json_response(text: str) -> Dict[str, Any]:
    """Robustly extracts JSON from an LLM response string with fallbacks."""
    cleaned = text.strip()

    # 1. Check for markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # 2. Try direct json.loads
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 3. Try finding outer braces
    brace_match = re.search(r"(\{[\s\S]*\})", cleaned)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except Exception:
            pass

    # 4. Fallback parser using regex if model returns narrative
    score_match = re.search(r"(?:score|cleanliness score)[\s:]*([0-9]{1,3})", text, re.IGNORECASE)
    score = float(score_match.group(1)) if score_match else 80.0

    return {
        "overall_score": score,
        "result_category": "Good" if score >= 75 else "Average",
        "category_scores": [
            {"category": "Floor Cleanliness", "score": score, "notes": "Evaluated from uploaded photos"},
            {"category": "Dust and Visible Dirt", "score": score, "notes": "Evaluated from uploaded photos"},
            {"category": "Waste Management", "score": score, "notes": "Evaluated from uploaded photos"},
            {"category": "Bed Organization", "score": score, "notes": "Evaluated from uploaded photos"},
            {"category": "Furniture Organization", "score": score, "notes": "Evaluated from uploaded photos"}
        ],
        "positive_observations": text[:300] if len(text) > 50 else "Room appears in acceptable condition.",
        "areas_for_improvement": "Ensure ongoing maintenance and cleaning.",
        "recommendations": "Regularly wipe surfaces and keep floors clear.",
        "suspected_damage": []
    }


def save_inspection_pipeline(
    tenant_id: int,
    room_id: int,
    month_year: str,
    saved_images: List[Dict[str, Any]],
    ai_result: Dict[str, Any]
) -> int:
    """
    Saves the new inspection, photos, category scores, rewards, and damage alerts to SQLite.
    Preserves historical inspections.
    """
    cleanliness = ai_result.get("cleanliness", {})
    overall_score = float(cleanliness.get("overall_score", 0.0))
    result_cat = cleanliness.get("result_category", "Average")
    positive_obs = cleanliness.get("positive_observations", "")
    areas_imp = cleanliness.get("areas_for_improvement", "")
    recomms = cleanliness.get("recommendations", "")
    reward_elig = 1 if cleanliness.get("reward_eligible", False) else 0

    conn = database.get_db_connection()
    c = conn.cursor()

    # 1. Insert Inspection Record (Always preserves previous inspection history!)
    c.execute("""
    INSERT INTO inspections (
        tenant_id, room_id, month_year, submission_date, overall_score,
        result_category, positive_observations, areas_for_improvement,
        recommendations, reward_eligible, status, ai_analysis_raw
    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, 'Inspected', ?);
    """, (
        tenant_id, room_id, month_year, overall_score,
        result_cat, positive_obs, areas_imp, recomms,
        reward_elig, json.dumps(ai_result)
    ))
    inspection_id = c.lastrowid

    # 2. Insert Inspection Images
    for img in saved_images:
        c.execute("""
        INSERT INTO inspection_images (inspection_id, image_type, file_path, file_name, file_size)
        VALUES (?, ?, ?, ?, ?);
        """, (inspection_id, img.get("type", "Room Photo"), img["path"], img["filename"], img.get("size", 0)))

    # 3. Insert Cleanliness Category Scores
    category_scores = cleanliness.get("category_scores", [])
    for cs in category_scores:
        cat_name = cs.get("category", "General")
        cat_score = float(cs.get("score", overall_score))
        cat_notes = cs.get("notes", "")
        c.execute("""
        INSERT INTO cleanliness_scores (inspection_id, category, score, max_score, notes)
        VALUES (?, ?, ?, 100, ?);
        """, (inspection_id, cat_name, cat_score, cat_notes))

    # 4. Process Reward Eligibility
    c.execute("SELECT monthly_rent FROM rooms WHERE id = ?;", (room_id,))
    room_row = c.fetchone()
    base_rent = room_row["monthly_rent"] if room_row else 0.0

    discount_pct = 0.0
    if overall_score >= 90:
        discount_pct = 10.0
    elif overall_score >= 80:
        discount_pct = 5.0
    elif overall_score >= 70:
        discount_pct = 2.0

    discount_amount = round((discount_pct / 100.0) * base_rent, 2)
    reward_points = int(overall_score)

    if discount_pct > 0:
        c.execute("SELECT id FROM rent_records WHERE tenant_id = ? AND month_year = ?;", (tenant_id, month_year))
        rent_row = c.fetchone()
        rent_rec_id = rent_row["id"] if rent_row else None

        # Check existing reward for this month
        c.execute("SELECT id, status FROM rewards WHERE tenant_id = ? AND month_year = ?;", (tenant_id, month_year))
        existing_rew = c.fetchone()

        if existing_rew and existing_rew["status"] == "Pending Approval":
            # Update pending reward with new score
            c.execute("""
            UPDATE rewards
            SET inspection_id = ?, rent_record_id = ?, cleanliness_score = ?,
                discount_percentage = ?, discount_amount = ?, reward_points = ?,
                created_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """, (inspection_id, rent_rec_id, overall_score, discount_pct, discount_amount, reward_points, existing_rew["id"]))
        elif not existing_rew:
            # Create new reward record
            c.execute("""
            INSERT INTO rewards (
                tenant_id, inspection_id, rent_record_id, month_year,
                cleanliness_score, discount_percentage, discount_amount,
                reward_points, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending Approval');
            """, (tenant_id, inspection_id, rent_rec_id, month_year, overall_score, discount_pct, discount_amount, reward_points))

    # 5. Insert Damage Alerts
    damage_alerts = ai_result.get("damage_alerts", [])
    for da in damage_alerts:
        cat = da.get("damage_category", "Other Issues")
        desc = da.get("description", "")
        sev = da.get("severity", "Medium")
        conf = float(da.get("confidence", 0.8))
        img_idx = da.get("image_index", 1)
        rec_act = da.get("recommended_action", "")

        img_ref = saved_images[img_idx - 1]["path"] if (1 <= img_idx <= len(saved_images)) else (saved_images[0]["path"] if saved_images else "")

        c.execute("""
        INSERT INTO damage_alerts (
            inspection_id, room_id, tenant_id, damage_category,
            description, severity, confidence, image_ref,
            recommended_action, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending Review');
        """, (inspection_id, room_id, tenant_id, cat, desc, sev, conf, img_ref, rec_act))

    conn.commit()
    conn.close()

    return inspection_id

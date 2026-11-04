"""
SmartRent AI - AI Room Inspection & Cleanliness Scoring Module
"""
import streamlit as st
from datetime import datetime
from pathlib import Path
from PIL import Image

import database
from config import INSPECTION_DIR, SCORE_TIERS
from services.image_analysis import analyze_room_inspection, save_inspection_pipeline
from services.groq_service import get_active_groq_api_key
from utils.authentication import is_owner, is_tenant, get_current_user
from utils.image_utils import validate_image, save_image_to_disk
from utils.helpers import (
    format_date,
    format_currency,
    get_score_color,
    calculate_score_category,
    get_month_options,
    get_current_month_str
)


def render_ai_inspection():
    user = get_current_user()
    if not user:
        st.error("Please select an active tenant account to access Room Inspections.")
        st.stop()
        return

    st.title("Room Cleanliness Inspection")

    if is_tenant():
        _render_tenant_inspection(user)
    else:
        _render_owner_inspection(user)


def _render_tenant_inspection(user):
    st.caption("Submit photographs of your unit for automated cleanliness analysis, organization assessment, and monthly rent discounts.")

    tenant = database.get_tenant_by_user_id(user["id"])
    if not tenant or not tenant.get("room_id"):
        st.warning("No room assignment found. Please contact property management.")
        st.stop()

    current_month = get_current_month_str()
    tenant_id = tenant["id"]
    room_id = tenant["room_id"]
    room_number = tenant["room_number"]

    tab_upload, tab_history = st.tabs(["Photograph Submission", "Inspection History"])

    with tab_upload:
        # Check existing inspection for informational banner
        existing_insps = database.get_tenant_inspections(tenant_id)
        current_insp = next((i for i in existing_insps if i["month_year"] == current_month), None)

        if current_insp:
            score = current_insp.get("overall_score", 0.0)
            st.info(
                f"Current Cycle Status ({current_month}): Latest score is {score}/100 ({current_insp.get('result_category', 'Good')}). "
                f"You may upload fresh photographs below to re-evaluate your unit anytime."
            )

        st.markdown("### Upload Unit Photographs")
        st.markdown("""
        **Submission Guidelines:**
        - Upload up to **3 clear photographs** (Full Room View, Floor & Surroundings, Bed & Furniture).
        - Ensure good lighting, neat bedding, and clutter-free flooring for optimal scoring.
        """)

        # Consent Checkbox
        consent = st.checkbox(
            "I consent to AI image analysis of my room photographs for cleanliness scoring, rent discount evaluation, and property integrity checks.",
            value=True
        )

        # File Uploader
        uploaded_files = st.file_uploader(
            "Select photographs (JPG, JPEG, PNG — Maximum 3 images)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="tenant_photo_uploader"
        )

        if uploaded_files:
            # Enforce max 3 images per Groq model limits
            if len(uploaded_files) > 3:
                st.warning("Model limit allows up to 3 images per request. The first 3 photographs will be processed.")
                active_files = uploaded_files[:3]
            else:
                active_files = uploaded_files

            st.markdown(f"##### Selected Images ({len(active_files)}):")

            preview_cols = st.columns(len(active_files))
            image_type_selections = []

            for idx, file in enumerate(active_files):
                with preview_cols[idx]:
                    try:
                        img = Image.open(file)
                        st.image(img, use_container_width=True, caption=f"Photo {idx+1}: {file.name[:22]}")
                    except Exception:
                        st.caption("Preview unavailable")

                    img_type = st.selectbox(
                        f"Area Classification #{idx+1}",
                        options=[
                            "Full Room View",
                            "Floor & Surroundings",
                            "Bed & Furniture",
                            "Kitchen Area",
                            "Bathroom Area",
                            "Other Angle"
                        ],
                        index=min(idx, 5),
                        key=f"tenant_img_type_{idx}"
                    )
                    image_type_selections.append(img_type)

            st.markdown("---")

            # Check Groq API Key
            api_key = get_active_groq_api_key()
            if not api_key:
                st.warning("AI Inspection service is temporarily unavailable. Please contact property management.")

            # Button: "Analyze My Room with AI"
            analyze_clicked = st.button(
                "Analyze My Room with AI",
                type="primary",
                use_container_width=True,
                disabled=not consent or not api_key
            )

            if analyze_clicked:
                with st.spinner("Analyzing unit photographs with Groq AI (qwen/qwen3.8-27b)..."):
                    try:
                        month_dir = INSPECTION_DIR / current_month
                        saved_images = []
                        valid_paths = []

                        for idx, f in enumerate(active_files):
                            is_valid, msg = validate_image(f)
                            if not is_valid:
                                st.error(f"Image {f.name} error: {msg}")
                                st.stop()

                            f_bytes = f.getvalue()
                            path, fname, sz = save_image_to_disk(
                                file_bytes=f_bytes,
                                original_name=f.name,
                                target_dir=month_dir,
                                prefix=f"tenant_{tenant_id}"
                            )
                            saved_images.append({
                                "path": path,
                                "filename": fname,
                                "size": sz,
                                "type": image_type_selections[idx]
                            })
                            valid_paths.append(path)

                        # Call Groq multimodal inspection
                        ai_result = analyze_room_inspection(
                            current_image_paths=valid_paths,
                            image_types=image_type_selections,
                            tenant_name=user["full_name"],
                            room_number=room_number,
                            api_key=api_key
                        )

                        # Save to database pipeline
                        new_inspection_id = save_inspection_pipeline(
                            tenant_id=tenant_id,
                            room_id=room_id,
                            month_year=current_month,
                            saved_images=saved_images,
                            ai_result=ai_result
                        )

                        st.session_state["latest_inspection_id"] = new_inspection_id
                        st.session_state["latest_ai_result"] = ai_result
                        st.success("Analysis complete and recorded. Review the breakdown below.")

                    except Exception as e:
                        st.error(f"AI Inspection Error: {str(e)}")

        # Immediate display of evaluation
        active_display_result = st.session_state.get("latest_ai_result")
        if active_display_result:
            cleanliness = active_display_result.get("cleanliness", {})
            score = cleanliness.get("overall_score", 0.0)
            score_color = get_score_color(score)
            res_cat = cleanliness.get("result_category", "Good")
            damage_alerts = active_display_result.get("damage_alerts", [])

            st.markdown("---")
            st.markdown("### Inspection Evaluation")

            res_c1, res_c2, res_c3 = st.columns([1, 1, 1])
            with res_c1:
                st.metric(
                    label="Cleanliness Score",
                    value=f"{score} / 100",
                    delta=res_cat
                )
            with res_c2:
                disc_pct = 10.0 if score >= 90 else (5.0 if score >= 80 else (2.0 if score >= 70 else 0.0))
                st.metric(
                    label="Eligible Rent Discount",
                    value=f"{disc_pct}% OFF",
                    delta="Eligible for Approval" if disc_pct > 0 else "Below 70 threshold"
                )
            with res_c3:
                st.metric(
                    label="Property Integrity Alerts",
                    value=len(damage_alerts),
                    delta="All Clear" if len(damage_alerts) == 0 else "Action Required",
                    delta_color="off" if len(damage_alerts) == 0 else "inverse"
                )

            # Observations and Recommendations
            o_col1, o_col2 = st.columns(2)
            with o_col1:
                st.html(f"""<div style="background-color: #FFFFFF; border: 1px solid #E3D7CE; border-left: 4px solid #AB7843; padding: 16px 18px; border-radius: 10px; margin-bottom: 14px; box-shadow: 0 1px 2px rgba(53,39,30,0.03);">
                    <div style="font-weight: 700; color: #6D3914; font-size: 0.92rem; margin-bottom: 6px;">Positive Observations</div>
                    <div style="font-size: 0.88rem; color: #35271E; line-height: 1.5;">{cleanliness.get('positive_observations', 'Well maintained space.')}</div>
                </div>""")

            with o_col2:
                st.html(f"""<div style="background-color: #FFFFFF; border: 1px solid #E3D7CE; border-left: 4px solid #4C2B08; padding: 16px 18px; border-radius: 10px; margin-bottom: 14px; box-shadow: 0 1px 2px rgba(53,39,30,0.03);">
                    <div style="font-weight: 700; color: #6D3914; font-size: 0.92rem; margin-bottom: 6px;">Areas for Improvement & Advice</div>
                    <div style="font-size: 0.88rem; color: #35271E; line-height: 1.5;">
                        <strong style="color: #4C2B08;">Focus:</strong> {cleanliness.get('areas_for_improvement', 'Continue consistent routine.')}<br>
                        <strong style="color: #4C2B08;">Recommendation:</strong> {cleanliness.get('recommendations', 'Regularly wipe surfaces and keep floor swept.')}
                    </div>
                </div>""")

            # Category scores breakdown
            cat_scores = cleanliness.get("category_scores", [])
            if cat_scores:
                st.markdown("##### Category Breakdown")
                cat_cols = st.columns(min(len(cat_scores), 3))
                for c_idx, cs in enumerate(cat_scores):
                    target_col = cat_cols[c_idx % len(cat_cols)]
                    with target_col:
                        c_score = cs.get("score", score)
                        c_col_code = get_score_color(c_score)
                        st.html(f"""<div style="padding: 12px 14px; background: #FFFFFF; border: 1px solid #E3D7CE; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(53,39,30,0.03);">
                            <div style="font-weight: 600; font-size: 0.85rem; color: #35271E;">{cs.get('category')}</div>
                            <div style="color: {c_col_code}; font-weight: 800; font-size: 1.15rem; margin: 2px 0;">{c_score} / 100</div>
                            <div style="color: #8C7465; font-size: 0.8rem; line-height: 1.3;">{cs.get('notes', '')}</div>
                        </div>""")

            # Property damage findings (if any)
            if damage_alerts:
                st.markdown("##### Suspected Property Damage Findings")
                for da in damage_alerts:
                    st.warning(
                        f"**{da.get('damage_category', 'Damage')}** (Severity: {da.get('severity', 'Medium')} | Confidence: {float(da.get('confidence', 0.8))*100:.0f}%)\n\n"
                        f"{da.get('description', '')}\n\n"
                        f"*Action:* {da.get('recommended_action', 'Owner visual inspection suggested')}"
                    )

    with tab_history:
        st.subheader("Historical Inspection Records")
        inspections = database.get_tenant_inspections(tenant_id)

        if not inspections:
            st.info("No prior inspections recorded.")
        else:
            for insp in inspections:
                score = insp.get("overall_score") or 0.0
                color = get_score_color(score)
                with st.expander(
                    f"Report: {insp['month_year']} (Submitted {format_date(insp['submission_date'])}) — Score: {score}/100 ({insp['result_category']})",
                    expanded=False
                ):
                    col_sc, col_notes = st.columns([1, 2])
                    with col_sc:
                        st.html(f"""<div style="background-color: #FFFFFF; padding: 18px; border-radius: 10px; text-align: center; border: 2px solid {color}; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(53,39,30,0.03);">
                            <h2 style="color: {color}; margin: 0; font-weight: 800;">{score}</h2>
                            <p style="margin: 0; font-weight: 700; color: #35271E;">{insp['result_category']}</p>
                            <p style="font-size: 0.8rem; color: #8C7465; margin-top: 4px;">{format_date(insp['submission_date'])}</p>
                        </div>""")

                        cat_scores = database.get_cleanliness_scores(insp["id"])
                        if cat_scores:
                            st.markdown("##### Category Scores")
                            for cs in cat_scores:
                                st.write(f"• **{cs['category']}**: `{cs['score']}/100`")

                    with col_notes:
                        st.markdown(f"**Positive Observations:**\n{insp.get('positive_observations', 'Clean and tidy.')}")
                        st.markdown(f"**Areas for Improvement:**\n{insp.get('areas_for_improvement', 'None detected.')}")
                        st.markdown(f"**Cleaning Advice:**\n{insp.get('recommendations', 'Maintain routine cleanliness.')}")

                    photos = database.get_inspection_images(insp["id"])
                    if photos:
                        st.markdown("##### Submitted Images")
                        p_cols = st.columns(min(len(photos), 3))
                        for p_idx, p in enumerate(photos):
                            c_idx = p_idx % min(len(photos), 3)
                            with p_cols[c_idx]:
                                if Path(p["file_path"]).exists():
                                    st.image(p["file_path"], caption=p["image_type"], use_container_width=True)
                                else:
                                    st.caption(f"{p['image_type']} (archived)")


def _render_owner_inspection(user):
    st.caption("Review monthly AI cleanliness scores, inspect uploaded photographs, and monitor tenant property upkeep.")

    months = get_month_options(past_months=6, future_months=1)
    current_m = get_current_month_str()
    default_idx = months.index(current_m) if current_m in months else 0

    col_m, col_filter = st.columns([1.5, 2])
    with col_m:
        sel_month = st.selectbox("Inspection Month", options=["All"] + months, index=1)
    with col_filter:
        sel_status = st.selectbox("Filter Result", ["All", "Excellent", "Good", "Average", "Needs Improvement"])

    filter_m = None if sel_month == "All" else sel_month
    inspections = database.get_all_inspections(filter_m)

    if sel_status != "All":
        inspections = [i for i in inspections if i.get("result_category") == sel_status]

    if not inspections:
        st.info("No inspection submissions found.")
        return

    scores = [i["overall_score"] for i in inspections if i.get("overall_score")]
    avg_sc = sum(scores) / len(scores) if scores else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("Inspections Submitted", len(inspections))
    m2.metric("Average Score", f"{avg_sc:.1f} / 100")
    m3.metric("Reward Eligible", sum(1 for i in inspections if i.get("reward_eligible")))

    st.markdown("---")

    for insp in inspections:
        score = insp.get("overall_score") or 0.0
        color = get_score_color(score)
        with st.expander(
            f"Unit {insp['room_number']} — {insp['tenant_name']} | Cycle: {insp['month_year']} | Score: {score}/100 ({insp['result_category']})",
            expanded=False
        ):
            c_info, c_action = st.columns([2.5, 1])

            with c_info:
                st.markdown(f"""
                - **Resident:** `{insp['tenant_name']}`
                - **Unit:** `{insp['room_number']}`
                - **Date Submitted:** {format_date(insp['submission_date'])}
                - **Rating:** <span style="color: {color}; font-weight: 700;">{score} / 100 ({insp['result_category']})</span>
                - **Eligible for Discount:** `{'Yes (Score >= 70)' if insp['reward_eligible'] else 'No'}`
                """, unsafe_allow_html=True)

                st.markdown(f"**Feedback:** {insp.get('positive_observations', 'N/A')}")
                st.markdown(f"**Improvement Areas:** {insp.get('areas_for_improvement', 'N/A')}")
                st.markdown(f"**Recommendations:** {insp.get('recommendations', 'N/A')}")

                cat_scores = database.get_cleanliness_scores(insp["id"])
                if cat_scores:
                    st.markdown("##### Category Breakdown:")
                    for cs in cat_scores:
                        st.caption(f"• **{cs['category']}**: `{cs['score']}/100` — {cs.get('notes', '')}")

            with c_action:
                st.markdown("##### Administrative Action")
                if st.button("Request Resubmission", key=f"resub_{insp['id']}"):
                    database.execute_query(
                        "UPDATE inspections SET status = 'Resubmission Requested' WHERE id = ?;",
                        (insp["id"],),
                        commit=True
                    )
                    st.warning("Resubmission requested from resident.")
                    st.rerun()

            photos = database.get_inspection_images(insp["id"])
            if photos:
                st.markdown("##### Submitted Images")
                p_cols = st.columns(min(len(photos), 3))
                for p_idx, p in enumerate(photos):
                    c_idx = p_idx % min(len(photos), 3)
                    with p_cols[c_idx]:
                        if Path(p["file_path"]).exists():
                            st.image(p["file_path"], caption=p["image_type"], use_container_width=True)
                        else:
                            st.caption(f"{p['image_type']} (archived)")


if __name__ == "__main__" or True:
    render_ai_inspection()

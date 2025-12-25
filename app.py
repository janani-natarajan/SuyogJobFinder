# --------------------------- 1. Imports ---------------------------
import streamlit as st
import pandas as pd
import requests
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap

# --------------------------- 2. Load Dataset ---------------------------
df = pd.read_json("cleaned_data.jsonl", lines=True)

# ---- REMOVE TIMESTAMP / DATE COLUMNS GLOBALLY ----
df = df.loc[:, ~df.columns.str.contains("time|date", case=False)]

if df.empty:
    st.stop()

# --------------------------- 3. Options ---------------------------
disabilities = [
    "Visual Impairment", "Hearing Impairment", "Physical Disabilities",
    "Neurological Disabilities", "Blood Disorders",
    "Intellectual and Developmental Disabilities", "Mental Illness", "Multiple Disabilities"
]

intellectual_subcategories = [
    "Autism Spectrum Disorder (ASD M)",
    "Autism Spectrum Disorder (ASD MoD)",
    "Intellectual Disability (ID)",
    "Specific Learning Disability (SLD)",
    "Mental Illness"
]

qualifications = [
    "10th Standard", "12th Standard", "Certificate", "Diploma",
    "Graduate", "Post Graduate", "Doctorate"
]

departments = df.get("department")
departments = departments.dropna().unique().tolist() if departments is not None else []

activities = [
    "S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting",
    "PP Pulling & Pushing", "KC Kneeling & Crouching",
    "MF Manipulation with Fingers", "RW Reading & Writing",
    "SE Seeing", "H Hearing", "C Communication"
]

# --------------------------- 4. Helper Functions ---------------------------
def map_group(qualification):
    q = qualification.strip().lower() if qualification else ""
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    elif q == "12th standard":
        return ["Group C", "Group D"]
    elif q:
        return ["Group D"]
    return []

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()

    if disability:
        d = disability.lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(d, na=False)
        df_filtered = df_filtered[mask] if mask.any() else df_filtered

    if subcategory:
        s = subcategory.lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(s, na=False)
        df_filtered = df_filtered[mask] if mask.any() else df_filtered

    allowed_groups = map_group(qualification)
    if allowed_groups and "group" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["group"].isin(allowed_groups)]

    if department and "department" in df_filtered.columns:
        df_filtered = df_filtered[
            df_filtered["department"].astype(str).str.lower().str.contains(department.lower(), na=False)
        ]

    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = (
            df_filtered["functional_requirements"]
            .astype(str).str.upper()
        )
        selected = [a.split()[0].upper() for a in activities]
        df_filtered = df_filtered[
            df_filtered["functional_norm"].apply(lambda x: any(a in x for a in selected))
        ]

    return df_filtered.reset_index(drop=True)

def generate_pdf_tabulated(jobs_df):
    jobs_df = jobs_df.loc[:, ~jobs_df.columns.str.contains("time|date", case=False)]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3)
    elements = []
    styles = getSampleStyleSheet()

    title = ParagraphStyle("title", fontSize=18, alignment=1)
    h2 = ParagraphStyle("h2", fontSize=14, textColor=colors.darkblue)
    h3 = ParagraphStyle("h3", fontSize=12)
    text = ParagraphStyle("text", fontSize=11)

    elements.append(Paragraph("Suyog+", title))
    elements.append(Paragraph("By DAIL NIEPMD", title))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", h2))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        elements.append(Paragraph(f"Designation: {job.get('designation','-')}", h2))
        elements.append(Paragraph(f"Group: {job.get('group','-')}", h3))
        elements.append(Paragraph(f"Department: {job.get('department','-')}", h3))
        elements.append(Spacer(1, 10))

        fields = [
            ("Qualification Required", job.get("qualification_required", "-")),
            ("Functional Requirements", job.get("functional_requirements", "-")),
            ("Nature of Work", job.get("nature_of_work", "-")),
            ("Working Conditions", job.get("working_conditions", "-")),
        ]

        for k, v in fields:
            wrapped = "<br/>".join(wrap(str(v), 100))
            elements.append(Paragraph(f"<b>{k}:</b> {wrapped}", text))

        elements.append(Spacer(1, 25))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------- 5. Streamlit UI ---------------------------
st.title("Suyog+ Job Finder")
st.markdown("Find suitable jobs for persons with disabilities in India.")

disability = st.selectbox("Select your type of disability:", disabilities)

subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.selectbox("Select the subcategory:", intellectual_subcategories)

qualification = st.selectbox("Select highest qualification:", qualifications)

department = st.selectbox("Select department:", departments) if departments else None

selected_activities = st.multiselect("Select functional activities:", activities)

if st.button("Find Jobs"):
    results = filter_jobs(disability, subcategory, qualification, department, selected_activities)

    if results.empty:
        st.warning("😞 Sorry, no jobs matched your profile.")
    else:
        st.success(f"✅ {len(results)} job(s) matched your profile.")
        st.dataframe(results)

        pdf = generate_pdf_tabulated(results)
        st.download_button(
            "Download PDF of Jobs",
            data=pdf,
            file_name="job_matches.pdf",
            mime="application/pdf"
        )

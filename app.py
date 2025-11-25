# app.py - Suyog+ Job Finder (Web Version with Activity Buttons)

import streamlit as st
import pandas as pd
import requests
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap

st.set_page_config(page_title="Suyog+ Job Finder", layout="wide")

# ---------------------------
# 1. GitHub raw file URL
# ---------------------------
GITHUB_URL = "https://raw.githubusercontent.com/janani-natarajan/SuyogJobFinder/main/cleaned_data.jsonl"

# ---------------------------
# 2. Load dataset
# ---------------------------
@st.cache_data(show_spinner=True)
def load_dataset(url):
    r = requests.get(url)
    r.raise_for_status()
    df = pd.read_json(io.BytesIO(r.content), lines=True)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    return df

df = load_dataset(GITHUB_URL)
if df.empty:
    st.stop()
st.success(f"Dataset loaded: {len(df)} records")

# ---------------------------
# 3. Options
# ---------------------------
disabilities = [
    "Visual Impairment", "Hearing Impairment", "Physical Disabilities",
    "Neurological Disabilities", "Blood Disorders",
    "Intellectual and Developmental Disabilities",
    "Mental Illness", "Multiple Disabilities"
]

intellectual_subcategories = [
    "Autism Spectrum Disorder (ASD M)",
    "Autism Spectrum Disorder (ASD MoD)",
    "Intellectual Disability (ID)",
    "Specific Learning Disability (SLD)",
    "Mental Illness"
]

qualifications = ["10th Standard", "12th Standard", "Certificate", "Diploma",
                  "Graduate", "Post Graduate", "Doctorate"]

departments = sorted(df["department"].dropna().astype(str).unique().tolist()) if "department" in df.columns else []

activities = [
    "S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting",
    "PP Pulling & Pushing", "KC Kneeling & Crouching",
    "MF Manipulation with Fingers", "RW Reading & Writing",
    "SE Seeing", "H Hearing", "C Communication"
]

# ---------------------------
# 4. Helper functions
# ---------------------------
def map_group(qualification):
    q = qualification.strip().lower() if isinstance(qualification, str) else ""
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    elif q == "12th standard":
        return ["Group C", "Group D"]
    elif q == "10th standard":
        return ["Group D"]
    else:
        return ["Group D"]

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities_sel=None):
    df_filtered = df.copy()

    if disability:
        d = disability.strip().lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabil" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(d, regex=False, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    if subcategory:
        sub = subcategory.strip().lower()
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcat" in col.lower() or "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.lower().str.contains(sub, regex=False, na=False)
        if mask_sub.any():
            df_filtered = df_filtered[mask_sub]

    if qualification and "group" in df_filtered.columns:
        allowed = map_group(qualification)
        mask_g = df_filtered["group"].astype(str).str.strip().isin(allowed)
        if mask_g.any():
            df_filtered = df_filtered[mask_g]

    if department and "department" in df_filtered.columns:
        dep = department.strip().lower()
        mask_dep = df_filtered["department"].astype(str).str.lower().str.contains(dep, regex=False, na=False)
        if mask_dep.any():
            df_filtered = df_filtered[mask_dep]

    if activities_sel and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper().str.replace(r'[^A-Z ]', '', regex=True)
        selected_norm = [a.split()[0].upper() for a in activities_sel]
        mask_act = df_filtered["functional_norm"].apply(lambda fr: any(a in fr for a in selected_norm))
        if mask_act.any():
            df_filtered = df_filtered[mask_act]

    return df_filtered.reset_index(drop=True)

def generate_pdf_tabulated(jobs_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=5, fontSize=18)
    style_heading2 = ParagraphStyle('Heading2', parent=styles['Heading2'], spaceAfter=10, fontSize=14, textColor=colors.darkblue)
    style_heading3 = ParagraphStyle('Heading3', parent=styles['Heading3'], spaceAfter=8, fontSize=13, textColor=colors.darkgreen)
    style_text = ParagraphStyle('Text', parent=styles['Normal'], spaceAfter=10, fontSize=11, leading=15)

    elements.append(Paragraph("Suyog+ — Job Matches", style_title))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", styles['Heading2']))
    elements.append(Spacer(1, 15))

    for _, job in jobs_df.iterrows():
        designation = str(job.get('designation', '-')).capitalize()
        group = str(job.get('group', '-')).capitalize()
        department = str(job.get('department', '-')).capitalize()

        elements.append(Paragraph(f"Designation: {designation}", style_heading2))
        elements.append(Paragraph(f"Group: {group}", style_heading3))
        elements.append(Paragraph(f"Department: {department}", style_heading3))
        elements.append(Spacer(1, 8))

        job_data = [
            ("Qualification Required", job.get('qualification_required', '-')),
            ("Functional Requirements", job.get('functional_requirements', '-')),
            ("Nature of Work", job.get('nature_of_work', '-')),
            ("Working Conditions", job.get('working_conditions', '-'))
        ]
        for field, value in job_data:
            wrapped_lines = "<br/>".join(wrap(str(value), 100))
            elements.append(Paragraph(f"<b>{field}:</b> {wrapped_lines}", style_text))
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("<hr/>", style_text))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---------------------------
# 5. UI
# ---------------------------
st.title("Suyog+ Job Finder (Web Version)")

# Session state for selected activities
if "selected_activities" not in st.session_state:
    st.session_state.selected_activities = []

with st.sidebar:
    disability = st.selectbox("Select disability type", disabilities)
    subcategory = None
    if disability == "Intellectual and Developmental Disabilities":
        subcategory = st.selectbox("Select subcategory", intellectual_subcategories)
    qualification = st.selectbox("Select highest qualification", qualifications)
    if departments:
        department = st.selectbox("Select department", departments)
    else:
        department = st.text_input("Department (free text)")

    st.write("### Select Functional Activities:")
    cols = st.columns(3)
    for idx, act in enumerate(activities):
        col = cols[idx % 3]
        if col.button(f"{'✅ ' if act in st.session_state.selected_activities else ''}{act}", key=act):
            if act in st.session_state.selected_activities:
                st.session_state.selected_activities.remove(act)
            else:
                st.session_state.selected_activities.append(act)

    if st.button("Done ✅"):
        if not st.session_state.selected_activities:
            st.warning("Please select at least one activity.")
        else:
            results = filter_jobs(
                disability=disability,
                subcategory=subcategory,
                qualification=qualification,
                department=department,
                activities_sel=st.session_state.selected_activities
            )
            if results.empty:
                st.warning("😞 No jobs matched your profile.")
            else:
                st.success(f"✅ {len(results)} job(s) found!")
                pdf_buf = generate_pdf_tabulated(results)
                st.download_button("Download job matches (PDF)", pdf_buf, file_name="job_matches.pdf", mime="application/pdf")
                st.dataframe(results)

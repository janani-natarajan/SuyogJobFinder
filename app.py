import streamlit as st
import pandas as pd
import requests
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap
from gtts import gTTS

# --------------------------- 1. Fetch Dataset from GitHub ---------------------------
GITHUB_URL = "https://raw.githubusercontent.com/janani-natarajan/SuyogJobFinder/main/cleaned_data.jsonl"

@st.cache_data
def load_dataset(url):
    r = requests.get(url)
    r.raise_for_status()
    df = pd.read_json(io.StringIO(r.text), lines=True)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    return df

df = load_dataset(GITHUB_URL)
if df.empty:
    st.error("❌ Dataset could not be loaded.")
    st.stop()

# --------------------------- 2. Options ---------------------------
disabilities = ["Visual Impairment", "Hearing Impairment", "Physical Disabilities",
                "Neurological Disabilities", "Blood Disorders",
                "Intellectual and Developmental Disabilities",
                "Mental Illness", "Multiple Disabilities"]

intellectual_subcategories = [
    "Autism Spectrum Disorder (ASD M)",
    "Autism Spectrum Disorder (ASD MoD)",
    "Intellectual Disability (ID)",
    "Specific Learning Disability (SLD)",
    "Mental Illness"
]

qualifications = ["10th Standard", "12th Standard", "Certificate", "Diploma",
                  "Graduate", "Post Graduate", "Doctorate"]

departments = df["department"].dropna().unique().tolist()

activities = ["S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting", "PP Pulling & Pushing",
              "KC Kneeling & Crouching", "MF Manipulation with Fingers", "RW Reading & Writing",
              "SE Seeing", "H Hearing", "C Communication"]

# --------------------------- 3. Helper Functions ---------------------------
def map_group(qualification):
    q = qualification.strip().lower()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    elif q == "12th standard":
        return ["Group C", "Group D"]
    elif q == "10th standard":
        return ["Group D"]
    else:
        return ["Group D"]

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities_selected=None):
    df_filtered = df.copy()
    if disability:
        d = disability.strip().lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(d, regex=False, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]
    if subcategory:
        sub_lower = subcategory.strip().lower()
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.lower().str.contains(sub_lower, regex=False, na=False)
        if mask_sub.any():
            df_filtered = df_filtered[mask_sub]
    allowed_groups = map_group(qualification) if qualification else []
    if allowed_groups and "group" in df_filtered.columns:
        mask_group = df_filtered["group"].astype(str).str.strip().isin(allowed_groups)
        if mask_group.any():
            df_filtered = df_filtered[mask_group]
    if department:
        dep_lower = department.strip().lower()
        if "department" in df_filtered.columns:
            mask_dep = df_filtered["department"].astype(str).str.lower().str.contains(dep_lower, regex=False, na=False)
            if mask_dep.any():
                df_filtered = df_filtered[mask_dep]
    if activities_selected and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper().str.replace(r'[^A-Z ]', '', regex=True)
        selected_norm = [a.split()[0].upper() for a in activities_selected]
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
    style_text = ParagraphStyle('Text', parent=styles['Normal'], spaceAfter=10, fontSize=11, leading=15)
    elements.append(Paragraph('<font color="darkblue">Suyog+</font>', style_title))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", styles['Heading1']))
    elements.append(Spacer(1, 20))
    for _, job in jobs_df.iterrows():
        designation = str(job.get('designation', '-')).capitalize()
        group = str(job.get('group', '-')).capitalize()
        department = str(job.get('department', '-')).capitalize()
        elements.append(Paragraph(f"Designation: {designation}", style_heading2))
        job_data = [
            ("Qualification Required", job.get('qualification_required', '-')),
            ("Functional Requirements", job.get('functional_requirements', '-'))
        ]
        for field, value in job_data:
            wrapped_lines = "<br/>".join(wrap(str(value).capitalize(), 100))
            elements.append(Paragraph(f"<b>{field}:</b> {wrapped_lines}", style_text))
        elements.append(Spacer(1, 15))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------- 4. Streamlit UI ---------------------------
st.set_page_config(page_title="Suyog+ Job Finder", layout="wide")
st.title("👋 Suyog+ Job Finder")

if "step" not in st.session_state:
    st.session_state.step = 0
    st.session_state.answers = {}

# Step 0: Disability
if st.session_state.step == 0:
    st.session_state.answers["disability"] = st.selectbox("Select your type of disability:", disabilities)
    if st.button("Next"):
        if st.session_state.answers["disability"] == "Intellectual and Developmental Disabilities":
            st.session_state.step = 0.5
        else:
            st.session_state.step = 1
        st.experimental_rerun()

# Step 0.5: Subcategory
elif st.session_state.step == 0.5:
    st.session_state.answers["subcategory"] = st.selectbox("Select subcategory:", intellectual_subcategories)
    if st.button("Next"):
        st.session_state.step = 1
        st.experimental_rerun()

# Step 1: Qualification
elif st.session_state.step == 1:
    st.session_state.answers["qualification"] = st.selectbox("Select highest qualification:", qualifications)
    if st.button("Next"):
        st.session_state.step = 2
        st.experimental_rerun()

# Step 2: Department
elif st.session_state.step == 2:
    st.session_state.answers["department"] = st.selectbox("Select department:", departments)
    if st.button("Next"):
        st.session_state.step = 3
        st.experimental_rerun()

# Step 3: Activities
elif st.session_state.step == 3:
    st.session_state.answers["activities"] = st.multiselect("Select functional activities:", activities)
    if st.button("Find Jobs"):
        df_results = filter_jobs(
            disability=st.session_state.answers.get("disability"),
            subcategory=st.session_state.answers.get("subcategory"),
            qualification=st.session_state.answers.get("qualification"),
            department=st.session_state.answers.get("department"),
            activities_selected=st.session_state.answers.get("activities")
        )
        if df_results.empty:
            st.warning("😞 Sorry, no jobs matched your profile.")
        else:
            st.success(f"✅ Found {len(df_results)} jobs matching your profile.")
            st.dataframe(df_results)
            pdf_buffer = generate_pdf_tabulated(df_results)
            st.download_button("📄 Download Job Matches PDF", pdf_buffer, file_name="job_matches.pdf", mime="application/pdf")

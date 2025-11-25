# --------------------------- 1. Install packages ---------------------------
# !pip install pandas reportlab gtts requests streamlit

# --------------------------- 2. Imports ---------------------------
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
import tempfile

# --------------------------- 3. Load Dataset from GitHub ---------------------------
GITHUB_URL = "https://raw.githubusercontent.com/janani-natarajan/SuyogJobFinder/main/cleaned_data.jsonl"

@st.cache_data(show_spinner=True)
def load_dataset(url):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        df = pd.read_json(io.StringIO(r.text), lines=True)
        # Clean string columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        st.error(f"Failed to load dataset: {e}")
        st.stop()
        return pd.DataFrame()

df = load_dataset(GITHUB_URL)
st.success(f"✅ Dataset loaded: {len(df)} records")

# --------------------------- 4. Options ---------------------------
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

# --------------------------- 5. Helper Functions ---------------------------
def map_group(qualification):
    q = qualification.strip().lower()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    elif q == "12th standard":
        return ["Group C", "Group D"]
    else:
        return ["Group D"]

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()

    if disability:
        d = disability.strip().lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(d, regex=False, na=False)
        df_filtered = df_filtered[mask] if mask.any() else df_filtered

    if subcategory:
        sub_lower = subcategory.strip().lower()
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.lower().str.contains(sub_lower, regex=False, na=False)
        df_filtered = df_filtered[mask_sub] if mask_sub.any() else df_filtered

    if qualification:
        allowed_groups = map_group(qualification)
        if "group" in df_filtered.columns:
            mask_group = df_filtered["group"].astype(str).str.strip().isin(allowed_groups)
            df_filtered = df_filtered[mask_group] if mask_group.any() else df_filtered

    if department:
        dep_lower = department.strip().lower()
        if "department" in df_filtered.columns:
            mask_dep = df_filtered["department"].astype(str).str.lower().str.contains(dep_lower, regex=False, na=False)
            df_filtered = df_filtered[mask_dep] if mask_dep.any() else df_filtered

    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper().str.replace(r'[^A-Z ]', '', regex=True)
        selected_norm = [a.split()[0].upper() for a in activities]
        mask_act = df_filtered["functional_norm"].apply(lambda fr: any(a in fr for a in selected_norm))
        df_filtered = df_filtered[mask_act] if mask_act.any() else df_filtered

    return df_filtered.reset_index(drop=True)

def generate_pdf_tabulated(jobs_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=5, fontSize=18)
    style_heading2 = ParagraphStyle('Heading2', parent=styles['Heading2'], spaceAfter=10, fontSize=14, textColor=colors.darkblue)
    style_text = ParagraphStyle('Text', parent=styles['Normal'], spaceAfter=10, fontSize=11, leading=15)

    elements.append(Paragraph('<font color="darkblue">Suyog</font><font color="maroon">+</font>', style_title))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", styles['Heading1']))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        designation = str(job.get('designation', '-')).capitalize()
        group = str(job.get('group', '-')).capitalize()
        department = str(job.get('department', '-')).capitalize()
        elements.append(Paragraph(f"Designation: {designation}", style_heading2))
        elements.append(Paragraph(f"Group: {group}", style_heading2))
        elements.append(Paragraph(f"Department: {department}", style_heading2))
        elements.append(Spacer(1, 10))
        for field in ["qualification_required", "functional_requirements", "nature_of_work", "working_conditions"]:
            value = job.get(field, "-")
            wrapped_lines = "<br/>".join(wrap(str(value).capitalize(), 100))
            elements.append(Paragraph(f"<b>{field.replace('_',' ').title()}:</b> {wrapped_lines}", style_text))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("<hr/>", style_text))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------- 6. Streamlit UI ---------------------------
st.title("👨‍💼 Suyog+ Job Finder for Persons with Disabilities")

with st.form("job_filter_form"):
    disability = st.selectbox("Select your type of disability:", disabilities)
    subcategory = None
    if disability == "Intellectual and Developmental Disabilities":
        subcategory = st.selectbox("Select subcategory:", intellectual_subcategories)
    qualification = st.selectbox("Select highest qualification:", qualifications)
    department = st.selectbox("Select department:", departments)
    activities_selected = st.multiselect("Select functional activities:", activities)
    submitted = st.form_submit_button("Find Jobs")

if submitted:
    df_results = filter_jobs(disability, subcategory, qualification, department, activities_selected)
    if df_results.empty:
        st.warning("😞 Sorry, no jobs matched your profile.")
    else:
        st.success(f"✅ {len(df_results)} jobs matched your profile!")

        # Show table
        st.dataframe(df_results)

        # Generate PDF and provide download
        pdf_buffer = generate_pdf_tabulated(df_results)
        st.download_button("📄 Download Job Matches PDF", pdf_buffer, file_name="job_matches.pdf")

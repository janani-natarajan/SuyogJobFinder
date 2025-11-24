# --------------------------- 1. Install packages ---------------------------
!pip install streamlit pandas reportlab gtts pydub

# --------------------------- 2. Imports ---------------------------
import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap
from gtts import gTTS

# --------------------------- 3. Load Dataset from GitHub ---------------------------
DATA_URL = "https://raw.githubusercontent.com/janani-natarajan/SuyogJobFinder/main/cleaned_data.jsonl"

@st.cache_data
def load_data(url):
    df = pd.read_json(url, lines=True)
    # Clean and normalize
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    return df

df = load_data(DATA_URL)
st.success(f"✅ Dataset loaded: {len(df)} job records")

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
    elif q == "10th standard":
        return ["Group D"]
    else:
        return ["Group D"]

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()

    # --- Disability filter ---
    if disability:
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.contains(disability, case=False, regex=False, na=False)
        df_filtered = df_filtered[mask]

    # --- Subcategory filter ---
    if subcategory:
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.contains(subcategory, case=False, regex=False, na=False)
        df_filtered = df_filtered[mask_sub]

    # --- Qualification / Group filter ---
    if qualification and "group" in df_filtered.columns:
        allowed_groups = map_group(qualification)
        df_filtered = df_filtered[df_filtered["group"].astype(str).str.strip().isin(allowed_groups)]

    # --- Department filter ---
    if department and "department" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["department"].astype(str).str.contains(department, case=False, regex=False)]

    # --- Activities filter ---
    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper()
        selected_norm = [a.upper() for a in activities]
        df_filtered = df_filtered[df_filtered["functional_norm"].apply(lambda fr: any(a in fr for a in selected_norm))]

    return df_filtered.reset_index(drop=True)

def generate_pdf_tabulated(jobs_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()

    style_title = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=5, fontSize=18)
    style_heading2 = ParagraphStyle('Heading2', parent=styles['Heading2'], spaceAfter=10, fontSize=14, textColor=colors.darkblue)
    style_heading3 = ParagraphStyle('Heading3', parent=styles['Heading3'], spaceAfter=8, fontSize=13, textColor=colors.darkgreen)
    style_heading4 = ParagraphStyle('Heading4', parent=styles['Heading4'], spaceAfter=6, fontSize=12, textColor=colors.darkred)
    style_text = ParagraphStyle('Text', parent=styles['Normal'], spaceAfter=10, fontSize=11, leading=15)

    title_html = '<font color="darkblue">Suyog</font><font color="maroon">+</font>'
    elements.append(Paragraph(title_html, style_title))
    elements.append(Paragraph('<font color="darkblue">By DAIL NIEPMD</font>', style_title))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", styles['Heading1']))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        designation = str(job.get('designation', '-')).capitalize()
        group = str(job.get('group', '-')).capitalize()
        department = str(job.get('department', '-')).capitalize()

        elements.append(Paragraph(f"Designation: {designation}", style_heading2))
        elements.append(Paragraph(f"Group: {group}", style_heading3))
        elements.append(Paragraph(f"Department: {department}", style_heading4))
        elements.append(Spacer(1, 10))

        job_data = [
            ("Qualification Required", job.get('qualification_required', '-')),
            ("Functional Requirements", job.get('functional_requirements', '-')),
            ("Disabilities Supported", " ".join([str(job.get(col, '')) for col in jobs_df.columns if "disabilities" in col.lower()])),
            ("Nature of Work", job.get('nature_of_work', '-')),
            ("Working Conditions", job.get('working_conditions', '-'))
        ]
        for field, value in job_data:
            wrapped_lines = "<br/>".join(wrap(str(value).capitalize(), 100))
            elements.append(Paragraph(f"<b>{field}:</b> {wrapped_lines}", style_text))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("<hr/>", style_text))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def send_tts(text):
    tts = gTTS(text=text, lang='en')
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    return audio_buffer

# --------------------------- 6. Streamlit Form ---------------------------
st.header("Find Jobs for Persons with Disabilities")

with st.form("user_form"):
    disability = st.selectbox("Select your type of disability:", disabilities)
    subcategory = None
    if disability == "Intellectual and Developmental Disabilities":
        subcategory = st.selectbox("Select the subcategory:", intellectual_subcategories)
    qualification = st.selectbox("Select highest qualification:", qualifications)
    department = st.selectbox("Select department:", departments)
    selected_activities = st.multiselect("Select functional activities:", activities)
    submitted = st.form_submit_button("Find Jobs")

    if submitted:
        df_results = filter_jobs(
            disability=disability,
            subcategory=subcategory,
            qualification=qualification,
            department=department,
            activities=selected_activities
        )

        st.write("Filtered jobs found:", len(df_results))  # debug info

        if df_results.empty:
            st.warning("😞 Sorry, no jobs matched your profile.")
            audio_file = send_tts("Sorry, no jobs matched your profile.")
            st.audio(audio_file, format="audio/mp3")
        else:
            pdf_buffer = generate_pdf_tabulated(df_results)
            st.success(f"✅ {len(df_results)} jobs matched your profile!")
            st.download_button("📄 Download Job Matches PDF", pdf_buffer, file_name="job_matches.pdf", mime="application/pdf")
            audio_file = send_tts(f"{len(df_results)} jobs matched your profile. PDF is ready for download.")
            st.audio(audio_file, format="audio/mp3")

import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from gtts import gTTS
import os
import json

# --------------------------- Load Dataset ---------------------------
file_path = "cleaned_data.jsonl"
df = pd.read_json(file_path, lines=True)
for col in df.columns:
    if df[col].dtype == object:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

# --------------------------- Options ---------------------------
disabilities = [
    "Visual Impairment","Hearing Impairment","Physical Disabilities",
    "Neurological Disabilities","Blood Disorders","Intellectual and Developmental Disabilities",
    "Mental Illness","Multiple Disabilities"
]

intellectual_subcategories = [
    "Autism Spectrum Disorder (ASD M)",
    "Autism Spectrum Disorder (ASD MoD)",
    "Intellectual Disability (ID)",
    "Specific Learning Disability (SLD)",
    "Mental Illness"
]

qualifications = ["10th Standard","12th Standard","Certificate","Diploma",
"Graduate","Post Graduate","Doctorate"]

departments = df["department"].dropna().unique().tolist()

activities = [
    "S Sitting","ST Standing","W Walking","BN Bending","L Lifting","PP Pulling & Pushing",
    "KC Kneeling & Crouching","MF Manipulation with Fingers","RW Reading & Writing",
    "SE Seeing","H Hearing","C Communication"
]

# --------------------------- Helper Functions ---------------------------
def map_group(qualification):
    q = qualification.strip().lower()
    if q in ["graduate","post graduate","doctorate"]:
        return ["Group A","Group B","Group C","Group D"]
    elif q == "12th standard":
        return ["Group C","Group D"]
    else:
        return ["Group D"]

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()
    warnings = []

    # Filter by disability
    if disability:
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(disability.lower(), na=False)
        if mask.any():
            df_filtered = df_filtered[mask]
        else:
            warnings.append("No exact matches for selected disability.")

    # Filter by subcategory
    if subcategory:
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.lower().str.contains(subcategory.lower(), na=False)
        if mask_sub.any():
            df_filtered = df_filtered[mask_sub]
        else:
            warnings.append("No exact matches for selected subcategory.")

    # Filter by group
    allowed_groups = map_group(qualification) if qualification else []
    if allowed_groups and "group" in df_filtered.columns:
        mask_group = df_filtered["group"].astype(str).str.strip().isin(allowed_groups)
        if mask_group.any():
            df_filtered = df_filtered[mask_group]
        else:
            warnings.append("No jobs match your qualification group.")

    # Filter by department
    if department:
        mask_dep = df_filtered["department"].astype(str).str.lower().str.contains(department.lower(), na=False)
        if mask_dep.any():
            df_filtered = df_filtered[mask_dep]
        else:
            warnings.append("No jobs in the selected department.")

    # Filter by activities
    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper().str.replace(r'[^A-Z ]','', regex=True)
        selected_norm = [a.split()[0].upper() for a in activities]
        mask_act = df_filtered["functional_norm"].apply(lambda fr: any(a in fr for a in selected_norm))
        if mask_act.any() and mask_act.sum() > 0:
            df_filtered = df_filtered[mask_act]
        else:
            warnings.append("No jobs match all selected activities. Showing closest matches.")

    return df_filtered.reset_index(drop=True), warnings

def capitalize_first_letter(value):
    value = str(value).strip()
    if value != '-':
        return value[0].upper() + value[1:]
    return value

def generate_pdf_tabulated(jobs_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3)
    elements = []
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=5, fontSize=18)
    style_text = ParagraphStyle('Text', parent=styles['Normal'], spaceAfter=10, fontSize=11, leading=15)

    title_html = '<font color="darkblue">Suyog</font><font color="maroon">+</font>'
    elements.append(Paragraph(title_html, style_title))
    elements.append(Paragraph('<font color="darkblue">By DAIL NIEPMD</font>', style_title))
    elements.append(Spacer(1, 20))

    total_matches = len(jobs_df)
    elements.append(Paragraph(f"Total Matches: {total_matches}", style_text))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        elements.append(Paragraph(f"<b>Designation:</b> {capitalize_first_letter(job.get('designation','-'))}", style_text))
        elements.append(Paragraph(f"<b>Group:</b> {capitalize_first_letter(job.get('group','-'))}", style_text))
        elements.append(Paragraph(f"<b>Department:</b> {capitalize_first_letter(job.get('department','-'))}", style_text))
        elements.append(Paragraph(f"<b>Qualification Required:</b> {capitalize_first_letter(job.get('qualification_required','-'))}", style_text))
        elements.append(Paragraph(f"<b>Functional Requirements:</b> {capitalize_first_letter(job.get('functional_requirements','-'))}", style_text))
        elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------- Streamlit UI ---------------------------
st.set_page_config(page_title="Suyog+ Job Finder", page_icon="🧩", layout="centered")
st.title("🧩 Suyog+ Job Finder for Persons with Disabilities")
st.write("Find government-identified jobs suitable for persons with disabilities in India.")

disability = st.selectbox("Select your disability:", disabilities)
subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.selectbox("Select your subcategory:", intellectual_subcategories)
qualification = st.selectbox("Select your qualification:", qualifications)
department = st.selectbox("Select a department:", departments)
selected_activities = st.multiselect("Select your functional abilities:", activities)

if st.button("🔍 Find Jobs"):
    jobs, warnings = filter_jobs(disability, subcategory, qualification, department, selected_activities)
    
    if warnings:
        for w in warnings:
            st.warning(w)
    
    if len(jobs) == 0:
        st.error("❌ No exact matches found. Showing closest jobs below.")
        jobs = df.sample(min(10, len(df)))  # Show a few sample jobs as fallback
    else:
        st.success(f"✅ Found {len(jobs)} matching jobs.")

    pdf_buffer = generate_pdf_tabulated(jobs)
    st.download_button(label="📄 Download Results as PDF", data=pdf_buffer, file_name="suyog_jobs.pdf", mime="application/pdf")
    
    if st.checkbox("🔊 Read summary aloud"):
        tts = gTTS(f"Found {len(jobs)} matching jobs. Please check the PDF for details.", lang='en')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        st.audio(audio_buffer, format="audio/mp3")

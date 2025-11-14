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
    full_matches = []
    partial_matches = []

    for _, job in df.iterrows():
        score = 0
        total_criteria = 0

        # Disability
        if disability:
            total_criteria += 1
            if "disabilities" in job and pd.notna(job["disabilities"]):
                if disability.lower() in job["disabilities"].lower():
                    score += 1

        # Subcategory
        if subcategory:
            total_criteria += 1
            if "subcategory" in job and pd.notna(job["subcategory"]):
                if subcategory.lower() in job["subcategory"].lower():
                    score += 1

        # Qualification Group
        total_criteria += 1
        allowed_groups = map_group(qualification)
        if "group" in job and job["group"].strip() in allowed_groups:
            score += 1

        # Department
        if department:
            total_criteria += 1
            if "department" in job and pd.notna(job["department"]):
                if department.lower() in job["department"].lower():
                    score += 1

        # Activities
        if activities and "functional_requirements" in job:
            total_criteria += 1
            fr = job["functional_requirements"].upper() if pd.notna(job["functional_requirements"]) else ""
            selected_norm = [a.split()[0].upper() for a in activities]
            if any(a in fr for a in selected_norm):
                score += 1

        # Decide if full or partial match
        if score == total_criteria:
            full_matches.append(job)
        elif score > 0:
            partial_matches.append(job)

    full_df = pd.DataFrame(full_matches)
    partial_df = pd.DataFrame(partial_matches)
    return full_df.reset_index(drop=True), partial_df.reset_index(drop=True)

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
    full_jobs, partial_jobs = filter_jobs(disability, subcategory, qualification, department, selected_activities)
    
    if len(full_jobs) == 0 and len(partial_jobs) == 0:
        st.error("❌ No matching jobs found. Try selecting fewer filters or other criteria.")
    
    if len(full_jobs) > 0:
        st.success(f"✅ Full Matches: {len(full_jobs)}")
        st.dataframe(full_jobs)
    
    if len(partial_jobs) > 0:
        st.warning(f"⚠️ Partial Matches: {len(partial_jobs)}")
        st.dataframe(partial_jobs)
    
    # Generate PDF for all matches
    combined_jobs = pd.concat([full_jobs, partial_jobs], ignore_index=True)
    if len(combined_jobs) > 0:
        pdf_buffer = generate_pdf_tabulated(combined_jobs)
        st.download_button(
            label="📄 Download All Matching Jobs as PDF",
            data=pdf_buffer,
            file_name="suyog_jobs.pdf",
            mime="application/pdf"
        )
        if st.checkbox("🔊 Read summary aloud"):
            tts = gTTS(f"Found {len(combined_jobs)} matching jobs. Please check the PDF for details.", lang='en')
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            st.audio(audio_buffer, format="audio/mp3")

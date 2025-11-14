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
disabilities = ["Visual Impairment","Hearing Impairment","Physical Disabilities",
"Neurological Disabilities","Blood Disorders","Intellectual and Developmental Disabilities",
"Mental Illness","Multiple Disabilities"]

intellectual_subcategories = ["Autism Spectrum Disorder (ASD M)",
"Autism Spectrum Disorder (ASD MoD)","Intellectual Disability (ID)","Specific Learning Disability (SLD)",
"Mental Illness"]

qualifications = ["10th Standard","12th Standard","Certificate","Diploma",
"Graduate","Post Graduate","Doctorate"]

departments = df["department"].dropna().unique().tolist()

activities = ["S Sitting","ST Standing","W Walking","BN Bending","L Lifting","PP Pulling & Pushing",
"KC Kneeling & Crouching","MF Manipulation with Fingers","RW Reading & Writing",
"SE Seeing","H Hearing","C Communication"]

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
    match_info = []

    for _, job in df_filtered.iterrows():
        match = True
        reasons = []

        # Disability check
        if disability and "disabilities" in job:
            if disability.lower() not in str(job["disabilities"]).lower():
                match = False
                reasons.append("Disability mismatch")

        # Subcategory check
        if subcategory and "subcategory" in job:
            if subcategory.lower() not in str(job.get("subcategory", "")).lower():
                match = False
                reasons.append("Subcategory mismatch")

        # Qualification group
        if qualification and "group" in job:
            allowed_groups = map_group(qualification)
            if job["group"].strip() not in allowed_groups:
                match = False
                reasons.append("Group mismatch")

        # Department check
        if department and "department" in job:
            if department.lower() not in str(job["department"]).lower():
                match = False
                reasons.append("Department mismatch")

        # Functional abilities check
        if activities and "functional_requirements" in job:
            fr_norm = str(job["functional_requirements"]).upper()
            selected_norm = [a.split()[0].upper() for a in activities]
            if not any(a in fr_norm for a in selected_norm):
                match = False
                reasons.append("Functional abilities mismatch")

        job_copy = job.copy()
        job_copy["match"] = match
        job_copy["reasons"] = ", ".join(reasons)
        match_info.append(job_copy)

    return pd.DataFrame(match_info)

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

    # Title
    title_html = '<font color="darkblue">Suyog</font><font color="maroon">+</font>'
    elements.append(Paragraph(title_html, style_title))
    elements.append(Paragraph('<font color="darkblue">By DAIL NIEPMD</font>', style_title))
    elements.append(Spacer(1, 20))

    total_matches = len(jobs_df)
    elements.append(Paragraph(f"Total Jobs: {total_matches}", style_text))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        elements.append(Paragraph(f"<b>Designation:</b> {capitalize_first_letter(job.get('designation','-'))}", style_text))
        elements.append(Paragraph(f"<b>Group:</b> {capitalize_first_letter(job.get('group','-'))}", style_text))
        elements.append(Paragraph(f"<b>Department:</b> {capitalize_first_letter(job.get('department','-'))}", style_text))
        elements.append(Paragraph(f"<b>Qualification Required:</b> {capitalize_first_letter(job.get('qualification_required','-'))}", style_text))
        elements.append(Paragraph(f"<b>Functional Requirements:</b> {capitalize_first_letter(job.get('functional_requirements','-'))}", style_text))
        elements.append(Paragraph(f"<b>Match Status:</b> {'✅ Full Match' if job['match'] else '⚠️ Partial Match'}", style_text))
        if not job['match']:
            elements.append(Paragraph(f"<b>Reasons:</b> {job['reasons']}", style_text))
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
    jobs = filter_jobs(disability, subcategory, qualification, department, selected_activities)
    if len(jobs) == 0:
        st.error("❌ No matching jobs found. Try selecting fewer filters or other criteria.")
    else:
        full_matches = jobs[jobs['match'] == True]
        partial_matches = jobs[jobs['match'] == False]

        st.success(f"✅ Full Matches: {len(full_matches)}")
        st.info(f"⚠️ Partial Matches: {len(partial_matches)}")

        # Display results in a table
        st.dataframe(jobs[['designation','group','department','qualification_required','functional_requirements','match','reasons']])

        # Download PDF
        pdf_buffer = generate_pdf_tabulated(jobs)
        st.download_button(label="📄 Download Results as PDF", data=pdf_buffer, file_name="suyog_jobs.pdf", mime="application/pdf")

        # Read summary aloud
        if st.checkbox("🔊 Read summary aloud"):
            tts_text = f"Found {len(full_matches)} fully matching jobs and {len(partial_matches)} partially matching jobs. Please check the PDF for details."
            tts = gTTS(tts_text, lang='en')
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            st.audio(audio_buffer, format="audio/mp3")

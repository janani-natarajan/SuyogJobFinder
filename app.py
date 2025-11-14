import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from gtts import gTTS
import os
import json

# --------------------------- Check / Create Dataset ---------------------------
file_path = "cleaned_data.jsonl"

if not os.path.exists(file_path):
    sample_data = [
        {
            "designation": "Clerk",
            "group": "Group C",
            "department": "Administrative",
            "qualification_required": "12th Standard",
            "functional_requirements": "S Sitting, RW Reading & Writing, SE Seeing",
            "disabilities": "Visual Impairment"
        },
        {
            "designation": "Teacher",
            "group": "Group B",
            "department": "Education",
            "qualification_required": "Graduate",
            "functional_requirements": "S Sitting, ST Standing, H Hearing, C Communication",
            "disabilities": "Hearing Impairment"
        }
    ]
    with open(file_path, "w") as f:
        for item in sample_data:
            f.write(json.dumps(item) + "\n")

# --------------------------- Load Dataset ---------------------------
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

def filter_jobs_with_partial(disability=None, subcategory=None, qualification=None, department=None, activities=None):
    full_matches = []
    partial_matches = []
    
    for _, job in df.iterrows():
        score = 0
        total = 0

        # Disability check
        if disability:
            total += 1
            if disability.lower() in str(job.get('disabilities','')).lower():
                score += 1
        
        # Subcategory check
        if subcategory:
            total += 1
            if subcategory.lower() in str(job.get('subcategory','')).lower():
                score += 1
        
        # Qualification / group check
        if qualification:
            total += 1
            allowed_groups = map_group(qualification)
            if str(job.get('group','')).strip() in allowed_groups:
                score += 1

        # Department check
        if department:
            total += 1
            if department.lower() in str(job.get('department','')).lower():
                score += 1

        # Activities check
        if activities:
            total += 1
            fr = str(job.get('functional_requirements','')).upper()
            fr_clean = ''.join([c for c in fr if c.isalpha() or c==' '])
            selected_norm = [a.split()[0].upper() for a in activities]
            if any(a in fr_clean for a in selected_norm):
                score += 1
        
        # Decide full vs partial
        if score == total and total>0:
            full_matches.append(job)
        elif score > 0:
            partial_matches.append(job)

    full_df = pd.DataFrame(full_matches)
    partial_df = pd.DataFrame(partial_matches)
    return full_df, partial_df

def capitalize_first_letter(value):
    value = str(value).strip()
    if value != '-':
        return value[0].upper() + value[1:]
    return value

def generate_pdf_tabulated(full_df, partial_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3)
    elements = []
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=5, fontSize=18)
    style_text = ParagraphStyle('Text', parent=styles['Normal'], spaceAfter=10, fontSize=11, leading=15)

    elements.append(Paragraph('<font color="darkblue">Suyog+</font> - By DAIL NIEPMD', style_title))
    elements.append(Spacer(1, 20))

    # Full Matches
    elements.append(Paragraph(f"✅ Full Matches: {len(full_df)}", style_text))
    for _, job in full_df.iterrows():
        elements.append(Paragraph(f"<b>Designation:</b> {capitalize_first_letter(job.get('designation','-'))}", style_text))
        elements.append(Paragraph(f"<b>Group:</b> {capitalize_first_letter(job.get('group','-'))}", style_text))
        elements.append(Paragraph(f"<b>Department:</b> {capitalize_first_letter(job.get('department','-'))}", style_text))
        elements.append(Paragraph(f"<b>Qualification Required:</b> {capitalize_first_letter(job.get('qualification_required','-'))}", style_text))
        elements.append(Paragraph(f"<b>Functional Requirements:</b> {capitalize_first_letter(job.get('functional_requirements','-'))}", style_text))
        elements.append(Spacer(1, 10))

    # Partial Matches
    elements.append(Paragraph(f"⚠️ Partial Matches: {len(partial_df)}", style_text))
    for _, job in partial_df.iterrows():
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
    full_jobs, partial_jobs = filter_jobs_with_partial(disability, subcategory, qualification, department, selected_activities)
    
    st.success(f"✅ Full Matches: {len(full_jobs)}")
    st.warning(f"⚠️ Partial Matches: {len(partial_jobs)}")

    pdf_buffer = generate_pdf_tabulated(full_jobs, partial_jobs)
    st.download_button(label="📄 Download Results as PDF", data=pdf_buffer, file_name="suyog_jobs.pdf", mime="application/pdf")

    if st.checkbox("🔊 Read summary aloud"):
        tts = gTTS(f"Found {len(full_jobs)} full matches and {len(partial_jobs)} partial matches. Please check the PDF for details.", lang='en')
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        st.audio(audio_buffer, format="audio/mp3")

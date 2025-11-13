import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from gtts import gTTS
import os
import json
from PIL import Image

# --------------------------- Page Config ---------------------------
st.set_page_config(
    page_title="Suyog+ Job Finder",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Optional logo
if os.path.exists("logo.png"):
    logo = Image.open("logo.png")
    st.image(logo, width=100)

# --------------------------- Header ---------------------------
st.markdown("""
    <h1 style='text-align: center; color: darkblue;'>
        🧩 Suyog<font color='maroon'>+</font> Job Finder
    </h1>
    <h4 style='text-align: center; color: gray;'>
        Find government-identified jobs suitable for persons with disabilities in India
    </h4>
    <hr>
""", unsafe_allow_html=True)

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
    "Visual Impairment", "Hearing Impairment", "Physical Disabilities",
    "Neurological Disabilities", "Blood Disorders", "Intellectual and Developmental Disabilities",
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

departments = df["department"].dropna().unique().tolist()

activities = [
    "S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting", "PP Pulling & Pushing",
    "KC Kneeling & Crouching", "MF Manipulation with Fingers", "RW Reading & Writing",
    "SE Seeing", "H Hearing", "C Communication"
]

# --------------------------- Helper Functions ---------------------------
def map_group(qualification):
    q = qualification.strip().lower()
    if q in ["graduate","post graduate","doctorate"]:
        return ["Group A","Group B","Group C","Group D"]
    elif q == "12th standard":
        return ["Group C","Group D"]
    else:  # includes 10th Standard and others
        return ["Group D"]

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()

    # Filter by disability
    if disability:
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(disability.lower(), na=False)
        df_filtered = df_filtered[mask]

    # Filter by subcategory (for intellectual disabilities)
    if subcategory:
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.lower().str.contains(subcategory.lower(), na=False)
        df_filtered = df_filtered[mask_sub]

    # Filter by qualification group
    if qualification and "group" in df_filtered.columns:
        allowed_groups = map_group(qualification)
        mask_group = df_filtered["group"].astype(str).str.split(",").apply(
            lambda x: any(g.strip() in allowed_groups for g in x)
        )
        df_filtered = df_filtered[mask_group]

    # Filter by department
    if department:
        mask_dep = df_filtered["department"].astype(str).str.lower().str.contains(department.lower(), na=False)
        df_filtered = df_filtered[mask_dep]

    # Filter by functional abilities
    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str)\
            .str.upper().str.replace(r'[^A-Z ]','', regex=True)
        selected_norm = [a.split()[0].upper() for a in activities]
        mask_act = df_filtered["functional_norm"].apply(lambda fr: any(a in fr for a in selected_norm))
        df_filtered = df_filtered[mask_act]

    return df_filtered.reset_index(drop=True)

def capitalize_first_letter(value):
    value = str(value).strip()
    return value[0].upper() + value[1:] if value and value != '-' else value

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

    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", style_text))
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

# --------------------------- Sidebar ---------------------------
st.sidebar.title("Filter Jobs")
disability = st.sidebar.selectbox("Select your disability:", disabilities)
subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.sidebar.selectbox("Select your subcategory:", intellectual_subcategories)
qualification = st.sidebar.selectbox("Select your qualification:", qualifications)
department = st.sidebar.selectbox("Select a department:", departments)
selected_activities = st.sidebar.multiselect("Select your functional abilities:", activities)

# --------------------------- Main Content ---------------------------
if st.sidebar.button("🔍 Find Jobs"):
    jobs = filter_jobs(disability, subcategory, qualification, department, selected_activities)
    if len(jobs) == 0:
        st.error("❌ No matching jobs found. Try different criteria.")
    else:
        st.success(f"✅ Found {len(jobs)} matching jobs.")
        pdf_buffer = generate_pdf_tabulated(jobs)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📄 Download Results as PDF",
                data=pdf_buffer,
                file_name="suyog_jobs.pdf",
                mime="application/pdf"
            )
        with col2:
            if st.checkbox("🔊 Read summary aloud"):
                tts = gTTS(f"Found {len(jobs)} matching jobs. Please check the PDF for details.", lang='en')
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)
                st.audio(audio_buffer, format="audio/mp3")

# --------------------------- Footer ---------------------------
st.markdown("""
    <hr>
    <p style='text-align: center; color: gray; font-size:12px;'>
    Developed by DAIL NIEPMD | Powered by Streamlit
    </p>
""", unsafe_allow_html=True)

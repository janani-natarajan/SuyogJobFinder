# Suyog+ Web App (Streamlit) — Cloud-ready
# Uses browser-side speech recognition (Web Speech API) instead of Python STT.

import streamlit as st
import pandas as pd
import io
import json
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap
from gtts import gTTS
import streamlit.components.v1 as components
from pathlib import Path

# --------------------------- Page Config ---------------------------
st.set_page_config(page_title="Suyog+ Job Finder", layout="wide")

# --------------------------- Helper Functions ---------------------------
@st.cache_data
def load_jsonl_file(path):
    """Load JSON or JSONL dataset from repo."""
    try:
        df = pd.read_json(path, lines=True)
    except:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)

    # Normalize text columns
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

    return df


def map_group(qualification):
    q = str(qualification).strip().lower()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    elif q == "12th standard":
        return ["Group C", "Group D"]
    elif q == "10th standard":
        return ["Group D"]
    else:
        return ["Group D"]


def filter_jobs(df, disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()

    # Disability filter
    if disability:
        d = disability.strip().lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(d, regex=False, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Subcategory filter
    if subcategory:
        sub_lower = subcategory.strip().lower()
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.lower().str.contains(sub_lower, regex=False, na=False)
        if mask_sub.any():
            df_filtered = df_filtered[mask_sub]

    # Qualification → Allowed Groups
    allowed_groups = map_group(qualification) if qualification else []
    if allowed_groups and "group" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["group"].astype(str).str.strip().isin(allowed_groups)]

    # Department filter
    if department and "department" in df_filtered.columns:
        dep_lower = department.strip().lower()
        df_filtered = df_filtered[df_filtered["department"].astype(str).str.lower().str.contains(dep_lower, regex=False, na=False)]

    # Functional Activities
    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered = df_filtered.copy()
        df_filtered["functional_norm"] = (
            df_filtered["functional_requirements"]
            .astype(str)
            .str.upper()
            .str.replace(r'[^A-Z ]', '', regex=True)
        )
        selected_norm = [a.split()[0].upper() for a in activities]
        mask_act = df_filtered["functional_norm"].apply(lambda fr: any(a in fr for a in selected_norm))
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
    style_heading4 = ParagraphStyle('Heading4', parent=styles['Heading4'], spaceAfter=6, fontSize=12, textColor=colors.darkred)
    style_text = ParagraphStyle('Text', parent=styles['Normal'], spaceAfter=10, fontSize=11, leading=15)

    elements.append(Paragraph('<font color="darkblue">Suyog</font><font color="maroon">+</font>', style_title))
    elements.append(Paragraph('<font color="darkblue">By DAIL NIEPMD</font>', style_title))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", styles['Heading1']))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        elements.append(Paragraph(f"Designation: {str(job.get('designation', '-')).capitalize()}", style_heading2))
        elements.append(Paragraph(f"Group: {str(job.get('group', '-')).capitalize()}", style_heading3))
        elements.append(Paragraph(f"Department: {str(job.get('department', '-')).capitalize()}", style_heading4))
        elements.append(Spacer(1, 10))

        job_data = [
            ("Qualification Required", job.get('qualification_required', '-')),
            ("Functional Requirements", job.get('functional_requirements', '-')),
            ("Disabilities Supported", " ".join([str(job.get(col, '')) for col in jobs_df.columns if "disabilities" in col.lower()])),
            ("Nature of Work", job.get('nature_of_work', '-')),
            ("Working Conditions", job.get('working_conditions', '-'))
        ]
        for field, value in job_data:
            wrapped = "<br/>".join(wrap(str(value).capitalize(), 100))
            elements.append(Paragraph(f"<b>{field}:</b> {wrapped}", style_text))

        elements.append(Spacer(1, 25))
        elements.append(Paragraph("<hr/>", style_text))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# --------------------------- Load Dataset ---------------------------
DATA_PATH = Path("cleaned_data.jsonl")

if not DATA_PATH.exists():
    st.error("❌ Dataset file 'cleaned_data.jsonl' not found in the repo.")
    st.stop()

df = load_jsonl_file(DATA_PATH)
st.success(f"Dataset loaded successfully — {len(df)} records")

# --------------------------- Form Options ---------------------------
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

departments = df["department"].dropna().unique().tolist() if "department" in df.columns else []

activities_list = [
    "S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting",
    "PP Pulling & Pushing", "KC Kneeling & Crouching", "MF Manipulation with Fingers",
    "RW Reading & Writing", "SE Seeing", "H Hearing", "C Communication"
]

# --------------------------- UI ---------------------------
st.title("Suyog+ — Job Finder for Persons with Disabilities")
st.markdown("Cloud-ready version with dataset auto-load and browser voice transcription.")

# Search Form
with st.form("search_form"):
    col1, col2 = st.columns(2)
    with col1:
        disability = st.selectbox("Select disability", disabilities)
        subcategory = None
        if disability == "Intellectual and Developmental Disabilities":
            subcategory = st.selectbox("Select subcategory", intellectual_subcategories)

    with col2:
        qualification = st.selectbox("Select qualification", qualifications)
        department = st.selectbox("Select department", departments)

    selected_activities = st.multiselect("Functional Activities", activities_list)
    activity_text = st.text_input("Paste codes or transcript text (optional)")

    submitted = st.form_submit_button("Search Jobs")

# ---------------- Voice Recorder (Browser-based) ----------------
components.html("""
<div>
  <h4>🎤 Voice Input (Browser-based)</h4>
  <button id="start">Start</button>
  <button id="stop">Stop</button>
  <textarea id="text" style="width:100%;height:120px;margin-top:10px"></textarea>
</div>
<script>
let r = null;
if ('webkitSpeechRecognition' in window) {
  r = new webkitSpeechRecognition();
  r.continuous = true;
  r.interimResults = true;
}
document.getElementById('start').onclick = () => { if(r) r.start(); };
document.getElementById('stop').onclick = () => { if(r) r.stop(); };
if(r){
  r.onresult = e => {
    let t = "";
    for(let i=e.resultIndex;i<e.results.length;i++){
      t += e.results[i][0].transcript + " ";
    }
    document.getElementById('text').value = t;
  };
}
</script>
""", height=250)

# Merge manual + voice activities
combined_activities = list(selected_activities)

if activity_text:
    tokens = [x.strip() for x in activity_text.replace(",", " ").split()]
    for t in tokens:
        for act in activities_list:
            if t.upper() in act.upper():
                if act not in combined_activities:
                    combined_activities.append(act)

# --------------------------- Perform Search ---------------------------
if submitted:
    results = filter_jobs(
        df,
        disability=disability,
        subcategory=subcategory,
        qualification=qualification,
        department=department,
        activities=combined_activities
    )

    if results.empty:
        st.warning("No job matches found.")
        t = gTTS("Sorry, no jobs matched your profile.", lang="en")
        buf = io.BytesIO()
        t.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf.read(), format="audio/mp3")

    else:
        st.success(f"{len(results)} jobs found!")
        st.dataframe(results.head(50))

        pdf_bytes = generate_pdf_tabulated(results)
        st.download_button("Download PDF", data=pdf_bytes, file_name="job_matches.pdf", mime="application/pdf")

        t = gTTS(f"{len(results)} jobs found. PDF ready to download.", lang="en")
        buf = io.BytesIO()
        t.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf.read(), format="audio/mp3")

st.markdown("---")
st.caption("Suyog+ — Cloud-Optimized Version")

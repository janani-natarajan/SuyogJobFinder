# Suyog+ Web App (Streamlit) — Cloud-ready
# Fully normalized dataset & robust filtering

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

st.set_page_config(page_title="Suyog+ Job Finder", layout="wide")

# --------------------------- Helper Functions ---------------------------
@st.cache_data
def load_jsonl_file(path):
    try:
        df = pd.read_json(path, lines=True)
    except:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().str.lower()
    return df

def map_group(qualification):
    q = str(qualification).lower().strip()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["group a", "group b", "group c", "group d"]
    elif q == "12th standard":
        return ["group c", "group d"]
    elif q == "10th standard":
        return ["group d"]
    else:
        return ["group d"]

def filter_jobs(df, disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()
    disability = disability.lower().strip() if disability else None
    subcategory = subcategory.lower().strip() if subcategory else None
    department = department.lower().strip() if department else None
    activities = [a.upper().strip() for a in activities] if activities else []

    # Disability
    if disability:
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.contains(disability, regex=False, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Subcategory
    if subcategory:
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.contains(subcategory, regex=False, na=False)
        if mask_sub.any():
            df_filtered = df_filtered[mask_sub]

    # Qualification → Group
    allowed_groups = map_group(qualification) if qualification else []
    if allowed_groups and "group" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["group"].astype(str).str.lower().isin(allowed_groups)]

    # Department
    if department and "department" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["department"].astype(str).str.lower().str.contains(department, regex=False, na=False)]

    # Functional Activities
    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered = df_filtered.copy()
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper().str.replace(r'[^A-Z ]', '', regex=True)
        mask_act = df_filtered["functional_norm"].apply(lambda fr: any(act in fr for act in activities))
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
st.success(f"✅ Dataset loaded successfully — {len(df)} records")

# --------------------------- UI Form Options ---------------------------
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

# --------------------------- Search Form ---------------------------
st.title("Suyog+ — Job Finder for Persons with Disabilities")
st.markdown("Cloud-ready version with dataset auto-load and browser voice transcription.")

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

# --------------------------- Browser Voice Input ---------------------------
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

# --------------------------- Combine Activities ---------------------------
combined_activities = list(selected_activities)
if activity_text:
    tokens = [x.strip() for x in activity_text.replace(",", " ").split()]
    for t in tokens:
        for act in activities_list:
            if t.lower() in act.lower() and act not in combined_activities:
                combined_activities.append(act)

# --------------------------- Perform Search ---------------------------
if submitted:
    results = filter_jobs(
        df,
        disability=disability.lower().strip(),
        subcategory=subcategory.lower().strip() if subcategory else None,
        qualification=qualification,
        department=department.lower().strip(),
        activities=[a.lower() for a in combined_activities]
    )
    st.write(f"Filtered results: {len(results)}")
    if results.empty:
        st.warning("😞 No job matches found.")
        t = gTTS("Sorry, no jobs matched your profile.", lang="en")
        buf = io.BytesIO()
        t.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf.read(), format="audio/mp3")
    else:
        st.success(f"✅ {len(results)} jobs found!")
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

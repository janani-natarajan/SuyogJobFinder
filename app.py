# Suyog+ Web App (Streamlit)
# Converted from Telegram bot to a single-file Streamlit website
# Features implemented to match the bot behavior:
# - Upload JSON/JSONL dataset
# - Select disability, (if intellectual -> subcategory), qualification, department
# - Pick functional activities (buttons + text/voice transcription)
# - Filter jobs using same rules and generate a PDF of results
# - Text-to-speech for announcements (gTTS)

import streamlit as st
import pandas as pd
import io
import json
import time
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap
from reportlab.lib import colors
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment

# --------------------------- Auto-load cleaned_data.jsonl ---------------------------
DEFAULT_DATA_PATH = r"C:\Users\ADMIN\Documents\SuyogJobFinder\cleaned_data.jsonl"

def auto_load_default():
    try:
        return pd.read_json(DEFAULT_DATA_PATH, lines=True)
    except Exception as e:
        st.error(f"Auto-load failed: {e}")
        return None

# ----------------------------------------------------------------------

st.set_page_config(page_title="Suyog+ Job Finder", layout="wide")

# --------------------------- 1. Helper utilities ---------------------------
@st.cache_data
def load_dataframe_from_bytes(uploaded_bytes, filename):
    try:
        # try JSON lines
        df = pd.read_json(io.BytesIO(uploaded_bytes), lines=True)
    except ValueError:
        # try normal JSON
        try:
            data = json.loads(uploaded_bytes.decode('utf-8'))
            df = pd.DataFrame(data)
        except Exception as e:
            raise e
    # normalize string columns
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

    if department and "department" in df_filtered.columns:
        dep_lower = department.strip().lower()
        mask_dep = df_filtered["department"].astype(str).str.lower().str.contains(dep_lower, regex=False, na=False)
        if mask_dep.any():
            df_filtered = df_filtered[mask_dep]

    if activities and "functional_requirements" in df_filtered.columns:
        # normalize functional requirements
        df_filtered = df_filtered.copy()
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper().str.replace(r'[^A-Z ]', '', regex=True)
        selected_norm = [a.split()[0].upper() for a in activities]
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
    return buffer.getvalue()


# --------------------------- 2. UI & App State ---------------------------
if 'uploaded_df' not in st.session_state:
    st.session_state['uploaded_df'] = None

st.title("Suyog+ — Job Finder for Persons with Disabilities")
st.markdown("Upload your cleaned JSON/JSONL dataset and use the controls to find matches.")

# Auto-loaded dataset replaces upload UI
st.session_state['uploaded_df'] = auto_load_default()
if st.session_state['uploaded_df'] is None:
    st.error("Default dataset could not be loaded. Please check the file path.")
    st.stop()

# derived options
df = st.session_state['uploaded_df']

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
activities_list = ["S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting", "PP Pulling & Pushing",
                   "KC Kneeling & Crouching", "MF Manipulation with Fingers", "RW Reading & Writing",
                   "SE Seeing", "H Hearing", "C Communication"]

# Form for user inputs
with st.form("job_search_form"):
    col1, col2 = st.columns(2)
    with col1:
        disability = st.selectbox("Select your type of disability", disabilities)
        subcategory = None
        if disability == "Intellectual and Developmental Disabilities":
            subcategory = st.selectbox("Select subcategory", intellectual_subcategories)
    with col2:
        qualification = st.selectbox("Select highest qualification", qualifications)
        department = st.selectbox("Select department", departments)

    st.write("Select functional activities (click to add). You can also paste codes like 'S, W' into the textbox below or upload a voice note to transcribe.")
    # activities as toggles
    selected_activities = st.multiselect("Functional activities", activities_list)
    activity_text = st.text_input("Or type/paste activity codes or names (e.g., 'S Sitting, W Walking')")

    # Audio upload for voice transcription
    audio_file = st.file_uploader("Upload a voice note (ogg/mp3/wav) to transcribe activities (optional)", type=['ogg','mp3','wav'])

    submitted = st.form_submit_button("Search jobs")

# process transcription if provided
transcribed_text = ""
if audio_file is not None:
    try:
        # Convert to WAV (if needed) and transcribe
        tmp_bytes = audio_file.read()
        ext = audio_file.name.split('.')[-1].lower()
        wav_bytes = None
        if ext == 'wav':
            wav_bytes = tmp_bytes
        else:
            # use pydub to convert
            audio_segment = AudioSegment.from_file(io.BytesIO(tmp_bytes), format=ext)
            out_buf = io.BytesIO()
            audio_segment.export(out_buf, format='wav')
            wav_bytes = out_buf.getvalue()

        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
            audio_data = recognizer.record(source)
        transcribed_text = recognizer.recognize_google(audio_data)
        st.info(f"🗣️ Transcribed: {transcribed_text}")
    except sr.UnknownValueError:
        st.warning("Could not understand the audio.")
    except Exception as e:
        st.error(f"Transcription failed: {e}")

# Combine activities from selections, text and transcription
combined_activities = list(selected_activities)
if activity_text:
    # parse codes or names
    tokens = [w.strip() for w in activity_text.replace(',', ' ').split() if w.strip()]
    # attempt to match with activities_list
    for t in tokens:
        # match by code or substring
        for act in activities_list:
            if t.upper() in act.upper() or act.split()[0].upper() == t.upper():
                if act not in combined_activities:
                    combined_activities.append(act)

if transcribed_text:
    tokens = [w.strip() for w in transcribed_text.replace(',', ' ').split() if w.strip()]
    for t in tokens:
        for act in activities_list:
            if t.upper() in act.upper() or act.split()[0].upper() == t.upper():
                if act not in combined_activities:
                    combined_activities.append(act)

# When user submits form, run search
if submitted:
    df_results = filter_jobs(
        df=df,
        disability=disability,
        subcategory=subcategory,
        qualification=qualification,
        department=department,
        activities=combined_activities
    )

    if df_results.empty:
        st.warning("😞 Sorry, no jobs matched your profile.")
        # TTS: produce an audio file saying sorry
        tts = gTTS(text="Sorry, no jobs matched your profile.", lang='en')
        tts_buf = io.BytesIO()
        tts.write_to_fp(tts_buf)
        tts_buf.seek(0)
        st.audio(tts_buf.read(), format='audio/mp3')
    else:
        st.success(f"✅ {len(df_results)} jobs matched your profile.")
        # show a preview of matches
        st.dataframe(df_results.head(50))
        # generate pdf bytes
        pdf_bytes = generate_pdf_tabulated(df_results)
        st.download_button("Download PDF with matches", data=pdf_bytes, file_name="job_matches.pdf", mime='application/pdf')
        # TTS: confirmation
        tts = gTTS(text=f"{len(df_results)} jobs matched your profile. PDF is ready to download.", lang='en')
        tts_buf = io.BytesIO()
        tts.write_to_fp(tts_buf)
        tts_buf.seek(0)
        st.audio(tts_buf.read(), format='audio/mp3')

# Footer
st.markdown("---")
st.caption("Converted from Telegram bot logic — same filtering and PDF output. To run locally: `streamlit run suyog_plus_streamlit_app.py`.")

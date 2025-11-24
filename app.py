# --------------------------- Imports ---------------------------
import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from gtts import gTTS
from pydub import AudioSegment
from PIL import Image
import imageio_ffmpeg
import os

# --------------------------- FFmpeg Setup ---------------------------
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

# --------------------------- Streamlit Config ---------------------------
st.set_page_config(
    page_title="Suyog Job Finder",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------- Load Dataset ---------------------------
DATA_URL = "https://github.com/janani-natarajan/SuyogJobFinder/raw/main/Dataset.xlsx"

@st.cache_data
def load_data(url):
    try:
        df = pd.read_excel(url)
        # Ensure 'functional_requirements' column exists
        if 'functional_requirements' not in df.columns:
            df['functional_requirements'] = ""
        return df
    except Exception as e:
        st.error(f"Failed to load dataset: {e}")
        return pd.DataFrame()

df = load_data(DATA_URL)

if df.empty:
    st.error("Dataset could not be loaded.")
else:
    st.success("✅ Dataset loaded successfully!")
    st.dataframe(df.head())

# --------------------------- Job Search Sidebar ---------------------------
st.sidebar.header("Job Search Filters")

designation_input = st.sidebar.text_input("Designation")
department_input = st.sidebar.text_input("Department")
qualification_input = st.sidebar.text_input("Qualification")
functional_input = st.sidebar.text_input("Functional Requirement (comma-separated)")

# --------------------------- Job Filtering Function ---------------------------
def search_jobs(df, designation, department, qualification, functional):
    filtered = df.copy()
    
    if designation:
        filtered = filtered[filtered['designation'].str.contains(designation, case=False, na=False)]
    if department:
        filtered = filtered[filtered['department'].str.contains(department, case=False, na=False)]
    if qualification:
        filtered = filtered[filtered['qualification_required'].str.contains(qualification, case=False, na=False)]
    
    # Functional requirement filtering
    if functional:
        func_terms = [x.strip().lower() for x in functional.split(",")]
        mask = filtered['functional_requirements'].fillna("").apply(
            lambda x: all(term in x.lower() for term in func_terms)
        )
        filtered = filtered[mask]
    
    return filtered

# --------------------------- Search Jobs ---------------------------
results = search_jobs(df, designation_input, department_input, qualification_input, functional_input)

# --------------------------- Display Results ---------------------------
st.header("Matching Jobs")

if results.empty:
    st.warning("⚠️ No job matches found. Try adjusting your filters or functional requirements.")
else:
    st.success(f"✅ Found {len(results)} matching jobs!")
    st.dataframe(results.reset_index(drop=True))

# --------------------------- PDF Export ---------------------------
st.header("Export Results to PDF")

if not results.empty:
    pdf_button = st.button("Generate PDF")
    if pdf_button:
        pdf_path = "job_results.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A3)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Matching Jobs", styles['Title']))
        elements.append(Spacer(1, 12))

        for index, row in results.iterrows():
            job_text = f"Designation: {row['designation']}<br/>" \
                       f"Department: {row['department']}<br/>" \
                       f"Qualification: {row['qualification_required']}<br/>" \
                       f"Functional Requirements: {row['functional_requirements']}"
            elements.append(Paragraph(job_text, styles['Normal']))
            elements.append(Spacer(1, 12))

        doc.build(elements)
        st.success(f"PDF Generated: {pdf_path}")
        st.download_button("Download PDF", data=open(pdf_path, "rb"), file_name="job_results.pdf")

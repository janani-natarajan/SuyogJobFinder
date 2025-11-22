# app.py — Suyog+ Job Finder (Safe PDF)
import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from gtts import gTTS
import os

# --------------------------- Config ---------------------------
st.set_page_config(page_title="Suyog+ Job Finder", page_icon="🧩", layout="wide")

# --------------------------- Load Dataset ---------------------------
DATA_FILE = "cleaned_data.jsonl"

if not os.path.exists(DATA_FILE):
    st.error(f"Dataset '{DATA_FILE}' not found!")
    st.stop()

df = pd.read_json(DATA_FILE, lines=True)
df.columns = [c.strip().lower() for c in df.columns]

# Strip string columns
for col in df.select_dtypes("object"):
    df[col] = df[col].str.strip()

# Ensure department & group columns exist
df["department"] = df.get("department", pd.Series([None]*len(df)))
df["group"] = df.get("group", pd.Series(["Group D"]*len(df)))  # default group if missing

departments = sorted([d for d in df["department"].dropna().unique()])

# --------------------------- Options ---------------------------
disabilities = [
    "Any", "Visual Impairment", "Hearing Impairment", "Physical Disabilities",
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

qualifications = ["Any", "10th Standard", "12th Standard", "Certificate", "Diploma",
                  "Graduate", "Post Graduate", "Doctorate"]

# --------------------------- Helper Functions ---------------------------
def capitalize_first_letter(value):
    """Safe capitalization of strings"""
    if not value:
        return "-"
    value = str(value).strip()
    if not value:
        return "-"
    return value[0].upper() + value[1:]

def map_group(qualification):
    if not qualification or qualification.lower() == "any":
        return ["Group A", "Group B", "Group C", "Group D"]
    q = qualification.lower()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    if q == "12th standard":
        return ["Group C", "Group D"]
    return ["Group D"]

def get_disability_text(job_row):
    keys = [k for k in job_row.keys() if "category_of_disabilities" in k.lower()]
    return " ".join(str(job_row.get(k, "-")) for k in keys if pd.notna(job_row.get(k, ""))) or "-"

# --------------------------- Classify Jobs ---------------------------
def classify_jobs(df, department, qualification, disability, subcategory):
    df_filtered = df.copy()
    st.write("### Debug: Job counts after each filter")
    st.write("Total jobs in dataset:", len(df_filtered))

    # Department filter
    if department != "Any":
        df_filtered = df_filtered[df_filtered["department"].str.contains(department, case=False, na=False)]
    st.write("After department filter:", len(df_filtered))

    # Qualification → Group filter
    allowed_groups = map_group(qualification)
    df_filtered = df_filtered[df_filtered["group"].apply(
        lambda g: any(ag.lower() in str(g).lower() for ag in allowed_groups)
    )]
    st.write("After group/qualification filter:", len(df_filtered))

    # Disability filter
    if disability != "Any":
        df_filtered = df_filtered[df_filtered.apply(
            lambda row: disability.lower() in get_disability_text(row).lower(),
            axis=1
        )]
    st.write("After disability filter:", len(df_filtered))

    # Subcategory filter
    if disability == "Intellectual and Developmental Disabilities" and subcategory != "Any":
        df_filtered = df_filtered[df_filtered["subcategory"].str.lower() == subcategory.lower()]
    st.write("After subcategory filter:", len(df_filtered))

    return df_filtered.reset_index(drop=True)

# --------------------------- PDF Generator ---------------------------
def generate_pdf(df_jobs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Heading1'], alignment=1, fontSize=22)
    cell_style = ParagraphStyle('cell', parent=styles['Normal'], fontSize=12)

    elems = [Paragraph("🧩 Suyog+ Job Finder — Results", title_style), Spacer(1, 20)]

    data = [["Designation", "Department", "Group", "Qualification", "Disabilities", "Functions"]]

    for _, row in df_jobs.iterrows():
        designation = capitalize_first_letter(row.get("designation", "-"))
        department = capitalize_first_letter(row.get("department", "-"))
        group = capitalize_first_letter(row.get("group", "-"))
        qualification = capitalize_first_letter(row.get("qualification_required", "-"))
        functions = capitalize_first_letter(row.get("functional_requirements", "-"))

        disabilities = get_disability_text(row)

        data.append([
            Paragraph(designation, cell_style),
            Paragraph(department, cell_style),
            Paragraph(group, cell_style),
            Paragraph(qualification, cell_style),
            Paragraph(disabilities, cell_style),
            Paragraph(functions, cell_style)
        ])

    table = Table(data, repeatRows=1, colWidths=[120, 120, 60, 80, 150, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP")
    ]))

    elems.append(table)
    doc.build(elems)
    buffer.seek(0)
    return buffer

# --------------------------- Display Results ---------------------------
def display_results(df_jobs):
    if df_jobs.empty:
        st.error("❌ No matching jobs found")
        return

    st.success(f"Found {len(df_jobs)} matching jobs")

    pdf_buffer = generate_pdf(df_jobs)
    st.download_button("📄 Download PDF", pdf_buffer, file_name="suyog_matches.pdf", mime="application/pdf")

    tts = gTTS(f"Found {len(df_jobs)} matching jobs.", lang='en')
    abuf = io.BytesIO()
    tts.write_to_fp(abuf)
    abuf.seek(0)
    st.audio(abuf, format="audio/mp3")

# --------------------------- Streamlit UI ---------------------------
st.sidebar.header("Filter Criteria")

disability = st.sidebar.selectbox("Disability", disabilities)
subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.sidebar.selectbox("Subcategory", ["Any"] + intellectual_subcategories)

qualification = st.sidebar.selectbox("Qualification", qualifications)

dept_search = st.sidebar.text_input("Search Department")
filtered_depts = [d for d in departments if dept_search.lower() in d.lower()] if dept_search else departments
department = st.sidebar.selectbox("Department", ["Any"] + filtered_depts)

st.title("🧩 Suyog+ Job Finder")

if st.sidebar.button("🔍 Find Jobs"):
    matched = classify_jobs(df, department, qualification, disability, subcategory)
    display_results(matched)

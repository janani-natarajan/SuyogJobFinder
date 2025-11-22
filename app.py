# app.py — Suyog+ Job Finder with Department Suggestions
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
DATA_FILE = "cleaned_data.jsonl"  # update path if needed

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
df["group"] = df.get("group", pd.Series(["Group D"]*len(df)))
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
def map_group(qualification):
    """Map qualification to allowed groups (fixed)"""
    if not qualification or qualification.lower() == "any":
        return ["Group A", "Group B", "Group C", "Group D"]
    q = qualification.lower()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    if q == "12th standard":
        return ["Group C", "Group D"]
    return ["Group D"]

def get_disability_text(job_row):
    """Concatenate all disability-related fields"""
    keys = [k for k in job_row.keys() if "category_of_disabilities" in k.lower()]
    return " ".join(str(job_row.get(k, "")) for k in keys if pd.notna(job_row.get(k, "")))

# --------------------------- Job Classification ---------------------------
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
    df_filtered = df_filtered[df_filtered['group'].fillna('') \
        .apply(lambda g: any(ag.lower() in g.lower() for ag in allowed_groups))]
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
        if 'subcategory' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["subcategory"].str.lower() == subcategory.lower()]
    st.write("After subcategory filter:", len(df_filtered))

    # Fallback if no exact match
    if df_filtered.empty:
        st.warning("❌ No exact matches. Showing partial matches ignoring disability/subcategory.")
        df_filtered = df.copy()

    return df_filtered.reset_index(drop=True)

# --------------------------- Safe Capitalization ---------------------------
def capitalize_first_letter(value):
    if value is None:
        return "-"
    value = str(value).strip()
    if value == "":
        return "-"
    return value[0].upper() + value[1:]


# --------------------------- PDF Generator (No More Errors) ---------------------------
def generate_pdf_tabulated(jobs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3)

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        'title',
        parent=styles['Heading1'],
        fontSize=22,
        alignment=1
    )
    style_text = ParagraphStyle(
        'text',
        parent=styles['Normal'],
        fontSize=12,
        leading=16
    )

    elements = []
    elements.append(Paragraph("🧩 Suyog+ Job Finder — Results", style_title))
    elements.append(Spacer(1, 20))

    # Create a table
    table_data = [
        ["Designation", "Department", "Group", "Qualification", "Disabilities", "Functions"]
    ]

    for _, job in jobs.iterrows():
        designation = capitalize_first_letter(job.get("designation", "-"))
        department = capitalize_first_letter(job.get("department", "-"))
        group = capitalize_first_letter(job.get("group", "-"))
        qualification = capitalize_first_letter(job.get("qualification_required", "-"))

        disabilities = job.get("category_of_disabilities", "")
        disabilities = capitalize_first_letter(disabilities)

        functions = job.get("functional_requirements", "-")
        functions = capitalize_first_letter(functions)

        table_data.append([
            Paragraph(designation, style_text),
            Paragraph(department, style_text),
            Paragraph(group, style_text),
            Paragraph(qualification, style_text),
            Paragraph(disabilities, style_text),
            Paragraph(functions, style_text),
        ])

    table = Table(table_data, repeatRows=1, colWidths=[120, 120, 60, 80, 150, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return buffer
# --------------------------- Display Results ---------------------------
def display_results(df_jobs):
    if df_jobs.empty:
        st.error("❌ No jobs to display")
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

# Filter-based job search
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

# Department-based suggestions
st.sidebar.header("💡 Department-based Suggestions")
dept_search_pref = st.sidebar.text_input("Preferred department for suggestions")

if dept_search_pref:
    suggested_jobs = df[df["department"].str.contains(dept_search_pref, case=False, na=False)].reset_index(drop=True)
    
    if suggested_jobs.empty:
        st.warning(f"❌ No jobs found in '{dept_search_pref}' department.")
    else:
        st.success(f"Found {len(suggested_jobs)} jobs in '{dept_search_pref}' department.")
        for idx, row in suggested_jobs.iterrows():
            st.write(f"**{row.get('designation','-')}** | Group: {row.get('group','-')} | Qualification: {row.get('qualification_required','-')}")

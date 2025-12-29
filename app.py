# --------------------------- 1. Imports ---------------------------
import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap

# --------------------------- 2. Load Dataset ---------------------------
df = pd.read_json("cleaned_data.jsonl", lines=True)

# ---- REMOVE TIMESTAMP / DATE COLUMNS ----
df = df.loc[:, ~df.columns.str.contains("time|date", case=False)]

if df.empty:
    st.error("Dataset is empty")
    st.stop()

# --------------------------- 3. Constants ---------------------------
GROUP_LEVEL_MAP = {
    "A": "A (Level 1)",
    "B": "B (Level 2)",
    "C": "C (Level 3)",
    "D": "D (Level 4)"
}

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

qualifications = [
    "10th Standard", "12th Standard", "Certificate", "Diploma",
    "Graduate", "Post Graduate", "Doctorate"
]

activities = [
    "S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting",
    "PP Pulling & Pushing", "KC Kneeling & Crouching",
    "MF Manipulation with Fingers", "RW Reading & Writing",
    "SE Seeing", "H Hearing", "C Communication"
]

departments = (
    df["department"]
    .dropna()
    .astype(str)
    .str.title()
    .unique()
    .tolist()
    if "department" in df.columns else []
)

# --------------------------- 4. Helper Functions ---------------------------
def map_group(qualification):
    q = qualification.lower()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["A", "B", "C", "D"]
    elif q == "12th standard":
        return ["C", "D"]
    return ["D"]

def format_department(name):
    return str(name).title()

def normalize_group(value):
    if not value:
        return ""
    value = str(value).upper()
    for g in ["A", "B", "C", "D"]:
        if g in value:
            return g
    return ""

# --------------------------- 5. Filter Function (Optional Filters) ---------------------------
def filter_jobs(disability=None, subcategory=None, qualification=None,
                department=None, activities=None):

    df_filtered = df.copy()

    # ---- Disability ----
    if disability:
        d = disability.lower()
        df_filtered = df_filtered[df_filtered.apply(
            lambda row: any(
                d in str(row[col]).lower()
                for col in df_filtered.columns
                if "disabilit" in col.lower()
            ), axis=1
        )]

    # ---- Subcategory ----
    if subcategory:
        s = subcategory.lower()
        df_filtered = df_filtered[df_filtered.apply(
            lambda row: any(
                s in str(row[col]).lower()
                for col in df_filtered.columns
                if "subcategory" in col.lower()
            ), axis=1
        )]

    # ---- Group / Qualification ----
    if qualification and "group" in df_filtered.columns:
        allowed_groups = map_group(qualification)
        df_filtered["group_norm"] = df_filtered["group"].apply(normalize_group)
        df_filtered = df_filtered[df_filtered["group_norm"].isin(allowed_groups)]

    # ---- Department ----
    if department:
        df_filtered = df_filtered[
            df_filtered["department"].astype(str).str.lower().str.contains(department.lower())
        ]

    # ---- Functional Activities ----
    if activities and "functional_requirements" in df_filtered.columns:
        selected = [a.split()[0].lower() for a in activities]
        df_filtered = df_filtered[df_filtered["functional_requirements"].astype(str).apply(
            lambda x: any(a in x.lower() for a in selected)
        )]

    return df_filtered.reset_index(drop=True)

# --------------------------- 6. PDF Generation ---------------------------
def generate_pdf(jobs_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3)
    styles = getSampleStyleSheet()

    title = ParagraphStyle("title", fontSize=18, alignment=1)
    h2 = ParagraphStyle("h2", fontSize=14, textColor=colors.darkblue)
    h3 = ParagraphStyle("h3", fontSize=12)
    text = ParagraphStyle("text", fontSize=11)

    elements = [
        Paragraph("Suyog+", title),
        Paragraph("By DAIL NIEPMD", title),
        Spacer(1, 15),
        Paragraph(f"Total Matches: {len(jobs_df)}", h2),
        Spacer(1, 20),
    ]

    for _, job in jobs_df.iterrows():
        group = GROUP_LEVEL_MAP.get(normalize_group(job.get("group")), job.get("group", "-"))
        department = format_department(job.get("department", "-"))
        disability = job.get("disabilities", "-")
        qualification = job.get("qualification_required", "-")
        functional_req = job.get("functional_requirements", "-")

        elements.append(Paragraph(f"Designation: {job.get('designation','-')}", h2))
        elements.append(Paragraph(f"Group: {group}", h3))
        elements.append(Paragraph(f"Department: {department}", h3))
        elements.append(Paragraph(f"Disability: {disability}", h3))
        elements.append(Paragraph(f"Qualification: {qualification}", h3))
        elements.append(Paragraph(f"Functional Requirements: {functional_req}", h3))
        elements.append(Spacer(1, 10))

        fields = [
            ("Nature of Work", job.get("nature_of_work", "-")),
            ("Working Conditions", job.get("working_conditions", "-")),
        ]

        for k, v in fields:
            wrapped = "<br/>".join(wrap(str(v), 100))
            elements.append(Paragraph(f"<b>{k}:</b> {wrapped}", text))

        elements.append(Spacer(1, 25))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------- 7. Streamlit UI ---------------------------
st.title("Suyog+ Job Finder")
st.markdown("Find suitable jobs for persons with disabilities in India.")

disability = st.selectbox("Select your type of disability *:", [""] + disabilities)

subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.selectbox("Select the subcategory *:", [""] + intellectual_subcategories)

qualification = st.selectbox("Select highest qualification *:", [""] + qualifications)

department = st.selectbox("Select department *:", [""] + departments) if departments else None

selected_activities = st.multiselect("Select functional activities *:", activities)

if st.button("Find Jobs"):
    results = filter_jobs(
        disability or None,
        subcategory or None,
        qualification or None,
        department or None,
        selected_activities or None
    )

    if results.empty:
        st.warning("😞 Sorry, no jobs matched your profile.")
    else:
        results["Group"] = results["group"].apply(
            lambda g: GROUP_LEVEL_MAP.get(normalize_group(g), g)
        )
        results["Department"] = results["department"].apply(format_department)
        results["Disability"] = results["disabilities"]
        results["Qualification"] = results["qualification_required"]
        results["Functional Requirements"] = results["functional_requirements"]

        st.success(f"✅ {len(results)} job(s) matched your profile.")
        st.dataframe(results)

        pdf = generate_pdf(results)
        st.download_button(
            "Download PDF of Jobs",
            data=pdf,
            file_name="job_matches.pdf",
            mime="application/pdf"
        )

# --------------------------- 1. Imports ---------------------------
import streamlit as st
import pandas as pd
import requests
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap

# --------------------------- 2. Load Dataset ---------------------------
df = pd.read_json("cleaned_data.jsonl", lines=True)

# ---- REMOVE TIMESTAMP / DATE COLUMNS GLOBALLY ----
df = df.loc[:, ~df.columns.str.contains("time|date", case=False)]

# Clean & normalize text columns
for col in df.columns:
    if df[col].dtype == object:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

if df.empty:
    st.stop()

# --------------------------- 3. Options ---------------------------
disabilities = [
    "Visual Impairment", "Hearing Impairment", "Physical Disabilities",
    "Neurological Disabilities", "Blood Disorders",
    "Intellectual and Developmental Disabilities", "Mental Illness", "Multiple Disabilities"
]

intellectual_subcategories = [
    "Autism Spectrum Disorder (ASD M)",
    "Autism Spectrum Disorder (ASD MoD)",
    "Intellectual Disability (ID)",
    "Specific Learning Disability (SLD)",
    "Mental Illness"
]

qualifications = [
    "10th Standard", "12th Standard", "Certificate",
    "Diploma", "Graduate", "Post Graduate", "Doctorate"
]

departments = (
    df["department"].dropna().unique().tolist()
    if "department" in df.columns else []
)

activities = [
    "S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting",
    "PP Pulling & Pushing", "KC Kneeling & Crouching",
    "MF Manipulation with Fingers", "RW Reading & Writing",
    "SE Seeing", "H Hearing", "C Communication"
]

# --------------------------- 4. Helper Functions ---------------------------
def map_group(qualification):
    q = qualification.lower().strip() if qualification else ""
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    elif q == "12th standard":
        return ["Group C", "Group D"]
    elif q:
        return ["Group D"]
    return []

def filter_jobs(disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()

    # Disability filter
    if disability:
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.contains(disability, case=False, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Subcategory filter
    if subcategory:
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask |= df_filtered[col].astype(str).str.contains(subcategory, case=False, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Qualification group filter
    allowed_groups = map_group(qualification)
    if allowed_groups and "group" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["group"].isin(allowed_groups)]

    # Department filter
    if department and "department" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["department"].str.contains(department, case=False, na=False)]

    # Functional activities filter
    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = (
            df_filtered["functional_requirements"]
            .astype(str)
            .str.upper()
            .str.replace(r"[^A-Z ]", "", regex=True)
        )
        selected_codes = [a.split()[0] for a in activities]
        df_filtered = df_filtered[
            df_filtered["functional_norm"].apply(lambda x: any(code in x for code in selected_codes))
        ]

    return df_filtered.reset_index(drop=True)

def generate_pdf_tabulated(jobs_df):
    buffer = io.BytesIO()

    # Extra safety: remove time/date if still present
    jobs_df = jobs_df.loc[:, ~jobs_df.columns.str.contains("time|date", case=False)]

    doc = SimpleDocTemplate(
        buffer, pagesize=A3,
        rightMargin=50, leftMargin=50,
        topMargin=50, bottomMargin=50
    )

    styles = getSampleStyleSheet()
    elements = []

    title = ParagraphStyle("title", parent=styles["Heading1"], alignment=1, fontSize=18)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.darkblue)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], textColor=colors.darkgreen)
    h4 = ParagraphStyle("h4", parent=styles["Heading4"], textColor=colors.darkred)
    text = ParagraphStyle("text", parent=styles["Normal"], fontSize=11, leading=15)

    elements.append(Paragraph("Suyog<font color='maroon'>+</font>", title))
    elements.append(Paragraph("By DAIL NIEPMD", title))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", styles["Heading2"]))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        elements.append(Paragraph(f"Designation: {job.get('designation','-')}", h2))
        elements.append(Paragraph(f"Group: {job.get('group','-')}", h3))
        elements.append(Paragraph(f"Department: {job.get('department','-')}", h4))
        elements.append(Spacer(1, 10))

        fields = [
            ("Qualification Required", job.get("qualification_required", "-")),
            ("Functional Requirements", job.get("functional_requirements", "-")),
            ("Nature of Work", job.get("nature_of_work", "-")),
            ("Working Conditions", job.get("working_conditions", "-")),
        ]

        for label, value in fields:
            wrapped = "<br/>".join(wrap(str(value), 100))
            elements.append(Paragraph(f"<b>{label}:</b> {wrapped}", text))

        elements.append(Spacer(1, 25))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------- 5. Streamlit UI ---------------------------
st.title("Suyog+ Job Finder")
st.markdown("Find suitable jobs for persons with disabilities in India.")

disability = st.selectbox("Select your type of disability:", disabilities)

subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.selectbox("Select subcategory:", intellectual_subcategories)

qualification = st.selectbox("Select highest qualification:", qualifications)

department = st.selectbox("Select department:", departments) if departments else None

selected_activities = st.multiselect("Select functional activities:", activities)

if st.button("Find Jobs"):
    results = filter_jobs(disability, subcategory, qualification, department, selected_activities)

    if results.empty:
        st.warning("😞 No jobs matched your profile.")
    else:
        st.success(f"✅ {len(results)} job(s) matched your profile.")
        st.dataframe(results)

        pdf = generate_pdf_tabulated(results)
        st.download_button(
            "Download PDF of Jobs",
            data=pdf,
            file_name="job_matches.pdf",
            mime="application/pdf"
        )

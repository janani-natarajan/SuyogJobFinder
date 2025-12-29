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

def map_group(qualification):
    q = qualification.lower()
    if q in ["Graduate", "Post graduate", "Doctorate"]:
        return ["A", "B", "C", "D"]
    elif q == "12th standard":
        return ["C", "D"]
    return ["D"]

# --------------------------- 5. Filter Jobs ---------------------------
def filter_jobs(department, qualification, activities):
    df_filtered = df.copy()

    # ---- Department ----
    df_filtered = df_filtered[df_filtered["department"].astype(str).str.lower().str.strip() == department.lower().strip()]

    # ---- Qualification ----
    allowed_groups = map_group(qualification)
    df_filtered["group_norm"] = df_filtered["group"].apply(normalize_group)
    df_filtered = df_filtered[df_filtered["group_norm"].isin(allowed_groups)]

    # ---- Functional Activities ----
    selected = [a.split()[0] for a in activities]
    df_filtered = df_filtered[df_filtered["functional_requirements"].astype(str).apply(
        lambda x: all(a in x for a in selected)
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

        elements.append(Paragraph(f"Designation: {job.get('designation','-')}", h2))
        elements.append(Paragraph(f"Group: {group}", h3))
        elements.append(Paragraph(f"Department: {department}", h3))
        elements.append(Spacer(1, 10))

        fields = [
            ("Qualification Required", job.get("qualification_required", "-")),
            ("Functional Requirements", job.get("functional_requirements", "-")),
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

department = st.selectbox("Select department:", [""] + departments)
qualification = st.selectbox("Select highest qualification:", [""] + qualifications)
selected_activities = st.multiselect("Select functional activities:", activities)

if st.button("Find Jobs"):
    # Check mandatory selections
    if not department:
        st.warning("Please select a department.")
    elif not qualification:
        st.warning("Please select a qualification.")
    elif not selected_activities:
        st.warning("Please select at least one functional activity.")
    else:
        results = filter_jobs(department, qualification, selected_activities)

        if results.empty:
            st.warning("😞 No jobs found for the selected criteria.")
        else:
            results["Group"] = results["group"].apply(lambda g: GROUP_LEVEL_MAP.get(normalize_group(g), g))
            results["Department"] = results["department"].apply(format_department)

            st.success(f"✅ {len(results)} job(s) found.")
            st.dataframe(results)

            pdf = generate_pdf(results)
            st.download_button(
                "Download PDF of Jobs",
                data=pdf,
                file_name="job_matches.pdf",
                mime="application/pdf"
            )

# --------------------------- 1. Imports ---------------------------
import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap

# --------------------------- 2. Load Local Dataset ---------------------------
DATA_FILE = "cleaned_data.jsonl"

@st.cache_data
def load_dataset(file_path):
    try:
        df = pd.read_json(file_path, lines=True)

        # Clean & normalize
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

        return df

    except FileNotFoundError:
        st.error(f"❌ File not found: {file_path}")
        return pd.DataFrame()

    except ValueError as e:
        st.error(f"❌ JSON format error: {e}")
        return pd.DataFrame()

    except Exception as e:
        st.error(f"❌ Failed to load dataset: {e}")
        return pd.DataFrame()


df = load_dataset(DATA_FILE)

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
    "10th Standard", "12th Standard", "Certificate", "Diploma",
    "Graduate", "Post Graduate", "Doctorate"
]

# Safe department extraction
departments = df.get("department")
departments = departments.dropna().unique().tolist() if departments is not None else []

activities = [
    "S Sitting", "ST Standing", "W Walking", "BN Bending", "L Lifting",
    "PP Pulling & Pushing", "KC Kneeling & Crouching",
    "MF Manipulation with Fingers", "RW Reading & Writing",
    "SE Seeing", "H Hearing", "C Communication"
]

# --------------------------- 4. Helper Functions ---------------------------
def map_group(qualification):
    if not qualification:
        return []
    q = qualification.lower()
    if q in ["graduate", "post graduate", "doctorate"]:
        return ["Group A", "Group B", "Group C", "Group D"]
    elif q == "12th standard":
        return ["Group C", "Group D"]
    else:
        return ["Group D"]

def filter_jobs(disability=None, subcategory=None, qualification=None,
                department=None, activities=None):

    df_filtered = df.copy()

    # Disability filter
    if disability:
        d = disability.lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "disabilities" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(d, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Subcategory filter
    if subcategory:
        s = subcategory.lower()
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if "subcategory" in col.lower():
                mask |= df_filtered[col].astype(str).str.lower().str.contains(s, na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Qualification group filter
    allowed_groups = map_group(qualification)
    if allowed_groups and "group" in df_filtered.columns:
        mask = df_filtered["group"].astype(str).isin(allowed_groups)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Department filter
    if department and "department" in df_filtered.columns:
        mask = df_filtered["department"].astype(str).str.lower().str.contains(department.lower(), na=False)
        if mask.any():
            df_filtered = df_filtered[mask]

    # Activities filter
    if activities and "functional_requirements" in df_filtered.columns:
        df_filtered["functional_norm"] = (
            df_filtered["functional_requirements"]
            .astype(str)
            .str.upper()
            .str.replace(r"[^A-Z ]", "", regex=True)
        )
        selected = [a.split()[0] for a in activities]
        mask = df_filtered["functional_norm"].apply(lambda x: any(a in x for a in selected))
        if mask.any():
            df_filtered = df_filtered[mask]

    return df_filtered.reset_index(drop=True)

def generate_pdf_tabulated(jobs_df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A3,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    elements = []
    styles = getSampleStyleSheet()

    title = ParagraphStyle("title", parent=styles["Heading1"],
                            alignment=1, fontSize=18)

    elements.append(Paragraph("Suyog+", title))
    elements.append(Paragraph("By DAIL NIEPMD", title))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Total Matches: {len(jobs_df)}", styles["Heading2"]))
    elements.append(Spacer(1, 20))

    for _, job in jobs_df.iterrows():
        elements.append(Paragraph(f"<b>Designation:</b> {job.get('designation','-')}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Group:</b> {job.get('group','-')}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Department:</b> {job.get('department','-')}", styles["Normal"]))
        elements.append(Spacer(1, 10))

        fields = [
            ("Qualification Required", job.get("qualification_required", "-")),
            ("Functional Requirements", job.get("functional_requirements", "-")),
            ("Nature of Work", job.get("nature_of_work", "-")),
            ("Working Conditions", job.get("working_conditions", "-")),
        ]

        for f, v in fields:
            text = "<br/>".join(wrap(str(v), 100))
            elements.append(Paragraph(f"<b>{f}:</b> {text}", styles["Normal"]))

        elements.append(Spacer(1, 20))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --------------------------- 5. Streamlit App ---------------------------
st.title("Suyog+ Job Finder")
st.markdown("Find suitable jobs for persons with disabilities in India.")

disability = st.selectbox("Select disability:", disabilities)

subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.selectbox("Select subcategory:", intellectual_subcategories)

qualification = st.selectbox("Highest qualification:", qualifications)

department = None
if departments:
    department = st.selectbox("Department:", departments)

selected_activities = st.multiselect("Functional activities:", activities)

if st.button("Find Jobs"):
    results = filter_jobs(disability, subcategory, qualification, department, selected_activities)

    if results.empty:
        st.warning("😞 No jobs matched your profile.")
    else:
        st.success(f"✅ {len(results)} job(s) found")
        st.dataframe(results)

        pdf = generate_pdf_tabulated(results)
        st.download_button(
            "📄 Download PDF",
            data=pdf,
            file_name="job_matches.pdf",
            mime="application/pdf"
        )

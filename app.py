# Suyog+ Web App — Cloud-ready & Robust Filtering
import streamlit as st
import pandas as pd
import io
import json
from pathlib import Path
from reportlab.lib.pagesizes import A3
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from textwrap import wrap
from gtts import gTTS
import streamlit.components.v1 as components

st.set_page_config(page_title="Suyog+ Job Finder", layout="wide")

# ------------------- Load Dataset -------------------
DATA_PATH = Path("cleaned_data.jsonl")
if not DATA_PATH.exists():
    st.error("❌ Dataset file 'cleaned_data.jsonl' not found.")
    st.stop()

def load_jsonl_file(path):
    """Load dataset and normalize all string columns."""
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

df = load_jsonl_file(DATA_PATH)
st.success(f"✅ Dataset loaded — {len(df)} records")

# ------------------- Debug Panel -------------------
st.subheader("🛠️ Debug Info")
st.write("Columns:", df.columns.tolist())
st.write("Sample rows:")
st.dataframe(df.head(5))
if 'group' in df.columns: st.write("Groups:", df['group'].unique())
if 'department' in df.columns: st.write("Departments:", df['department'].unique())
dis_cols = [c for c in df.columns if 'disabilities' in c.lower()]
st.write("Disability columns:", dis_cols)

# ------------------- Form Options -------------------
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

# ------------------- UI -------------------
st.title("Suyog+ — Job Finder")
st.markdown("Developed by Janani N  \nAgate Infotek")

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

# ------------------- Combine Activities -------------------
combined_activities = list(selected_activities)
if activity_text:
    tokens = [x.strip() for x in activity_text.replace(",", " ").split()]
    for t in tokens:
        for act in activities_list:
            if t.lower() in act.lower() and act not in combined_activities:
                combined_activities.append(act)

# ------------------- Filter Functions -------------------
def map_group(qualification):
    q = str(qualification).lower().strip()
    if q in ["graduate","post graduate","doctorate"]: return ["group a","group b","group c","group d"]
    if q=="12th standard": return ["group c","group d"]
    if q=="10th standard": return ["group d"]
    return ["group d"]

def filter_jobs(df, disability=None, subcategory=None, qualification=None, department=None, activities=None):
    df_filtered = df.copy()
    disability = disability.lower().strip() if disability else None
    subcategory = subcategory.lower().strip() if subcategory else None
    department = department.lower().strip() if department else None
    activities = [a.upper().strip() for a in activities] if activities else []

    # Robust Disability filter (ignore case, partial match)
    if disability:
        mask = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if 'disabilities' in col.lower():
                mask |= df_filtered[col].astype(str).str.contains(disability, case=False, na=False)
        df_filtered = df_filtered[mask]

    # Subcategory filter (robust)
    if subcategory:
        mask_sub = pd.Series(False, index=df_filtered.index)
        for col in df_filtered.columns:
            if 'subcategory' in col.lower():
                mask_sub |= df_filtered[col].astype(str).str.contains(subcategory, case=False, na=False)
        if mask_sub.any():
            df_filtered = df_filtered[mask_sub]

    # Group filter
    if qualification:
        allowed_groups = map_group(qualification)
        if 'group' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['group'].astype(str).str.lower().isin([g.lower() for g in allowed_groups])]

    # Department filter
    if department and 'department' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['department'].astype(str).str.lower().str.contains(department, case=False, na=False)]

    # Functional activities filter
    if activities and 'functional_requirements' in df_filtered.columns:
        df_filtered["functional_norm"] = df_filtered["functional_requirements"].astype(str).str.upper().str.replace(r'[^A-Z ]','',regex=True)
        mask_act = df_filtered["functional_norm"].apply(lambda fr: any(act in fr for act in activities))
        df_filtered = df_filtered[mask_act]

    return df_filtered.reset_index(drop=True)

# ------------------- Perform Search -------------------
if submitted:
    results = filter_jobs(
        df,
        disability=disability,
        subcategory=subcategory,
        qualification=qualification,
        department=department,
        activities=[a.lower() for a in combined_activities]
    )

    st.write(f"Total results: {len(results)}")

    if results.empty:
        st.warning("😞 No job matches found — check debug panel above.")
    else:
        st.success(f"✅ {len(results)} jobs found!")
        st.dataframe(results.head(50))

import streamlit as st
import pandas as pd
import requests
import io

st.set_page_config(page_title="Suyog+ Job Finder", layout="wide")

# ---------------------------
# GitHub raw file URL
# ---------------------------
GITHUB_URL = "https://raw.githubusercontent.com/janani-natarajan/SuyogJobFinder/main/cleaned_data.jsonl"

# ---------------------------
# Load dataset safely
# ---------------------------
@st.cache_data(show_spinner=True)
def load_dataset(url):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()  # throws if status != 200
        text = r.text.strip()
        # Basic check: ensure it's JSONL (each line is JSON)
        if not text or not text[0] in ["{", "["]:
            st.error("⚠️ Fetched content is not valid JSON. Check the GitHub raw URL.")
            return pd.DataFrame()
        # Read JSONL
        df = pd.read_json(io.StringIO(text), lines=True)
        # Clean string columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        return df
    except Exception as e:
        st.error(f"Failed to load dataset from GitHub: {e}")
        return pd.DataFrame()

df = load_dataset(GITHUB_URL)

if df.empty:
    st.stop()
else:
    st.success(f"✅ Dataset loaded: {len(df)} records")

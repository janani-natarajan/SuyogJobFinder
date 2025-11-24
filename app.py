# --------------------------- 1. Import Libraries ---------------------------
import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import pyttsx3
import os

# --------------------------- 2. Load Dataset ---------------------------
DATA_PATH = r"C:\Users\ADMIN\OneDrive\Documents\Janani\Internship\iSUyog\Dataset.xlsx"
df = pd.read_excel(DATA_PATH)

# --------------------------- 3. Streamlit UI ---------------------------
st.set_page_config(page_title="Suyog Job Finder", layout="wide")
st.title("🔎 Suyog Job Finder")

# Input for searching jobs
search_keyword = st.text_input("Enter a keyword (designation, department, group):").strip().lower()

# Filter dataset based on input
if search_keyword:
    filtered = df[df.apply(lambda row: search_keyword in str(row['designation']).lower() \
                                        or search_keyword in str(row['department']).lower() \
                                        or search_keyword in str(row['group']).lower(), axis=1)]
else:
    filtered = df.copy()

# Display results
if filtered.empty:
    st.warning("No matching jobs found.")
else:
    st.dataframe(filtered.reset_index(drop=True))

    # --------------------------- 4. PDF Generation ---------------------------
    def generate_pdf(df_to_save):
        pdf_file = "Jobs_Report.pdf"
        doc = SimpleDocTemplate(pdf_file)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Suyog Job Finder Report", styles['Title']))
        story.append(Spacer(1, 12))

        for i, row in df_to_save.iterrows():
            text = f"<b>{row['designation']}</b> | {row['department']} | {row['group']}"
            story.append(Paragraph(text, styles['Normal']))
            story.append(Spacer(1, 6))

        doc.build(story)
        return pdf_file

    if st.button("📄 Download PDF Report"):
        pdf_path = generate_pdf(filtered)
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name="Jobs_Report.pdf")

    # --------------------------- 5. Text-to-Speech ---------------------------
    if st.button("🔊 Read Jobs Aloud"):
        engine = pyttsx3.init()
        for i, row in filtered.iterrows():
            text = f"{row['designation']}, Department: {row['department']}, Group: {row['group']}"
            engine.say(text)
        engine.runAndWait()
        st.success("✅ Done reading jobs aloud!")

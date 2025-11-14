# --------------------------- Streamlit UI ---------------------------

st.set_page_config(page_title="Suyog+ Job Finder", page_icon="🧩", layout="centered")
st.title("🧩 Suyog+ Job Finder for Persons with Disabilities")
st.write("Find government-identified jobs suitable for persons with disabilities in India.")

disability = st.selectbox("Select your disability:", disabilities)
subcategory = None
if disability == "Intellectual and Developmental Disabilities":
    subcategory = st.selectbox("Select your subcategory:", intellectual_subcategories)

qualification = st.selectbox("Select your qualification:", qualifications)

# SEARCHABLE department selection using 'st.selectbox'
department = st.selectbox(
    "Select a department:",
    options=departments,
    index=0,  # default to first department
    help="Type to search for your department"  # shows hint
)

selected_activities = st.multiselect("Select your functional abilities:", activities)

if st.button("🔍 Find Jobs"):
    jobs = filter_jobs(disability, subcategory, qualification, department, selected_activities)
    if len(jobs) == 0:
        st.error("❌ No matching jobs found. Try different criteria.")
    else:
        st.success(f"✅ Found {len(jobs)} matching jobs.")
        pdf_buffer = generate_pdf_tabulated(jobs)
        st.download_button(label="📄 Download Results as PDF", data=pdf_buffer, file_name="suyog_jobs.pdf", mime="application/pdf")
        if st.checkbox("🔊 Read summary aloud"):
            tts = gTTS(f"Found {len(jobs)} matching jobs. Please check the PDF for details.", lang='en')
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            st.audio(audio_buffer, format="audio/mp3")

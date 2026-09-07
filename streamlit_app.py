import streamlit as st
import os
import tempfile
import json
from resume_parser import parse_resume
from sql_injection_detector import SQLInjectionDetector
from prompt_injection_detector import PromptInjectionDetector
from ats_scorer import ATSScorer

# Set page config
st.set_page_config(
    page_title="Resume SQL Detection & ATS Scorer",
    page_icon="📄",
    layout="wide"
)

@st.cache_resource
def get_sql_detector():
    return SQLInjectionDetector()

@st.cache_resource
def get_prompt_detector():
    return PromptInjectionDetector()

@st.cache_resource
def get_ats_scorer():
    return ATSScorer()


# Title and description
st.title("📄 Resume Security & ATS Scoring System")
st.markdown("""
This application helps you:
1. **Detect SQL injection attempts** in resume files
2. **Detect prompt injection attempts** in resume files
3. **Sanitize resumes** by removing malicious patterns
4. **Calculate ATS scores** to see how well your resume would perform in Applicant Tracking Systems
""")

# Sidebar for options
st.sidebar.header("Options")
sanitize_sql_option = st.sidebar.checkbox(
    "Sanitize SQL injection (remove detected patterns)",
    value=True,
    help="If checked, detected SQL injection patterns will be removed from the resume text before scoring"
)
sanitize_prompt_option = st.sidebar.checkbox(
    "Sanitize prompt injection (remove detected patterns)",
    value=True,
    help="If checked, detected prompt injection patterns will be removed from the resume text before scoring"
)

# File upload section
st.header("📁 Upload Files")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Resume File")
    resume_file = st.file_uploader(
        "Upload your resume (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        key="resume_upload"
    )

with col2:
    st.subheader("Job Description (Optional)")
    job_desc_file = st.file_uploader(
        "Upload job description for better ATS scoring (TXT)",
        type=["txt"],
        key="job_desc_upload"
    )

# Process button
if st.button("🔍 Analyze Resume", type="primary"):
    if resume_file is None:
        st.error("Please upload a resume file.")
    else:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(resume_file.name)[1]) as tmp_resume:
            tmp_resume.write(resume_file.getvalue())
            resume_path = tmp_resume.name

        job_desc_path = None
        if job_desc_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w') as tmp_job:
                tmp_job.write(job_desc_file.getvalue().decode('utf-8'))
                job_desc_path = tmp_job.name

        try:
            # Parse resume
            with st.spinner("Extracting text from resume..."):
                resume_text = parse_resume(resume_path)

            # Display extracted text in an expander
            with st.expander("📄 View Extracted Resume Text"):
                st.text_area("Resume Content", resume_text, height=200, disabled=True)

            # SQL Injection Detection
            with st.spinner("Checking for SQL injection..."):
                sql_detector = get_sql_detector()
                sql_is_malicious, sql_matches = sql_detector.detect(resume_text)

            # Prompt Injection Detection
            with st.spinner("Checking for prompt injection..."):
                prompt_detector = get_prompt_detector()
                prompt_is_malicious, prompt_matches = prompt_detector.detect(resume_text)

            # Display SQL injection results
            st.header("🔒 SQL Injection Analysis")
            if sql_is_malicious:
                st.error(f"⚠️ **SQL Injection Detected!** Found {len(sql_matches)} suspicious pattern(s).")
                with st.expander("View Detected Patterns"):
                    for i, match in enumerate(sql_matches, 1):
                        st.write(f"{i}. `{match}`")
            else:
                st.success("✅ **No SQL injection detected.** Your resume appears to be clean.")

            # Display prompt injection results
            st.header("🛡️ Prompt Injection Analysis")
            if prompt_is_malicious:
                st.error(f"⚠️ **Prompt Injection Detected!** Found {len(prompt_matches)} suspicious pattern(s).")
                with st.expander("View Detected Patterns"):
                    for i, match in enumerate(prompt_matches, 1):
                        st.write(f"{i}. `{match}`")
            else:
                st.success("✅ **No prompt injection detected.** Your resume appears to be clean.")

            # Determine if we need to sanitize and what text to use for scoring
            text_to_score = resume_text
            sanitization_status = []

            if sql_is_malicious and sanitize_sql_option:
                with st.spinner("Sanitizing SQL injection..."):
                    text_to_score = sql_detector.sanitize(text_to_score)
                sanitization_status.append("SQL injection patterns removed")

            if prompt_is_malicious and sanitize_prompt_option:
                with st.spinner("Sanitizing prompt injection..."):
                    text_to_score = prompt_detector.sanitize(text_to_score)
                sanitization_status.append("prompt injection patterns removed")

            # Show sanitization info
            if sanitization_status:
                st.info(f"🧹 Resume has been sanitized: {', '.join(sanitization_status)}.")

                # Show comparison if sanitization occurred
                if sql_is_malicious and sanitize_sql_option or prompt_is_malicious and sanitize_prompt_option:
                    with st.expander("View Sanitized Text"):
                        st.text_area("Sanitized Content", text_to_score, height=200, disabled=True)
            else:
                if sql_is_malicious or prompt_is_malicious:
                    detected_threats = []
                    if sql_is_malicious:
                        detected_threats.append("SQL injection")
                    if prompt_is_malicious:
                        detected_threats.append("prompt injection")

                    threat_str = " and ".join(detected_threats)
                    st.warning(f"⚠️ {threat_str.capitalize()} detected but NOT sanitized (as per your settings).")
                else:
                    st.success("✅ **No security threats detected.** Your resume appears to be clean.")

            # ATS Scoring
            with st.spinner("Calculating ATS score..."):
                job_description = None
                if job_desc_path and os.path.exists(job_desc_path):
                    with open(job_desc_path, 'r', encoding='utf-8') as f:
                        job_description = f.read()

                scorer = get_ats_scorer()
                scores = scorer.score_resume(text_to_score, job_description)

            # Display ATS scores
            st.header("📊 ATS Scoring Results")

            # Create columns for metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="Section Presence",
                    value=f"{scores['section_presence']:.0%}",
                    help="Score based on presence of standard resume sections (contact, experience, education, skills, summary)"
                )

            with col2:
                st.metric(
                    label="Keyword Density",
                    value=f"{scores['keyword_density']:.0%}",
                    help="Score based on density of ATS-relevant keywords"
                )

            with col3:
                st.metric(
                    label="Length Score",
                    value=f"{scores['length']:.0%}",
                    help="Score based on resume length (ideal around 400-800 words)"
                )

            if 'semantic_similarity' in scores:
                with col4:
                    st.metric(
                        label="Job Match",
                        value=f"{scores['semantic_similarity']:.0%}",
                        help="Semantic similarity between resume and job description"
                    )

            # Overall score
            overall_percentage = scores['overall'] * 100
            st.subheader("Overall ATS Score")
            st.progress(scores['overall'])
            st.markdown(f"### {overall_percentage:.1f}%")

            # Interpretation
            if overall_percentage >= 80:
                st.success("🎉 Excellent! Your resume is well-optimized for ATS systems.")
            elif overall_percentage >= 60:
                st.info("👍 Good! Your resume should pass most ATS screenings.")
            elif overall_percentage >= 40:
                st.warning("⚠️ Fair. Consider improving your resume for better ATS compatibility.")
            else:
                st.error("❌ Poor. Your resume may struggle to pass ATS filters. Consider revising.")

            # Detailed scores
            with st.expander("📈 Detailed Scores"):
                st.json(scores)

            # Download results
            results = {
                "resume_file": resume_file.name,
                "sql_injection_detected": sql_is_malicious,
                "sql_injection_matches": sql_matches,
                "prompt_injection_detected": prompt_is_malicious,
                "prompt_injection_matches": prompt_matches,
                "sanitized_sql": sanitize_sql_option and sql_is_malicious,
                "sanitized_prompt": sanitize_prompt_option and prompt_is_malicious,
                "ats_scores": scores,
                "ats_score_percentage": overall_percentage
            }

            st.download_button(
                label="💾 Download Results as JSON",
                data=json.dumps(results, indent=2),
                file_name="resume_analysis_results.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.exception(e)

        finally:
            # Clean up temporary files
            try:
                os.unlink(resume_path)
                if job_desc_path and os.path.exists(job_desc_path):
                    os.unlink(job_desc_path)
            except:
                pass

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Built with ❤️ using Streamlit | For educational purposes only</p>
</div>
""", unsafe_allow_html=True)
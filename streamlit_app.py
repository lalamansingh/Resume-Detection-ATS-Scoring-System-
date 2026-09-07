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
    page_title="Resume Security & ATS Scoring System",
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
4. **Calculate ATS scores** and identify specific resume mistakes against a required Job Description
5. **Get actionable recommendations** on how to increase your ATS score
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

# Input section
st.header("📁 Input Files & Job Description")
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Resume File *(Required)*")
    resume_file = st.file_uploader(
        "Upload your resume (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        key="resume_upload"
    )

with col2:
    st.subheader("2. Job Description *(Mandatory for ATS Scoring)*")
    jd_input_method = st.radio(
        "Select Job Description input method:",
        ["Paste Text", "Upload File"],
        horizontal=True
    )

    job_desc_text = ""
    job_desc_file = None

    if jd_input_method == "Paste Text":
        job_desc_text = st.text_area(
            "Paste the target Job Description:",
            placeholder="Paste requirements, responsibilities, and required skills here...",
            height=160
        )
    else:
        job_desc_file = st.file_uploader(
            "Upload job description file (TXT, PDF, or DOCX)",
            type=["txt", "pdf", "docx"],
            key="job_desc_upload"
        )

# Process button
if st.button("🔍 Analyze Resume & Calculate ATS Score", type="primary"):
    # Validation
    if resume_file is None:
        st.error("❌ Please upload a resume file to proceed.")
    else:
        resume_path = None
        job_desc_path = None
        extracted_job_desc = ""

        # Extract Job Description text if provided
        if jd_input_method == "Paste Text":
            extracted_job_desc = job_desc_text.strip()
        elif job_desc_file is not None:
            suffix = os.path.splitext(job_desc_file.name)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_job:
                tmp_job.write(job_desc_file.getvalue())
                job_desc_path = tmp_job.name
            try:
                extracted_job_desc = parse_resume(job_desc_path).strip()
            except Exception as e:
                st.error(f"Failed to read job description file: {e}")

        # Check mandatory requirement for Job Description
        has_job_desc = bool(extracted_job_desc)

        # Create temporary resume file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(resume_file.name)[1]) as tmp_resume:
            tmp_resume.write(resume_file.getvalue())
            resume_path = tmp_resume.name

        try:
            # 1. Parse resume
            with st.spinner("Extracting text from resume..."):
                resume_text = parse_resume(resume_path)

            # Display extracted text in an expander
            with st.expander("📄 View Extracted Resume Text"):
                st.text_area("Resume Content", resume_text, height=200, disabled=True)

            # 2. Security Analysis: SQL Injection Detection
            with st.spinner("Checking for SQL injection..."):
                sql_detector = get_sql_detector()
                sql_is_malicious, sql_matches = sql_detector.detect(resume_text)

            # 3. Security Analysis: Prompt Injection Detection
            with st.spinner("Checking for prompt injection..."):
                prompt_detector = get_prompt_detector()
                prompt_is_malicious, prompt_matches = prompt_detector.detect(resume_text)

            # Display SQL injection results
            st.header("🔒 Security Analysis")
            sec_col1, sec_col2 = st.columns(2)

            with sec_col1:
                st.subheader("SQL Injection Check")
                if sql_is_malicious:
                    st.error(f"⚠️ **SQL Injection Detected!** Found {len(sql_matches)} suspicious pattern(s).")
                    with st.expander("View Detected SQL Patterns"):
                        for i, match in enumerate(sql_matches, 1):
                            st.code(match, language="sql")
                else:
                    st.success("✅ **No SQL injection detected.**")

            with sec_col2:
                st.subheader("Prompt Injection Check")
                if prompt_is_malicious:
                    st.error(f"⚠️ **Prompt Injection Detected!** Found {len(prompt_matches)} suspicious pattern(s).")
                    with st.expander("View Detected Prompt Injection Patterns"):
                        for i, match in enumerate(prompt_matches, 1):
                            st.code(match)
                else:
                    st.success("✅ **No prompt injection detected.**")

            # Determine text for scoring (with sanitization if enabled)
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

            if sanitization_status:
                st.info(f"🧹 Resume sanitized: {', '.join(sanitization_status)}.")
                with st.expander("View Sanitized Resume Text"):
                    st.text_area("Sanitized Content", text_to_score, height=180, disabled=True)
            elif sql_is_malicious or prompt_is_malicious:
                st.warning("⚠️ Security threats were detected but NOT sanitized based on your options.")

            # 4. ATS Scoring & Weakness Analysis
            st.header("📊 ATS Scoring & Feedback")

            if not has_job_desc:
                st.error("⚠️ **Job Description is Mandatory for ATS Scoring!**")
                st.warning("Please paste or upload a Job Description above so the system can evaluate keyword matching, semantic alignment, and generate improvement tips.")
            else:
                with st.spinner("Evaluating resume against Job Description and calculating ATS score..."):
                    scorer = get_ats_scorer()
                    scores = scorer.score_resume(text_to_score, extracted_job_desc)

                overall_percentage = scores['overall'] * 100

                # Summary Metric & Progress
                st.subheader(f"Overall ATS Score: {overall_percentage:.1f}%")
                st.progress(scores['overall'])

                if overall_percentage >= 80:
                    st.success("🎉 **Excellent!** Your resume is well-optimized and has strong alignment with this job.")
                elif overall_percentage >= 60:
                    st.info("👍 **Good!** Your resume has decent potential but needs targeted improvements.")
                elif overall_percentage >= 40:
                    st.warning("⚠️ **Fair.** Your resume is missing key requirements and sections needed to pass ATS screens.")
                else:
                    st.error("❌ **Poor.** Low alignment with job requirements. High risk of ATS rejection.")

                # Metric Cards
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        label="Section Presence",
                        value=f"{scores['section_presence']:.0%}",
                        help=f"Detected sections: {', '.join(scores['found_sections'])}"
                    )
                with col2:
                    st.metric(
                        label="Skill & Keyword Match",
                        value=f"{scores['keyword_density']:.0%}",
                        help="Match percentage against skills required in the job description"
                    )
                with col3:
                    st.metric(
                        label="Length Score",
                        value=f"{scores['length']:.0%}",
                        help=f"Resume length: {scores['word_count']} words (ideal: 400-800 words)"
                    )
                with col4:
                    st.metric(
                        label="Semantic Similarity",
                        value=f"{scores['semantic_similarity']:.0%}",
                        help="AI contextual alignment between your resume and the job description"
                    )

                # Mistakes / Weaknesses Section ("Kya galti thi isme")
                st.markdown("---")
                st.subheader("❌ Identified Resume Weaknesses ('Kya galti thi isme')")
                st.caption("These issues negatively impacted your ATS score:")

                for mistake in scores['mistakes']:
                    st.error(f"• {mistake}")

                # Score Improvement Guide ("Score ko kaise badha skti hun")
                st.markdown("---")
                st.subheader("💡 How to Increase Your ATS Score ('Score ko kaise badha skti hun')")
                st.caption("Apply these specific changes to boost your score and pass recruiter screening:")

                for rec in scores['recommendations']:
                    st.info(f"👉 {rec}")

                # Skill Comparison Tags
                st.markdown("---")
                st.subheader("🎯 Job Description Skills Breakdown")
                kw_col1, kw_col2 = st.columns(2)

                with kw_col1:
                    st.markdown("##### ✅ Matched Skills (Present in your resume)")
                    if scores['matched_keywords']:
                        tags = " ".join([f"`{k}`" for k in scores['matched_keywords']])
                        st.markdown(tags)
                    else:
                        st.caption("None of the targeted job skills were found.")

                with kw_col2:
                    st.markdown("##### ⚠️ Missing Skills (Add these to your resume)")
                    if scores['missing_keywords']:
                        tags = " ".join([f"`{k}`" for k in scores['missing_keywords']])
                        st.markdown(tags)
                    else:
                        st.caption("Great job! All identified job skills are present.")

                # Detailed JSON View & Download
                with st.expander("📈 View Complete ATS Analysis Data (JSON)"):
                    st.json(scores)

                results = {
                    "resume_file": resume_file.name,
                    "sql_injection_detected": sql_is_malicious,
                    "sql_injection_matches": sql_matches,
                    "prompt_injection_detected": prompt_is_malicious,
                    "prompt_injection_matches": prompt_matches,
                    "ats_scores": scores,
                    "ats_score_percentage": overall_percentage,
                    "mistakes": scores['mistakes'],
                    "recommendations": scores['recommendations']
                }

                st.download_button(
                    label="💾 Download Full Analysis Report as JSON",
                    data=json.dumps(results, indent=2),
                    file_name="resume_ats_analysis_report.json",
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"An error occurred during analysis: {str(e)}")
            st.exception(e)

        finally:
            # Clean up temporary files
            try:
                if resume_path and os.path.exists(resume_path):
                    os.unlink(resume_path)
                if job_desc_path and os.path.exists(job_desc_path):
                    os.unlink(job_desc_path)
            except:
                pass

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Built with ❤️ using Streamlit | AI-Powered Resume Security & ATS Scoring System</p>
</div>
""", unsafe_allow_html=True)
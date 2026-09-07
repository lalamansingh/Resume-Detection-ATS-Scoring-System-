import streamlit as st
import os
import re
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

# Versioned cache keys to ensure fresh code on Streamlit Community Cloud
@st.cache_resource
def get_sql_detector(_v="2026.09.07.v3"):
    return SQLInjectionDetector()

@st.cache_resource
def get_prompt_detector(_v="2026.09.07.v3"):
    return PromptInjectionDetector()

@st.cache_resource
def get_ats_scorer(_v="2026.09.07.v4"):
    return ATSScorer()


# Title and description
st.title("📄 Resume Security & ATS Scoring System")
st.markdown("""
This application helps you:
1. **Detect security vulnerabilities** (SQL & Prompt Injection) in resumes.
2. **Calculate precision ATS score** against a target Job Description.
3. **Analyze weaknesses and mistakes** (*"Kya galti thi isme"*).
4. **Get a detailed action plan** on exactly what to fix to maximize your score (*"Score ko kaise badhaye"*).
""")

# Sidebar for options
st.sidebar.header("⚙️ Settings & Tools")
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

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Clear App Cache & Reload"):
    st.cache_resource.clear()
    st.rerun()

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
if st.button("🔍 Analyze Resume & Generate Detailed Report", type="primary"):
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

            with st.expander("📄 View Extracted Resume Text"):
                st.text_area("Resume Content", resume_text, height=200, disabled=True)

            # 2. Security Analysis
            with st.spinner("Running security checks..."):
                sql_detector = get_sql_detector()
                sql_is_malicious, sql_matches = sql_detector.detect(resume_text)

                prompt_detector = get_prompt_detector()
                prompt_is_malicious, prompt_matches = prompt_detector.detect(resume_text)

            st.header("🔒 Security Analysis")
            sec_col1, sec_col2 = st.columns(2)

            with sec_col1:
                st.subheader("SQL Injection Check")
                if sql_is_malicious:
                    st.error(f"⚠️ **SQL Injection Detected!** Found {len(sql_matches)} pattern(s).")
                    with st.expander("View Detected SQL Patterns"):
                        for i, match in enumerate(sql_matches, 1):
                            st.code(match, language="sql")
                else:
                    st.success("✅ **No SQL injection detected.**")

            with sec_col2:
                st.subheader("Prompt Injection Check")
                if prompt_is_malicious:
                    st.error(f"⚠️ **Prompt Injection Detected!** Found {len(prompt_matches)} pattern(s).")
                    with st.expander("View Detected Prompt Injection Patterns"):
                        for i, match in enumerate(prompt_matches, 1):
                            st.code(match)
                else:
                    st.success("✅ **No prompt injection detected.**")

            # Sanitization if needed
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

            # 3. ATS Scoring & Weakness Analysis
            st.header("📊 ATS Scoring & Performance Analysis")

            if not has_job_desc:
                st.error("⚠️ **Job Description is Mandatory for ATS Scoring!**")
                st.warning("A Job Description is required to calculate keyword density, assess semantic fit, and identify missing qualifications. Please paste or upload a Job Description above.")
            else:
                with st.spinner("Evaluating resume against Job Description..."):
                    scorer = get_ats_scorer()
                    scores = scorer.score_resume(text_to_score, extracted_job_desc)

                # Robust, defensive field retrieval with fallback to avoid any KeyError
                overall = scores.get('overall', 0.0)
                overall_percentage = overall * 100.0 if overall <= 1.0 else overall
                normalized_overall = min(max(overall_percentage / 100.0, 0.0), 1.0)

                section_score = scores.get('section_presence', 0.0)
                keyword_score = scores.get('keyword_density', 0.0)
                length_score = scores.get('length', 0.0)
                semantic_score = scores.get('semantic_similarity', 0.0)

                found_sections = scores.get('found_sections')
                if found_sections is None:
                    sec_patterns = {
                        'contact': r'\b(email|phone|address|linkedin|github)\b',
                        'experience': r'\b(experience|work history|employment|professional experience|work experience)\b',
                        'education': r'\b(education|academic background|qualifications|academic|degree)\b',
                        'skills': r'\b(skills|technical skills|competencies|expertise|technologies)\b',
                        'summary': r'\b(summary|profile|objective|professional summary|about me)\b'
                    }
                    found_sections = [s for s, pat in sec_patterns.items() if re.search(pat, text_to_score, re.I)]

                missing_sections = scores.get('missing_sections')
                if missing_sections is None:
                    sec_keys = ['contact', 'experience', 'education', 'skills', 'summary']
                    missing_sections = [s for s in sec_keys if s not in found_sections]

                matched_keywords = scores.get('matched_keywords', [])
                missing_keywords = scores.get('missing_keywords', [])
                word_count = scores.get('word_count', len(re.findall(r'\b\w+\b', text_to_score)))

                mistakes = scores.get('mistakes', [])
                recommendations = scores.get('recommendations', [])

                # Fallback generator if empty
                if not mistakes or not recommendations:
                    if hasattr(scorer, '_generate_mistakes_and_recommendations'):
                        m, r = scorer._generate_mistakes_and_recommendations(
                            missing_sections=missing_sections,
                            matched_keywords=matched_keywords,
                            missing_keywords=missing_keywords,
                            word_count=word_count,
                            length_score=length_score,
                            semantic_score=semantic_score,
                            keyword_score=keyword_score
                        )
                        mistakes = mistakes or m
                        recommendations = recommendations or r

                # Summary Metric & Progress
                st.subheader(f"Overall ATS Score: {overall_percentage:.1f}%")
                st.progress(normalized_overall)

                if overall_percentage >= 80:
                    st.success("🎉 **Excellent!** Your resume is strongly aligned with this job description.")
                elif overall_percentage >= 60:
                    st.info("👍 **Good!** Your resume is viable but targeted adjustments can push it to top-tier.")
                elif overall_percentage >= 40:
                    st.warning("⚠️ **Fair.** Several core qualifications and sections are missing. High risk of ATS filtering.")
                else:
                    st.error("❌ **Poor.** Low keyword and semantic match. Substantial revisions required.")

                # Metric Cards
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    sections_tooltip = ", ".join(found_sections) if found_sections else "None detected"
                    st.metric(
                        label="Section Presence",
                        value=f"{section_score:.0%}",
                        help=f"Detected sections: {sections_tooltip}"
                    )
                with col2:
                    st.metric(
                        label="Skill & Keyword Match",
                        value=f"{keyword_score:.0%}",
                        help=f"Matched {len(matched_keywords)} target skills from Job Description"
                    )
                with col3:
                    st.metric(
                        label="Length Score",
                        value=f"{length_score:.0%}",
                        help=f"Current word count: {word_count} words (ideal: 400-800 words)"
                    )
                with col4:
                    st.metric(
                        label="Semantic Similarity",
                        value=f"{semantic_score:.0%}",
                        help="AI semantic embedding similarity between your resume and the job description"
                    )

                # =========================================================================
                # DETAILED REPORT & ACTION PLAN ("Kya chheze shii karke score badha skta hun")
                # =========================================================================
                st.markdown("---")
                st.header("📋 Detailed Score Improvement Report & Action Plan")
                st.markdown("**Exactly what is holding back your resume and how to fix each component to reach 90%+ ATS Score:**")

                report_tab1, report_tab2, report_tab3, report_tab4 = st.tabs([
                    "❌ Mistakes Found ('Kya Galti Thi')",
                    "💡 Action Plan to Boost Score",
                    "🎯 Skills & Keywords Audit",
                    "📑 Section-by-Section Review"
                ])

                with report_tab1:
                    st.subheader("Identified Weaknesses & Errors in Resume")
                    if mistakes:
                        for i, mistake in enumerate(mistakes, 1):
                            st.error(f"**{i}.** {mistake}")
                    else:
                        st.success("✅ No critical faults found! Your resume aligns well with standard requirements.")

                with report_tab2:
                    st.subheader("Step-by-Step Fixes to Boost Your Score")
                    st.markdown("Follow this prioritized checklist to immediately boost your ATS ranking:")

                    step_num = 1
                    # 1. Section additions
                    if missing_sections:
                        st.markdown(f"#### Step {step_num}: Add Missing Mandatory Sections (+25% Score Impact)")
                        for s in missing_sections:
                            if s == 'contact':
                                st.info("• **Contact Information**: Place email, phone number, LinkedIn URL, and GitHub portfolio at the very top.")
                            elif s == 'summary':
                                st.info("• **Professional Summary**: Add a 2-3 line summary tailored specifically to the position.")
                            elif s == 'experience':
                                st.info("• **Work Experience**: Include job titles, company names, employment dates, and achievement bullets.")
                            elif s == 'education':
                                st.info("• **Education**: List degree name, institution name, and graduation year clearly.")
                            elif s == 'skills':
                                st.info("• **Skills Section**: Create a categorized section: Programming Languages, Frameworks, Cloud/DevOps, Databases.")
                        step_num += 1

                    # 2. Keyword additions
                    if missing_keywords:
                        st.markdown(f"#### Step {step_num}: Incorporate Missing Job Keywords (+30% Score Impact)")
                        st.warning(f"ATS parsers scan for exact matches from the job posting. Add these **{len(missing_keywords)} missing skills** where applicable:")
                        st.code(", ".join(missing_keywords), language="text")
                        st.markdown("**Where to place them:**")
                        st.markdown("- Add technical skills into your **Skills** section.")
                        st.markdown("- Integrate them into project bullet points showing **context and impact** (e.g. *'Built scalable APIs using FastAPI and deployed with Docker on AWS'*).")
                        step_num += 1

                    # 3. Word count & length
                    st.markdown(f"#### Step {step_num}: Optimize Word Count & Density (+15% Score Impact)")
                    if word_count < 400:
                        needed_words = 450 - word_count
                        st.warning(f"• **Your resume is currently {word_count} words.** Expand by approximately **+{needed_words} words**.")
                        st.markdown("  - Detail 2-3 projects with architecture, challenges, and measurable results.")
                        st.markdown("  - Add quantifiable impact metrics (e.g., *'Improved system latency by 28%'*, *'Handled 10k+ daily users'*).")
                    elif word_count > 1000:
                        trim_words = word_count - 800
                        st.warning(f"• **Your resume is currently {word_count} words.** Condense by approximately **-{trim_words} words**.")
                        st.markdown("  - Remove older or irrelevant internships and older school achievements.")
                        st.markdown("  - Keep work bullets concise (maximum 3-4 high-impact bullets per role).")
                    else:
                        st.success(f"• **Word count is ideal ({word_count} words).** Length is in the sweet spot (400-800 words).")
                    step_num += 1

                    # 4. Semantic similarity
                    st.markdown(f"#### Step {step_num}: Align Phrasing with Job Responsibilities (+30% Score Impact)")
                    st.info("• **Mirror the Job Description Language**: Modern AI-based ATS systems use semantic vector embeddings. Rephrase your bullet points using the same action verbs, methodology terms (e.g., 'Agile', 'CI/CD pipelines'), and phrasing found in the job posting.")

                with report_tab3:
                    st.subheader("Target Job Description Skills Breakdown")
                    kcol1, kcol2 = st.columns(2)

                    with kcol1:
                        st.markdown("##### ✅ Matched Skills (Present in your resume)")
                        if matched_keywords:
                            st.success(f"**Found {len(matched_keywords)} matching skills:**")
                            st.markdown(" ".join([f"`{k}`" for k in matched_keywords]))
                        else:
                            st.warning("No target skills from the job description were found in your resume.")

                    with kcol2:
                        st.markdown("##### ⚠️ Missing Skills (Add these to your resume)")
                        if missing_keywords:
                            st.error(f"**Missing {len(missing_keywords)} requested skills:**")
                            st.markdown(" ".join([f"`{k}`" for k in missing_keywords]))
                        else:
                            st.success("🎉 Excellent! Your resume contains all core skills found in the job description.")

                with report_tab4:
                    st.subheader("Standard ATS Section Audit")
                    st.markdown("Applicant Tracking Systems require standard section headers to parse your background properly:")

                    standard_secs = [
                        ('contact', 'Contact Information (Email, Phone, Links)'),
                        ('summary', 'Professional Summary / Objective'),
                        ('experience', 'Work Experience / Employment History'),
                        ('education', 'Education & Qualifications'),
                        ('skills', 'Skills & Technical Competencies')
                    ]

                    for sec_id, sec_label in standard_secs:
                        if sec_id in found_sections:
                            st.success(f"✅ **{sec_label}**: Present")
                        else:
                            st.error(f"❌ **{sec_label}**: Missing — *Add this section to improve score*")

                # Printable/Downloadable Improvement Plan
                st.markdown("---")
                st.subheader("📥 Download Your Custom Improvement Report")

                txt_report = f"""=======================================================
RESUME SECURITY & ATS SCORING REPORT
=======================================================
Resume File: {resume_file.name}
Overall ATS Score: {overall_percentage:.1f}%

SECURITY CHECKS:
- SQL Injection Detected: {sql_is_malicious}
- Prompt Injection Detected: {prompt_is_malicious}

ATS SUB-SCORES:
- Section Presence Score: {section_score:.0%}
- Skill & Keyword Match: {keyword_score:.0%}
- Length Score: {length_score:.0%} (Word Count: {word_count} words)
- Semantic Similarity: {semantic_score:.0%}

IDENTIFIED WEAKNESSES ("Kya Galti Thi"):
{chr(10).join([f"- {m}" for m in mistakes])}

ACTION PLAN TO MAXIMIZE SCORE ("Score Kaise Badhaye"):
{chr(10).join([f"{i}. {r}" for i, r in enumerate(recommendations, 1)])}

SKILLS AUDIT:
- Matched Skills: {', '.join(matched_keywords) if matched_keywords else 'None'}
- Missing Skills to Add: {', '.join(missing_keywords) if missing_keywords else 'None'}
- Sections Present: {', '.join(found_sections) if found_sections else 'None'}
- Sections Missing: {', '.join(missing_sections) if missing_sections else 'None'}
=======================================================
"""
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    st.download_button(
                        label="📄 Download Action Plan (TXT Report)",
                        data=txt_report,
                        file_name="resume_improvement_action_plan.txt",
                        mime="text/plain"
                    )
                with r_col2:
                    json_export = {
                        "resume_file": resume_file.name,
                        "overall_ats_score": round(overall_percentage, 1),
                        "section_presence_score": round(section_score * 100, 1),
                        "keyword_match_score": round(keyword_score * 100, 1),
                        "length_score": round(length_score * 100, 1),
                        "semantic_similarity_score": round(semantic_score * 100, 1),
                        "word_count": word_count,
                        "found_sections": found_sections,
                        "missing_sections": missing_sections,
                        "matched_keywords": matched_keywords,
                        "missing_keywords": missing_keywords,
                        "mistakes": mistakes,
                        "actionable_recommendations": recommendations
                    }
                    st.download_button(
                        label="💾 Download Full Data (JSON)",
                        data=json.dumps(json_export, indent=2),
                        file_name="ats_report.json",
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
# Resume Security & ATS Scoring System

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=lalamansingh/Resume-Detection-ATS-Scoring-System-&branch=main&mainModule=streamlit_app.py)

An intelligent, AI-powered system to detect security threats (SQL Injection and Prompt Injection) in resumes, calculate precision ATS (Applicant Tracking System) scores against a target Job Description, identify specific resume mistakes, and provide actionable recommendations to boost your score.

---

## 🚀 Key Features

- **Resume & Job Description Parsing**: Extract clean text from PDF, DOCX, and TXT files.
- **Security Threat Detection**:
  - **SQL Injection Detection**: Detects SQL injection attempts in resume content.
  - **Prompt Injection Detection**: Identifies adversarial prompts aimed at manipulating downstream LLM screening systems.
  - **Text Sanitization**: Automatically strips malicious patterns before scoring.
- **Mandatory Job Description Matching**:
  - Evaluates resume directly against the job requirements (paste text or upload file).
  - Identifies **Matched Skills** vs **Missing Skills** required by the role.
- **Resume Mistake & Weakness Analysis ("Kya galti thi isme")**:
  - Detects missing core sections (`Contact`, `Experience`, `Education`, `Skills`, `Summary`).
  - Flags missing critical keywords and technologies found in the job description.
  - Assesses word count (flags resumes that are too brief or excessively long).
  - Flags low contextual semantic similarity.
- **Actionable Score Improvement Guide ("Score ko kaise badha skti hun")**:
  - Concrete suggestions on which keywords to incorporate.
  - Specific section additions and restructuring advice.
  - Optimal length guidance (recommended 400–800 words).
  - High-impact bullet point phrasing tips.

---

## 📦 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/lalamansingh/Resume-Detection-ATS-Scoring-System-.git
   cd Resume-Detection-ATS-Scoring-System-
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🖥️ Usage

### Web Application (Streamlit)

Launch the interactive web UI:

```bash
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser:
1. Upload your resume (`.pdf`, `.docx`, or `.txt`).
2. Provide the target Job Description (paste text or upload file).
3. Click **"Analyze Resume & Calculate ATS Score"**.
4. View detected security threats, ATS scores, identified weaknesses, and improvement recommendations.
5. Download the complete analysis report as JSON.

### Command Line Interface (CLI)

To analyze a resume and compute ATS score against a job description:

```bash
python main.py sample_resume.txt --job_desc sample_job.txt
```

To save results to JSON:

```bash
python main.py sample_resume.txt --job_desc sample_job.txt --output result.json
```

---

## 📊 Sample Output

```json
{
  "resume_file": "sample_resume.txt",
  "sql_injection_detected": false,
  "sql_injection_matches": [],
  "prompt_injection_detected": false,
  "prompt_injection_matches": [],
  "sanitized": false,
  "ats_score_percentage": 85.0,
  "mistakes": [
    "Missing Job Description Skills: Found 1 skills/technologies mentioned in the job description that are absent from your resume: agile.",
    "Resume Too Brief: Your resume has only 85 words (ideal length is 400-800 words)."
  ],
  "recommendations": [
    "Incorporate these key skills from the job description naturally into your Skills and Experience bullet points: agile.",
    "Expand your resume to at least 400-600 words. Add details on project scope, tools used, and measurable outcomes.",
    "Use clear bullet points starting with strong action verbs and quantify results with metrics."
  ]
}
```

---

## 📜 License

MIT License
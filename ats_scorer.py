import re
import logging
from typing import List, Dict, Optional, Any, Tuple
import numpy as np

# Try to import sentence-transformers for semantic similarity
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not installed. Semantic similarity scoring will be disabled.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ATSScorer:
    def __init__(self):
        # Define common sections to look for in a resume
        self.sections = {
            'contact': ['email', 'phone', 'address', 'linkedin', 'github'],
            'experience': ['experience', 'work history', 'employment', 'professional experience', 'work experience'],
            'education': ['education', 'academic background', 'qualifications', 'academic', 'degree'],
            'skills': ['skills', 'technical skills', 'competencies', 'expertise', 'core competencies', 'technologies'],
            'summary': ['summary', 'profile', 'objective', 'professional summary', 'about me']
        }
        # Compile regex patterns for section detection (case-insensitive)
        self.section_patterns = {}
        for section, keywords in self.sections.items():
            pattern = r'\b(' + '|'.join(keywords) + r')\b'
            self.section_patterns[section] = re.compile(pattern, re.IGNORECASE)

        # Common tech and professional keywords catalog for matching
        self.at_keywords = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go', 'rust',
            'html', 'css', 'react', 'angular', 'vue', 'node.js', 'next.js', 'django', 'flask', 'fastapi', 'spring',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'nosql', 'oracle', 'sqlite',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'ci/cd', 'jenkins', 'git', 'github', 'devops', 'linux',
            'machine learning', 'deep learning', 'nlp', 'ai', 'artificial intelligence', 'computer vision',
            'data analysis', 'data science', 'pandas', 'numpy', 'scikit-learn', 'pytorch', 'tensorflow',
            'rest api', 'graphql', 'microservices', 'system design', 'distributed systems', 'agile', 'scrum',
            'management', 'leadership', 'communication', 'problem solving', 'teamwork', 'collaboration',
            'project management', 'analytics', 'reporting', 'optimization', 'debugging', 'testing', 'unit testing'
        ]
        self.keyword_pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in self.at_keywords) + r')\b', re.IGNORECASE)

        # Initialize sentence transformer model if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"Failed to load sentence-transformers model: {e}")
                self.model = None
        else:
            self.model = None

    def _score_section_presence(self, text: str) -> Tuple[float, List[str], List[str]]:
        """
        Score based on presence of standard resume sections.
        Returns:
            score (float): 0.0 - 1.0
            found_sections (list): List of detected section names
            missing_sections (list): List of missing section names
        """
        found_sections = []
        missing_sections = []
        for section, pattern in self.section_patterns.items():
            if pattern.search(text):
                found_sections.append(section)
            else:
                missing_sections.append(section)

        score = len(found_sections) / len(self.sections)
        logger.info(f"Section presence score: {score:.2f} (found {len(found_sections)}/{len(self.sections)} sections)")
        return score, found_sections, missing_sections

    def _extract_jd_keywords(self, job_description: str) -> List[str]:
        """
        Extract relevant skills/keywords present in the Job Description.
        """
        jd_lower = job_description.lower()
        found_jd_keywords = []
        for kw in self.at_keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, jd_lower):
                found_jd_keywords.append(kw)

        # Also extract any words with uppercase letters or tech acronyms from JD (e.g. AWS, CI/CD, ETL, Kafka)
        acronyms = set(re.findall(r'\b[A-Z]{2,6}\b', job_description))
        common_stop_acronyms = {'THE', 'AND', 'FOR', 'ARE', 'WITH', 'FROM', 'THIS', 'THAT', 'HAVE', 'WILL', 'YOUR'}
        valid_acronyms = [a.lower() for a in acronyms if a not in common_stop_acronyms]
        for a in valid_acronyms:
            if a not in found_jd_keywords and len(a) >= 2:
                found_jd_keywords.append(a)

        return sorted(list(set(found_jd_keywords)))

    def _match_keywords(self, resume_text: str, jd_keywords: List[str]) -> Tuple[List[str], List[str]]:
        """
        Match JD keywords against resume text.
        Returns:
            matched (list): keywords found in both JD and resume
            missing (list): keywords found in JD but missing in resume
        """
        resume_lower = resume_text.lower()
        matched = []
        missing = []

        for kw in jd_keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, resume_lower):
                matched.append(kw)
            else:
                missing.append(kw)

        return matched, missing

    def _score_keyword_density(self, text: str, jd_keywords: Optional[List[str]] = None) -> Tuple[float, List[str], List[str]]:
        """
        Score based on density of ATS-relevant keywords and match with JD keywords.
        Returns:
            score (float): 0.0 - 1.0
            matched_keywords (list)
            missing_keywords (list)
        """
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0, [], []

        if jd_keywords:
            matched, missing = self._match_keywords(text, jd_keywords)
            match_ratio = len(matched) / len(jd_keywords) if jd_keywords else 0.0
            density_matches = self.keyword_pattern.findall(text.lower())
            general_density = min((len(density_matches) / len(words)) / 0.15, 1.0)
            score = 0.7 * match_ratio + 0.3 * general_density
            return min(score, 1.0), matched, missing
        else:
            density_matches = self.keyword_pattern.findall(text.lower())
            density = len(density_matches) / len(words)
            score = min(density / 0.15, 1.0)
            return score, [], []

    def _score_length(self, text: str) -> Tuple[float, int]:
        """
        Score based on resume length (word count).
        Ideal resume length is around 400-800 words.
        Returns:
            score (float): 0.0 - 1.0
            word_count (int)
        """
        word_count = len(re.findall(r'\b\w+\b', text))
        if word_count < 100:
            score = word_count / 100.0
        elif word_count > 1000:
            score = max(0.0, 1.0 - (word_count - 1000) / 1000.0)
        else:
            # Optimal around 600 words
            score = 1.0 - abs(word_count - 600) / 400.0
            score = max(0.0, min(score, 1.0))
        logger.info(f"Length score: {score:.2f} (word count: {word_count})")
        return score, word_count

    def _score_semantic_similarity(self, resume_text: str, job_description: str) -> float:
        """
        Score based on semantic similarity between resume and job description.
        Returns a score between 0 and 1 (cosine similarity).
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE or self.model is None:
            logger.warning("Sentence transformer model not available. Returning 0.0 for semantic similarity.")
            return 0.0
        if not job_description or not job_description.strip():
            return 0.0
        try:
            resume_embedding = self.model.encode(resume_text, convert_to_tensor=True)
            job_embedding = self.model.encode(job_description, convert_to_tensor=True)
            cosine_score = util.pytorch_cos_sim(resume_embedding, job_embedding)
            score = max(0.0, float(cosine_score.item()))
            logger.info(f"Semantic similarity score: {score:.2f}")
            return score
        except Exception as e:
            logger.error(f"Error computing semantic similarity: {e}")
            return 0.0

    def _generate_mistakes_and_recommendations(
        self,
        missing_sections: List[str],
        matched_keywords: List[str],
        missing_keywords: List[str],
        word_count: int,
        length_score: float,
        semantic_score: float,
        keyword_score: float
    ) -> Tuple[List[str], List[str]]:
        """
        Analyze mistakes/weaknesses in the resume and generate actionable recommendations to increase score.
        """
        mistakes = []
        recommendations = []

        # 1. Section Presence Analysis
        if missing_sections:
            formatted_missing = [s.capitalize() for s in missing_sections]
            mistakes.append(
                f"Missing Essential Section(s): Resume is missing {', '.join(formatted_missing)} section(s). ATS parsers require standard section headers to classify your information."
            )
            for s in missing_sections:
                if s == 'contact':
                    recommendations.append("Add a Contact section at the top with Email, Phone Number, LinkedIn, and GitHub profile links.")
                elif s == 'experience':
                    recommendations.append("Add an Experience section detailing your work history, company names, job titles, and quantifiable achievements.")
                elif s == 'education':
                    recommendations.append("Add an Education section specifying your degree, institution, graduation year, and relevant coursework.")
                elif s == 'skills':
                    recommendations.append("Add a dedicated Skills / Technical Competencies section categorizing your programming languages, frameworks, databases, and tools.")
                elif s == 'summary':
                    recommendations.append("Include a 2-3 line Professional Summary at the beginning summarizing your expertise and value proposition for this role.")

        # 2. Missing Keywords from Job Description
        if missing_keywords:
            top_missing = missing_keywords[:8]
            mistakes.append(
                f"Missing Job Description Skills: Found {len(missing_keywords)} skills/technologies mentioned in the job description that are absent from your resume: {', '.join(top_missing)}."
            )
            recommendations.append(
                f"Incorporate these key skills from the job description naturally into your Skills and Experience bullet points: {', '.join(top_missing)}."
            )

        # 3. Word Count / Length Analysis
        if word_count < 400:
            mistakes.append(
                f"Resume Too Brief: Your resume has only {word_count} words (ideal length is 400-800 words). It likely lacks sufficient project details and impact metrics."
            )
            recommendations.append(
                f"Expand your resume to at least 400-600 words. Add details on project scope, tools used, problems solved, and measurable outcomes (e.g. 'Reduced load time by 35%')."
            )
        elif word_count > 1000:
            mistakes.append(
                f"Resume Too Long: Your resume contains {word_count} words (ideal length is 400-800 words). Lengthy multi-page resumes may dilute keyword density or get truncated."
            )
            recommendations.append(
                f"Condense your resume to 400-800 words by cutting outdated or non-relevant experience, focusing on high-impact accomplishments from the last 3-5 years."
            )
        else:
            recommendations.append(
                f"Good resume length ({word_count} words). Continue maintaining concise, high-impact bullet points."
            )

        # 4. Semantic Similarity / Role Alignment
        if semantic_score < 0.50:
            mistakes.append(
                f"Low Contextual Alignment ({semantic_score:.0%}): The overall language and focus of your resume deviate significantly from the job description."
            )
            recommendations.append(
                "Align your resume's terminology with the job description. Rephrase your achievements using the same action verbs and terminology used in the job requirements."
            )
        elif semantic_score < 0.70:
            recommendations.append(
                f"Moderate job alignment ({semantic_score:.0%}). Mirror exact phrases and responsibilities from the job posting in your project descriptions to push similarity above 75%."
            )

        # 5. Formatting & ATS Parsing Tips
        recommendations.append(
            "Use clear bullet points starting with strong action verbs (e.g., 'Architected', 'Spearheaded', 'Optimized', 'Automated') and quantify your results with metrics/percentages."
        )

        if not mistakes:
            mistakes.append("No major faults found! Your resume closely matches standard ATS criteria and the job description.")

        return mistakes, recommendations

    def score_resume(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Compute ATS score for a resume against a mandatory job description.
        Returns a dictionary with individual scores, overall score, mistakes, and recommendations.

        Raises:
            ValueError: If job_description is not provided or is empty.
        """
        if not job_description or not job_description.strip():
            raise ValueError("Job description is mandatory for ATS scoring. Please provide a job description.")

        # 1. Section presence score
        section_score, found_sections, missing_sections = self._score_section_presence(resume_text)

        # 2. Extract JD keywords and match
        jd_keywords = self._extract_jd_keywords(job_description)
        keyword_score, matched_keywords, missing_keywords = self._score_keyword_density(resume_text, jd_keywords)

        # 3. Length score
        length_score, word_count = self._score_length(resume_text)

        # 4. Semantic similarity
        semantic_score = self._score_semantic_similarity(resume_text, job_description)

        # Overall score: weighted combination
        # Section Presence: 25%, Keyword/Skill Match: 30%, Length: 15%, Semantic Similarity: 30%
        overall = (
            0.25 * section_score +
            0.30 * keyword_score +
            0.15 * length_score +
            0.30 * semantic_score
        )

        # 5. Analyze mistakes and generate recommendations
        mistakes, recommendations = self._generate_mistakes_and_recommendations(
            missing_sections=missing_sections,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            word_count=word_count,
            length_score=length_score,
            semantic_score=semantic_score,
            keyword_score=keyword_score
        )

        scores = {
            'section_presence': section_score,
            'keyword_density': keyword_score,
            'length': length_score,
            'semantic_similarity': semantic_score,
            'overall': round(overall, 4),
            'word_count': word_count,
            'found_sections': found_sections,
            'missing_sections': missing_sections,
            'jd_keywords': jd_keywords,
            'matched_keywords': matched_keywords,
            'missing_keywords': missing_keywords,
            'mistakes': mistakes,
            'recommendations': recommendations
        }

        logger.info(f"ATS scores computed. Overall: {overall:.2%}, Mistakes: {len(mistakes)}, Recommendations: {len(recommendations)}")
        return scores

    def get_ats_score_percentage(self, resume_text: str, job_description: str) -> float:
        """
        Returns the overall ATS score as a percentage (0-100).
        """
        scores = self.score_resume(resume_text, job_description)
        return scores['overall'] * 100

if __name__ == "__main__":
    scorer = ATSScorer()
    sample_resume = """
    John Doe
    Email: john.doe@example.com
    Phone: 555-123-4567

    SUMMARY
    Experienced software engineer with 5 years of experience in web development.

    EXPERIENCE
    Software Engineer at ABC Corp (2020-Present)
    - Developed web applications using JavaScript, React, and Node.js.
    - Collaborated with cross-functional teams to deliver projects on time.

    EDUCATION
    Bachelor of Science in Computer Science
    XYZ University, 2015-2019

    SKILLS
    JavaScript, React, Node.js, HTML, CSS, SQL, Python
    """
    job_desc = """
    We are looking for a Senior Software Engineer with experience in JavaScript, React, Node.js, Docker, Kubernetes, AWS, and TypeScript.
    The candidate will lead system design, microservices architecture, and CI/CD automation.
    """
    res = scorer.score_resume(sample_resume, job_desc)
    print("Scores:", res['overall'])
    print("Mistakes:", res['mistakes'])
    print("Recommendations:", res['recommendations'])
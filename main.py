import os
import sys
import logging
import argparse
import json

from resume_parser import parse_resume
from sql_injection_detector import SQLInjectionDetector
from prompt_injection_detector import PromptInjectionDetector
from ats_scorer import ATSScorer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Detect security threats in resumes, compute ATS score, identify mistakes, and provide improvement recommendations.')
    parser.add_argument('resume_file', help='Path to the resume file (PDF, DOCX, TXT)')
    parser.add_argument('--job_desc', help='Path to job description file (TXT, PDF, DOCX) - MANDATORY for ATS scoring', default=None)
    parser.add_argument('--output', help='Output file to save results (JSON format)', default=None)
    parser.add_argument('--no_sanitize', action='store_true', help='Do not sanitize detected threats (only detect)')
    args = parser.parse_args()

    logger.info(f"Processing resume: {args.resume_file}")

    # Step 1: Parse resume
    try:
        resume_text = parse_resume(args.resume_file)
        logger.info(f"Resume text extracted, length: {len(resume_text)} characters")
    except Exception as e:
        logger.error(f"Failed to parse resume: {e}")
        sys.exit(1)

    # Step 2: Detect and sanitize SQL injection
    sql_detector = SQLInjectionDetector()
    sql_is_malicious, sql_matches = sql_detector.detect(resume_text)
    logger.info(f"SQL injection detected: {sql_is_malicious}")
    if sql_matches:
        logger.info(f"SQL Matches: {sql_matches}")

    # Step 3: Detect and sanitize Prompt injection
    prompt_detector = PromptInjectionDetector()
    prompt_is_malicious, prompt_matches = prompt_detector.detect(resume_text)
    logger.info(f"Prompt injection detected: {prompt_is_malicious}")
    if prompt_matches:
        logger.info(f"Prompt Matches: {prompt_matches}")

    # Sanitization
    text_to_score = resume_text
    if not args.no_sanitize:
        if sql_is_malicious:
            text_to_score = sql_detector.sanitize(text_to_score)
        if prompt_is_malicious:
            text_to_score = prompt_detector.sanitize(text_to_score)

    # Step 4: Compute ATS score (Requires Job Description)
    scores = None
    mistakes = []
    recommendations = []

    if args.job_desc:
        if os.path.exists(args.job_desc):
            try:
                job_desc_text = parse_resume(args.job_desc)
                scorer = ATSScorer()
                scores = scorer.score_resume(text_to_score, job_desc_text)
                mistakes = scores.get('mistakes', [])
                recommendations = scores.get('recommendations', [])
                logger.info(f"ATS Score: {scores['overall'] * 100:.1f}%")
            except Exception as e:
                logger.error(f"Error computing ATS score: {e}")
        else:
            logger.error(f"Job description file not found: {args.job_desc}")
    else:
        logger.warning("Job description (--job_desc) was not provided. ATS scoring was skipped because a Job Description is mandatory.")

    # Step 5: Prepare output
    result = {
        'resume_file': args.resume_file,
        'sql_injection_detected': sql_is_malicious,
        'sql_injection_matches': sql_matches,
        'prompt_injection_detected': prompt_is_malicious,
        'prompt_injection_matches': prompt_matches,
        'sanitized': not args.no_sanitize and (sql_is_malicious or prompt_is_malicious),
        'ats_scores': scores,
        'ats_score_percentage': scores['overall'] * 100 if scores else None,
        'mistakes': mistakes,
        'recommendations': recommendations
    }

    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        except Exception as e:
            logger.error(f"Failed to write output file: {e}")
    else:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
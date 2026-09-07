import unittest
from ats_scorer import ATSScorer

class TestATSFeedback(unittest.TestCase):
    def setUp(self):
        self.scorer = ATSScorer()

    def test_mandatory_job_description(self):
        """Test that missing or empty job description raises ValueError."""
        resume = "Some resume text"
        with self.assertRaises(ValueError):
            self.scorer.score_resume(resume, "")

        with self.assertRaises(ValueError):
            self.scorer.score_resume(resume, "   ")

        with self.assertRaises(ValueError):
            self.scorer.score_resume(resume, None)

    def test_missing_sections_and_keywords(self):
        """Test that missing sections and missing JD keywords are detected."""
        # Resume has SQL and Python, but missing Java, Docker, Kubernetes, AWS
        resume = """
        Contact: test@example.com
        Experience:
        Software Engineer at XYZ
        Worked with SQL and Python databases.
        Skills:
        SQL, Python
        """
        # Job description requires Java, Docker, Kubernetes, AWS, SQL
        jd = """
        Looking for a Senior Cloud Engineer with experience in Java, Docker, Kubernetes, AWS, and SQL.
        Must have good communication skills.
        """
        scores = self.scorer.score_resume(resume, jd)
        self.assertIn('overall', scores)
        self.assertIn('mistakes', scores)
        self.assertIn('recommendations', scores)

        # Check missing sections
        self.assertIn('education', scores['missing_sections'])
        self.assertIn('summary', scores['missing_sections'])

        # Check missing keywords
        missing_kw = scores['missing_keywords']
        for kw in ['docker', 'kubernetes', 'aws']:
            self.assertIn(kw, missing_kw)

        # Check matched keywords
        self.assertIn('sql', scores['matched_keywords'])

        # Verify mistakes and recommendations lists are non-empty
        self.assertTrue(len(scores['mistakes']) > 0)
        self.assertTrue(len(scores['recommendations']) > 0)

        # Check word count
        self.assertTrue(scores['word_count'] < 400)
        # Verify length mistake reported
        mistakes_str = " ".join(scores['mistakes'])
        self.assertIn("Resume Too Brief", mistakes_str)
        self.assertIn("Missing Essential Section", mistakes_str)
        self.assertIn("Missing Job Description Skills", mistakes_str)

if __name__ == "__main__":
    unittest.main()

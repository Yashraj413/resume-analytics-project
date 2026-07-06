"""
NLP Engine — Skill Extraction, Resume Parsing, and Text Processing
Uses a hybrid approach: rule-based matching (no GPU required) + TF-IDF similarity
Falls back gracefully if spaCy model not available.
"""

import re
import json
import math
from typing import Optional
from collections import defaultdict

# ──────────────────────────────────────────────
# Master Skills Taxonomy (expandable)
# ──────────────────────────────────────────────

SKILLS_TAXONOMY = {
    "Python": "programming",
    "R": "programming",
    "SQL": "programming",
    "Scala": "programming",
    "Java": "programming",
    "Julia": "programming",
    "SAS": "programming",
    "MATLAB": "programming",
    "C++": "programming",
    "JavaScript": "programming",
    "TensorFlow": "ml_frameworks",
    "PyTorch": "ml_frameworks",
    "Scikit-learn": "ml_frameworks",
    "Keras": "ml_frameworks",
    "XGBoost": "ml_frameworks",
    "LightGBM": "ml_frameworks",
    "CatBoost": "ml_frameworks",
    "MLflow": "ml_frameworks",
    "Hugging Face": "nlp",
    "BERT": "nlp",
    "GPT": "nlp",
    "NLTK": "nlp",
    "spaCy": "nlp",
    "LangChain": "nlp",
    "Transformers": "nlp",
    "Pandas": "data_tools",
    "NumPy": "data_tools",
    "Spark": "data_tools",
    "PySpark": "data_tools",
    "Hadoop": "data_tools",
    "Kafka": "data_tools",
    "Airflow": "data_tools",
    "dbt": "data_tools",
    "Power BI": "visualization",
    "Tableau": "visualization",
    "Matplotlib": "visualization",
    "Seaborn": "visualization",
    "Plotly": "visualization",
    "Looker": "visualization",
    "Grafana": "visualization",
    "Excel": "visualization",
    "MySQL": "databases",
    "PostgreSQL": "databases",
    "MongoDB": "databases",
    "Redis": "databases",
    "Snowflake": "databases",
    "BigQuery": "databases",
    "Redshift": "databases",
    "SQLite": "databases",
    "Oracle": "databases",
    "Cassandra": "databases",
    "AWS": "cloud",
    "GCP": "cloud",
    "Azure": "cloud",
    "Docker": "cloud",
    "Kubernetes": "cloud",
    "Terraform": "cloud",
    "Git": "devops",
    "GitHub": "devops",
    "CI/CD": "devops",
    "Jenkins": "devops",
    "Statistics": "analytical",
    "Machine Learning": "analytical",
    "Deep Learning": "analytical",
    "Time Series": "analytical",
    "A/B Testing": "analytical",
    "Data Modeling": "analytical",
    "Feature Engineering": "analytical",
    "Natural Language Processing": "analytical",
    "Computer Vision": "analytical",
    "Communication": "soft_skills",
    "Problem Solving": "soft_skills",
    "Team Leadership": "soft_skills",
    "Stakeholder Management": "soft_skills",
    "Agile": "soft_skills",
    "Scrum": "soft_skills",
    "Project Management": "soft_skills",
}

# Lowercase lookup for fast matching
_SKILL_LOWER_MAP = {k.lower(): k for k in SKILLS_TAXONOMY}

# Aliases / synonyms → canonical skill
SKILL_ALIASES = {
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "pyspark": "PySpark",
    "natural language processing": "Natural Language Processing",
    "nlp": "Natural Language Processing",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "ab testing": "A/B Testing",
    "amazon web services": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "microsoft azure": "Azure",
    "hf": "Hugging Face",
    "huggingface": "Hugging Face",
    "k8s": "Kubernetes",
}


# ──────────────────────────────────────────────
# Core NLP Utilities
# ──────────────────────────────────────────────

class ResumeNLPEngine:
    """
    Hybrid NLP engine for resume parsing and skill extraction.
    No GPU or large model dependency — uses regex + vocabulary matching.
    Optional: plug in spaCy for enhanced NER.
    """

    def __init__(self, use_spacy: bool = True):
        self.use_spacy = use_spacy
        self.nlp = None
        self._load_spacy()

    def _load_spacy(self):
        if not self.use_spacy:
            return
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            print("[NLP] spaCy model loaded: en_core_web_sm")
        except (ImportError, OSError):
            print("[NLP] spaCy model not found — using rule-based extraction only.")
            print("[NLP] To enable: python -m spacy download en_core_web_sm")
            self.nlp = None

    # ── Skill Extraction ──────────────────────

    def extract_skills(self, text: str) -> list[str]:
        """
        Extract skills from free-form resume text.
        Uses: alias normalization → multi-word phrase matching → single-word matching.
        """
        text_lower = text.lower()
        found_skills = set()

        # 1. Check aliases (multi-word synonyms)
        for alias, canonical in SKILL_ALIASES.items():
            if alias in text_lower:
                found_skills.add(canonical)

        # 2. Check multi-word skills from taxonomy
        for skill in SKILLS_TAXONOMY:
            if skill.lower() in text_lower:
                found_skills.add(skill)

        # 3. Token-level matching after cleaning
        clean_tokens = set(re.findall(r'\b[a-zA-Z][a-zA-Z0-9\+\#\-\.]*\b', text))
        for token in clean_tokens:
            canonical = _SKILL_LOWER_MAP.get(token.lower())
            if canonical:
                found_skills.add(canonical)

        # 4. spaCy NER enhancement (if available)
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("ORG", "PRODUCT", "GPE"):
                    canonical = _SKILL_LOWER_MAP.get(ent.text.lower())
                    if canonical:
                        found_skills.add(canonical)

        return sorted(found_skills)

    # ── Experience Extraction ─────────────────

    def extract_experience_years(self, text: str) -> int:
        """Parse years of experience from resume text."""
        patterns = [
            r'(\d+)\+?\s*years?\s+of\s+(?:professional\s+)?experience',
            r'(\d+)\+?\s*years?\s+experience',
            r'experience\s+of\s+(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s+(?:of\s+)?experience',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0

    # ── Education Extraction ──────────────────

    def extract_education(self, text: str) -> dict:
        """Extract degree, field, university from text."""
        degrees_re = r'\b(B\.?Tech|M\.?Tech|B\.?Sc|M\.?Sc|MBA|BCA|MCA|Ph\.?D|Bachelor|Master|B\.?E|M\.?E)\b'
        degree_match = re.search(degrees_re, text, re.IGNORECASE)

        university_keywords = ["University", "Institute", "College", "IIT", "NIT", "BITS", "VIT"]
        uni_pattern = r'(?:' + '|'.join(university_keywords) + r')[^\n,\.]{2,40}'
        uni_match = re.search(uni_pattern, text, re.IGNORECASE)

        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', text)

        return {
            "degree": degree_match.group(0) if degree_match else "Unknown",
            "university": uni_match.group(0).strip() if uni_match else "Unknown",
            "graduation_year": int(year_match.group(0)) if year_match else None,
        }

    # ── Contact Info Extraction ───────────────

    def extract_contact_info(self, text: str) -> dict:
        """Extract email and phone from resume text."""
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        phone_match = re.search(r'(?:\+91[\s\-]?)?[6-9]\d{9}', text)
        return {
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
        }

    # ── Full Resume Parse ─────────────────────

    def parse_resume(self, resume_text: str) -> dict:
        """Complete resume parsing pipeline."""
        skills = self.extract_skills(resume_text)
        education = self.extract_education(resume_text)
        contact = self.extract_contact_info(resume_text)
        experience_years = self.extract_experience_years(resume_text)

        # Skill categorization
        skill_breakdown = defaultdict(list)
        for skill in skills:
            category = SKILLS_TAXONOMY.get(skill, "other")
            skill_breakdown[category].append(skill)

        return {
            "extracted_skills": skills,
            "skill_count": len(skills),
            "skill_breakdown": dict(skill_breakdown),
            "education": education,
            "contact": contact,
            "experience_years_detected": experience_years,
        }


# ──────────────────────────────────────────────
# TF-IDF Resume ↔ Job Similarity Engine
# ──────────────────────────────────────────────

class TFIDFMatcher:
    """
    Lightweight TF-IDF based resume-to-job description similarity scoring.
    No external model required — pure Python implementation.
    """

    def __init__(self):
        self.idf_cache = {}
        self._corpus_tokenized = []

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'\b[a-z][a-z0-9\+\#]*\b', text.lower())

    def _tf(self, tokens: list[str]) -> dict[str, float]:
        freq = defaultdict(int)
        for t in tokens:
            freq[t] += 1
        total = len(tokens) or 1
        return {t: c / total for t, c in freq.items()}

    def _idf(self, term: str, corpus: list[list[str]]) -> float:
        n_docs = len(corpus)
        n_containing = sum(1 for doc in corpus if term in doc) + 1
        return math.log((n_docs + 1) / n_containing) + 1

    def _tfidf_vector(self, tokens: list[str], corpus: list[list[str]]) -> dict[str, float]:
        tf = self._tf(tokens)
        return {t: score * self._idf(t, corpus) for t, score in tf.items()}

    def _cosine_similarity(self, v1: dict, v2: dict) -> float:
        keys = set(v1) | set(v2)
        dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in keys)
        mag1 = math.sqrt(sum(x**2 for x in v1.values()))
        mag2 = math.sqrt(sum(x**2 for x in v2.values()))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)

    def compute_similarity(self, resume_text: str, job_text: str) -> float:
        """Compute TF-IDF cosine similarity between resume and job description."""
        tok_resume = self._tokenize(resume_text)
        tok_job = self._tokenize(job_text)
        corpus = [tok_resume, tok_job]
        vec_resume = self._tfidf_vector(tok_resume, corpus)
        vec_job = self._tfidf_vector(tok_job, corpus)
        return round(self._cosine_similarity(vec_resume, vec_job), 4)


# ──────────────────────────────────────────────
# Scoring Engine
# ──────────────────────────────────────────────

class ScoringEngine:
    """
    Multi-factor scoring engine for resume-job matching.
    Weights: skill_match (50%), experience (30%), education (10%), tfidf (10%)
    """

    WEIGHTS = {
        "skill_match": 0.50,
        "experience": 0.30,
        "education": 0.10,
        "tfidf": 0.10,
    }

    DEGREE_SCORE = {
        "phd": 100, "ph.d": 100,
        "m.tech": 90, "mtech": 90, "m.sc": 88, "msc": 88,
        "mba": 85, "mca": 83, "m.e": 88,
        "b.tech": 75, "btech": 75, "b.e": 75, "b.sc": 70,
        "bca": 65, "bba": 60,
        "unknown": 50,
    }

    def __init__(self):
        self.tfidf = TFIDFMatcher()

    def _skill_match_score(
        self,
        candidate_skills: list[str],
        required_skills: list[str],
        preferred_skills: list[str],
    ) -> tuple[float, list, list, list]:
        """Returns (score, matched, missing, extra_skills)."""
        cand_lower = {s.lower(): s for s in candidate_skills}
        req_lower = [s.lower() for s in required_skills]
        pref_lower = [s.lower() for s in preferred_skills]

        matched_req = [s for s in req_lower if s in cand_lower]
        matched_pref = [s for s in pref_lower if s in cand_lower]
        missing = [required_skills[i] for i, s in enumerate(req_lower) if s not in cand_lower]
        extra = [v for k, v in cand_lower.items() if k not in req_lower and k not in pref_lower]

        req_score = (len(matched_req) / len(req_lower) * 100) if req_lower else 100
        pref_score = (len(matched_pref) / len(pref_lower) * 100) if pref_lower else 100
        combined = req_score * 0.75 + pref_score * 0.25

        matched_canonical = [cand_lower[s] for s in matched_req] + [cand_lower[s] for s in matched_pref if s in cand_lower]
        return combined, list(set(matched_canonical)), missing, extra

    def _experience_score(self, candidate_exp: int, min_exp: int) -> float:
        if candidate_exp >= min_exp:
            bonus = min((candidate_exp - min_exp) * 5, 15)
            return min(100.0, 85.0 + bonus)
        ratio = candidate_exp / min_exp if min_exp > 0 else 0
        return round(ratio * 75, 1)

    def _education_score(self, degree: str) -> float:
        deg_clean = degree.lower().replace(".", "").replace(" ", "")
        for key, score in self.DEGREE_SCORE.items():
            if key.replace(".", "") in deg_clean:
                return float(score)
        return 50.0

    def score_resume(
        self,
        candidate: dict,
        job: dict,
    ) -> dict:
        """
        Full scoring pipeline for one candidate vs one job.
        Returns a detailed score report.
        """
        candidate_skills = candidate.get("skills", [])
        required_skills = job.get("required_skills", [])
        preferred_skills = job.get("preferred_skills", [])

        # Skill match
        skill_score, matched, missing, extra = self._skill_match_score(
            candidate_skills, required_skills, preferred_skills
        )

        # Experience
        exp_score = self._experience_score(
            candidate.get("years_experience", 0),
            job.get("min_experience", 0)
        )

        # Education
        edu_score = self._education_score(
            candidate.get("education", {}).get("degree", "unknown")
        )

        # TF-IDF semantic similarity
        job_text = f"{job['title']} {' '.join(required_skills + preferred_skills)}"
        resume_text = candidate.get("resume_text", " ".join(candidate_skills))
        tfidf_score = self.tfidf.compute_similarity(resume_text, job_text) * 100

        # Weighted overall
        overall = (
            skill_score * self.WEIGHTS["skill_match"]
            + exp_score * self.WEIGHTS["experience"]
            + edu_score * self.WEIGHTS["education"]
            + tfidf_score * self.WEIGHTS["tfidf"]
        )
        overall = round(overall, 2)

        # Recommendation
        if overall >= 72:
            recommendation = "Shortlist"
        elif overall >= 50:
            recommendation = "Review"
        else:
            recommendation = "Reject"

        return {
            "candidate_id": candidate["candidate_id"],
            "job_id": job["job_id"],
            "overall_score": overall,
            "skill_match_score": round(skill_score, 2),
            "experience_score": round(exp_score, 2),
            "education_score": round(edu_score, 2),
            "tfidf_score": round(tfidf_score, 2),
            "matched_skills": matched,
            "missing_skills": missing,
            "extra_skills": extra[:10],
            "recommendation": recommendation,
        }


if __name__ == "__main__":
    engine = ResumeNLPEngine(use_spacy=False)
    scorer = ScoringEngine()

    sample_text = (
        "5 years experience in Python, SQL, TensorFlow, Power BI. "
        "B.Tech Computer Science, IIT Bombay. Led a team of 4 analysts. "
        "Built customer churn model using scikit-learn and XGBoost."
    )

    parsed = engine.parse_resume(sample_text)
    print("\n[NLP] Extracted skills:", parsed["extracted_skills"])
    print("[NLP] Skill breakdown:", parsed["skill_breakdown"])
    print("[NLP] Education:", parsed["education"])

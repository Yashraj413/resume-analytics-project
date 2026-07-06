"""
Sample Data Generator for Resume Screening Analytics
Generates realistic synthetic resumes and job descriptions for demo/testing.
"""

import json
import random
from datetime import datetime, timedelta

CANDIDATES = [
    {"name": "Priya Sharma", "exp": 4, "role": "Data Analyst"},
    {"name": "Rahul Mehta", "exp": 7, "role": "Senior Data Scientist"},
    {"name": "Ananya Iyer", "exp": 2, "role": "Junior Data Analyst"},
    {"name": "Vikram Nair", "exp": 5, "role": "ML Engineer"},
    {"name": "Sneha Patel", "exp": 3, "role": "Business Analyst"},
    {"name": "Arjun Reddy", "exp": 8, "role": "Data Engineer"},
    {"name": "Pooja Gupta", "exp": 1, "role": "Data Analyst Intern"},
    {"name": "Karan Singh", "exp": 6, "role": "Senior ML Engineer"},
    {"name": "Divya Menon", "exp": 3, "role": "Data Analyst"},
    {"name": "Rohan Das", "exp": 9, "role": "Principal Data Scientist"},
    {"name": "Meera Joshi", "exp": 4, "role": "Analytics Engineer"},
    {"name": "Aditya Kumar", "exp": 2, "role": "Junior Data Scientist"},
    {"name": "Neha Batra", "exp": 5, "role": "Data Scientist"},
    {"name": "Siddharth Rao", "exp": 3, "role": "Business Intelligence Analyst"},
    {"name": "Kavita Verma", "exp": 7, "role": "Senior Data Analyst"},
    {"name": "Manish Tiwari", "exp": 1, "role": "Data Analyst Fresher"},
    {"name": "Swati Agarwal", "exp": 6, "role": "ML Ops Engineer"},
    {"name": "Rajesh Pillai", "exp": 4, "role": "Data Analyst"},
    {"name": "Isha Chopra", "exp": 8, "role": "Data Science Lead"},
    {"name": "Nikhil Bhatt", "exp": 2, "role": "Junior ML Engineer"},
]

SKILLS_POOL = {
    "programming": ["Python", "R", "SQL", "Scala", "Java", "Julia", "SAS"],
    "ml_frameworks": ["TensorFlow", "PyTorch", "Scikit-learn", "Keras", "XGBoost", "LightGBM", "CatBoost"],
    "data_tools": ["Pandas", "NumPy", "Spark", "Hadoop", "Kafka", "Airflow", "dbt"],
    "visualization": ["Power BI", "Tableau", "Matplotlib", "Seaborn", "Plotly", "Looker", "Grafana"],
    "databases": ["MySQL", "PostgreSQL", "MongoDB", "Redis", "Snowflake", "BigQuery", "Redshift"],
    "cloud": ["AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform"],
    "nlp": ["NLTK", "spaCy", "Hugging Face", "BERT", "GPT", "LangChain"],
    "soft_skills": ["Communication", "Problem Solving", "Team Leadership", "Stakeholder Management", "Agile"],
}

JOB_DESCRIPTIONS = [
    {
        "job_id": "JD001",
        "title": "Data Analyst",
        "department": "Analytics",
        "required_skills": ["Python", "SQL", "Power BI", "Pandas", "Excel"],
        "preferred_skills": ["Tableau", "R", "Spark"],
        "min_experience": 2,
        "location": "Pune",
        "salary_range": "6-10 LPA",
    },
    {
        "job_id": "JD002",
        "title": "Senior Data Scientist",
        "department": "AI/ML",
        "required_skills": ["Python", "Machine Learning", "TensorFlow", "SQL", "Statistics"],
        "preferred_skills": ["Spark", "AWS", "Docker", "Kubernetes"],
        "min_experience": 5,
        "location": "Bangalore",
        "salary_range": "18-28 LPA",
    },
    {
        "job_id": "JD003",
        "title": "ML Engineer",
        "department": "Engineering",
        "required_skills": ["Python", "TensorFlow", "Docker", "AWS", "SQL", "Scikit-learn"],
        "preferred_skills": ["Kubernetes", "Spark", "Kafka", "MLflow"],
        "min_experience": 3,
        "location": "Hyderabad",
        "salary_range": "12-20 LPA",
    },
    {
        "job_id": "JD004",
        "title": "Business Intelligence Analyst",
        "department": "Business Analytics",
        "required_skills": ["SQL", "Power BI", "Excel", "Tableau", "Communication"],
        "preferred_skills": ["Python", "R", "Looker", "Stakeholder Management"],
        "min_experience": 2,
        "location": "Mumbai",
        "salary_range": "8-14 LPA",
    },
    {
        "job_id": "JD005",
        "title": "Data Engineer",
        "department": "Data Platform",
        "required_skills": ["Python", "SQL", "Spark", "Airflow", "Kafka", "PostgreSQL"],
        "preferred_skills": ["Scala", "Kubernetes", "dbt", "Snowflake"],
        "min_experience": 4,
        "location": "Remote",
        "salary_range": "15-25 LPA",
    },
]


def generate_resume(candidate: dict) -> dict:
    """Generate a synthetic resume for a candidate."""
    random.seed(hash(candidate["name"]))

    exp = candidate["exp"]
    role = candidate["role"].lower()

    # Determine skill set based on role and experience
    skills = []

    # Always include some base skills
    skills.extend(random.sample(SKILLS_POOL["programming"], min(3, len(SKILLS_POOL["programming"]))))
    skills.extend(random.sample(SKILLS_POOL["data_tools"], min(2, len(SKILLS_POOL["data_tools"]))))
    skills.extend(random.sample(SKILLS_POOL["databases"], min(2, len(SKILLS_POOL["databases"]))))
    skills.extend(random.sample(SKILLS_POOL["visualization"], min(2, len(SKILLS_POOL["visualization"]))))

    if exp >= 3:
        skills.extend(random.sample(SKILLS_POOL["ml_frameworks"], min(2, len(SKILLS_POOL["ml_frameworks"]))))
    if exp >= 5:
        skills.extend(random.sample(SKILLS_POOL["cloud"], min(2, len(SKILLS_POOL["cloud"]))))
    if "nlp" in role or "scientist" in role:
        skills.extend(random.sample(SKILLS_POOL["nlp"], min(2, len(SKILLS_POOL["nlp"]))))
    if exp >= 3:
        skills.extend(random.sample(SKILLS_POOL["soft_skills"], min(3, 5)))

    skills = list(set(skills))

    # Education
    degrees = ["B.Tech", "M.Tech", "B.Sc", "M.Sc", "MBA", "BCA", "MCA"]
    fields = ["Computer Science", "Statistics", "Mathematics", "Data Science", "Information Technology", "Electronics"]
    universities = [
        "IIT Bombay", "IIT Delhi", "IIT Madras", "NIT Pune", "BITS Pilani",
        "Delhi University", "Pune University", "VIT Vellore", "Anna University",
        "Manipal University"
    ]

    grad_year = 2024 - exp - random.randint(0, 1)

    education = {
        "degree": random.choice(degrees),
        "field": random.choice(fields),
        "university": random.choice(universities),
        "graduation_year": grad_year,
        "gpa": round(random.uniform(6.5, 9.8), 1),
    }

    # Work experience
    companies = [
        "Infosys", "TCS", "Wipro", "HCL", "Tech Mahindra", "Cognizant",
        "Accenture", "Capgemini", "IBM", "Deloitte", "EY", "KPMG",
        "Mu Sigma", "Fractal Analytics", "Tiger Analytics", "Latent View"
    ]

    work_experience = []
    remaining_exp = exp
    current_date = datetime.now()

    job_titles = ["Data Analyst", "Senior Data Analyst", "Data Scientist",
                  "Senior Data Scientist", "ML Engineer", "Data Engineer",
                  "Junior Analyst", "Analytics Consultant"]

    while remaining_exp > 0:
        duration = min(random.randint(1, 3), remaining_exp)
        end_date = current_date - timedelta(days=365 * (exp - remaining_exp))
        start_date = end_date - timedelta(days=365 * duration)

        work_experience.append({
            "company": random.choice(companies),
            "title": random.choice(job_titles),
            "start_date": start_date.strftime("%b %Y"),
            "end_date": end_date.strftime("%b %Y") if remaining_exp != exp else "Present",
            "duration_years": duration,
            "description": generate_job_description_text(skills[:5]),
        })
        remaining_exp -= duration

    # Projects
    project_templates = [
        "Customer Churn Prediction using {ml} and {tool}",
        "Sales Forecasting Dashboard with {viz} and {db}",
        "Real-time Fraud Detection System using {ml} and {cloud}",
        "NLP-based Sentiment Analysis Pipeline using {nlp_tool}",
        "Automated Reporting System using {tool} and {viz}",
        "Data Pipeline Optimization using {etl}",
        "A/B Testing Framework using Python and Statistical Analysis",
        "Supply Chain Analytics Dashboard with {viz}",
    ]

    viz_options = [s for s in skills if s in SKILLS_POOL["visualization"]] or ["Tableau"]
    ml_options = [s for s in skills if s in SKILLS_POOL["ml_frameworks"]] or ["Scikit-learn"]
    db_options = [s for s in skills if s in SKILLS_POOL["databases"]] or ["PostgreSQL"]
    cloud_options = [s for s in skills if s in SKILLS_POOL["cloud"]] or ["AWS"]
    nlp_options = [s for s in skills if s in SKILLS_POOL["nlp"]] or ["NLTK"]
    tool_options = [s for s in skills if s in SKILLS_POOL["data_tools"]] or ["Pandas"]

    projects = []
    num_projects = min(3, max(1, exp))
    chosen_templates = random.sample(project_templates, min(num_projects, len(project_templates)))

    for template in chosen_templates:
        project_name = template.format(
            ml=random.choice(ml_options),
            viz=random.choice(viz_options),
            db=random.choice(db_options),
            cloud=random.choice(cloud_options),
            nlp_tool=random.choice(nlp_options),
            tool=random.choice(tool_options),
            etl=random.choice(["Airflow", "dbt", "Spark"]),
        )
        projects.append({
            "name": project_name,
            "skills_used": random.sample(skills, min(4, len(skills))),
            "impact": f"Improved efficiency by {random.randint(15, 70)}%",
        })

    # Contact info
    email_domain = random.choice(["gmail.com", "yahoo.com", "outlook.com"])
    name_slug = candidate["name"].lower().replace(" ", ".")

    return {
        "candidate_id": f"CAND{str(CANDIDATES.index(candidate) + 1).zfill(3)}",
        "name": candidate["name"],
        "email": f"{name_slug}@{email_domain}",
        "phone": f"+91 9{random.randint(100000000, 999999999)}",
        "location": random.choice(["Pune", "Mumbai", "Bangalore", "Hyderabad", "Delhi", "Chennai"]),
        "years_experience": exp,
        "current_role": candidate["role"],
        "skills": skills,
        "education": education,
        "work_experience": work_experience,
        "projects": projects,
        "certifications": generate_certifications(skills, exp),
        "resume_text": generate_raw_resume_text(candidate, skills, education, work_experience, projects),
        "applied_date": (datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d"),
        "source": random.choice(["LinkedIn", "Naukri", "Indeed", "Referral", "Company Website"]),
        "status": random.choice(["Shortlisted", "Rejected", "Under Review", "Interview Scheduled", "Offer Extended"]),
    }


def generate_job_description_text(skills: list) -> str:
    actions = ["Developed", "Built", "Designed", "Implemented", "Optimized", "Automated", "Led"]
    outcomes = [
        "reducing processing time by 40%",
        "improving model accuracy by 15%",
        "saving 20 hours/week of manual effort",
        "enabling real-time decision making",
        "supporting $2M revenue decisions",
    ]
    skill = random.choice(skills) if skills else "Python"
    return f"{random.choice(actions)} analytics solution using {skill}, {random.choice(outcomes)}."


def generate_certifications(skills: list, exp: int) -> list:
    cert_map = {
        "AWS": "AWS Certified Solutions Architect",
        "GCP": "Google Cloud Professional Data Engineer",
        "Azure": "Microsoft Azure Data Scientist Associate",
        "Python": "Python for Data Science (IBM)",
        "TensorFlow": "TensorFlow Developer Certificate",
        "Power BI": "Microsoft PL-300: Power BI Data Analyst",
        "Tableau": "Tableau Desktop Specialist",
        "SQL": "SQL for Data Science (Coursera)",
    }
    certs = []
    for skill in skills:
        if skill in cert_map and random.random() > 0.5:
            certs.append(cert_map[skill])
    return list(set(certs))[:min(3, exp)]


def generate_raw_resume_text(candidate, skills, education, work_experience, projects) -> str:
    skill_str = ", ".join(skills[:12])
    work_str = " | ".join([f"{w['title']} at {w['company']} ({w['duration_years']}yr)" for w in work_experience])
    proj_str = " | ".join([p["name"] for p in projects])
    return (
        f"{candidate['name']} | {candidate['role']} | {candidate['exp']} years experience\n"
        f"Skills: {skill_str}\n"
        f"Education: {education['degree']} in {education['field']} from {education['university']} ({education['graduation_year']})\n"
        f"Experience: {work_str}\n"
        f"Projects: {proj_str}"
    )


def generate_all_data() -> dict:
    resumes = [generate_resume(c) for c in CANDIDATES]
    return {"resumes": resumes, "job_descriptions": JOB_DESCRIPTIONS}


if __name__ == "__main__":
    import os
    data = generate_all_data()
    base_dir = os.path.dirname(__file__)
    resumes_path = os.path.join(base_dir, "resumes.json")
    jd_path = os.path.join(base_dir, "job_descriptions.json")
    with open(resumes_path, "w") as f:
        json.dump(data["resumes"], f, indent=2)
    with open(jd_path, "w") as f:
        json.dump(data["job_descriptions"], f, indent=2)
    print(f"Generated {len(data['resumes'])} resumes and {len(data['job_descriptions'])} job descriptions.")

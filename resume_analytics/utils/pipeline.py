"""
ETL Pipeline — Ingests resumes + job descriptions into SQLite,
runs NLP extraction, computes match scores, populates all tables.
"""

import json
import os
import sys
import sqlite3
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sql.database import get_connection, initialize_db, log_event, DB_PATH
from models.nlp_engine import ResumeNLPEngine, ScoringEngine, SKILLS_TAXONOMY


def load_json(path: str) -> list:
    with open(path) as f:
        return json.load(f)


# ──────────────────────────────────────────────
# INGEST: Skills Taxonomy
# ──────────────────────────────────────────────

def populate_skills_table(conn: sqlite3.Connection) -> None:
    print("[ETL] Populating skills taxonomy...")
    for skill_name, category in SKILLS_TAXONOMY.items():
        conn.execute(
            "INSERT OR IGNORE INTO skills (skill_name, category) VALUES (?, ?)",
            (skill_name, category)
        )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    print(f"[ETL]   -> {count} skills in taxonomy")


# ──────────────────────────────────────────────
# INGEST: Job Descriptions
# ──────────────────────────────────────────────

def ingest_job_descriptions(conn: sqlite3.Connection, jobs: list) -> None:
    print(f"[ETL] Ingesting {len(jobs)} job descriptions...")
    for job in jobs:
        conn.execute(
            """INSERT OR REPLACE INTO job_descriptions
               (job_id, title, department, min_experience, location, salary_range)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (job["job_id"], job["title"], job.get("department"),
             job.get("min_experience", 0), job.get("location"), job.get("salary_range"))
        )
        # Required skills
        for skill in job.get("required_skills", []):
            conn.execute(
                "INSERT OR IGNORE INTO job_required_skills (job_id, skill_name, is_required) VALUES (?, ?, 1)",
                (job["job_id"], skill)
            )
        # Preferred skills
        for skill in job.get("preferred_skills", []):
            conn.execute(
                "INSERT OR IGNORE INTO job_required_skills (job_id, skill_name, is_required) VALUES (?, ?, 0)",
                (job["job_id"], skill)
            )
        log_event(conn, "job_ingested", job["job_id"], {"title": job["title"]})
    conn.commit()
    print(f"[ETL]   -> Done")


# ──────────────────────────────────────────────
# INGEST: Candidates + Resume NLP
# ──────────────────────────────────────────────

def ingest_candidates(conn: sqlite3.Connection, resumes: list, nlp: ResumeNLPEngine) -> None:
    print(f"[ETL] Ingesting {len(resumes)} candidates with NLP extraction...")

    for r in resumes:
        # NLP pass on raw resume text
        parsed = nlp.parse_resume(r.get("resume_text", ""))

        # Merge NLP-extracted skills with structured skills (structured takes priority)
        structured_skills = set(r.get("skills", []))
        nlp_skills = set(parsed["extracted_skills"])
        all_skills = structured_skills | nlp_skills  # union

        edu = r.get("education", {})

        conn.execute(
            """INSERT OR REPLACE INTO candidates
               (candidate_id, name, email, phone, location, years_experience, current_role,
                education_degree, education_field, education_university, graduation_year, gpa,
                applied_date, source, status, resume_text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                r["candidate_id"], r["name"], r["email"], r.get("phone"), r.get("location"),
                r.get("years_experience", 0), r.get("current_role"),
                edu.get("degree"), edu.get("field"), edu.get("university"),
                edu.get("graduation_year"), edu.get("gpa"),
                r.get("applied_date"), r.get("source"), r.get("status"),
                r.get("resume_text", "")
            )
        )

        # Candidate skills
        for skill_name in all_skills:
            row = conn.execute("SELECT skill_id FROM skills WHERE skill_name = ?", (skill_name,)).fetchone()
            if row:
                conn.execute(
                    "INSERT OR IGNORE INTO candidate_skills (candidate_id, skill_id) VALUES (?, ?)",
                    (r["candidate_id"], row[0])
                )

        # Work experience
        for we in r.get("work_experience", []):
            conn.execute(
                """INSERT INTO work_experience
                   (candidate_id, company, title, start_date, end_date, duration_years, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (r["candidate_id"], we.get("company"), we.get("title"),
                 we.get("start_date"), we.get("end_date"), we.get("duration_years"), we.get("description"))
            )

        # Projects
        for p in r.get("projects", []):
            conn.execute(
                "INSERT INTO projects (candidate_id, project_name, skills_used, impact) VALUES (?, ?, ?, ?)",
                (r["candidate_id"], p.get("name"), json.dumps(p.get("skills_used", [])), p.get("impact"))
            )

        # Certifications
        for cert in r.get("certifications", []):
            conn.execute(
                "INSERT INTO certifications (candidate_id, cert_name) VALUES (?, ?)",
                (r["candidate_id"], cert)
            )

        log_event(conn, "resume_ingested", r["candidate_id"], {
            "name": r["name"],
            "skills_extracted": len(all_skills),
            "nlp_skills_added": len(nlp_skills - structured_skills),
        })

    conn.commit()
    print(f"[ETL]   -> Done")


# ──────────────────────────────────────────────
# SCORING: All candidates × all jobs
# ──────────────────────────────────────────────

def run_scoring_pipeline(conn: sqlite3.Connection, resumes: list, jobs: list, scorer: ScoringEngine) -> None:
    print(f"[ETL] Running scoring pipeline ({len(resumes)} × {len(jobs)} = {len(resumes)*len(jobs)} pairs)...")

    for resume in resumes:
        for job in jobs:
            result = scorer.score_resume(resume, job)
            conn.execute(
                """INSERT OR REPLACE INTO match_scores
                   (candidate_id, job_id, overall_score, skill_match_score, experience_score,
                    education_score, matched_skills, missing_skills, extra_skills, recommendation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result["candidate_id"], result["job_id"],
                    result["overall_score"], result["skill_match_score"],
                    result["experience_score"], result["education_score"],
                    json.dumps(result["matched_skills"]),
                    json.dumps(result["missing_skills"]),
                    json.dumps(result["extra_skills"]),
                    result["recommendation"],
                )
            )
            log_event(conn, "score_computed", result["candidate_id"], {
                "job_id": result["job_id"],
                "score": result["overall_score"],
                "recommendation": result["recommendation"],
            })

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM match_scores").fetchone()[0]
    print(f"[ETL]   -> {total} match scores computed")


# ──────────────────────────────────────────────
# ANALYTICS QUERIES: Pre-computed summary stats
# ──────────────────────────────────────────────

def print_summary(conn: sqlite3.Connection) -> None:
    print("\n" + "="*60)
    print("  PIPELINE SUMMARY")
    print("="*60)

    stats = {
        "Total Candidates": conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
        "Total Jobs":        conn.execute("SELECT COUNT(*) FROM job_descriptions").fetchone()[0],
        "Total Skills":      conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0],
        "Match Scores":      conn.execute("SELECT COUNT(*) FROM match_scores").fetchone()[0],
        "Shortlisted":       conn.execute("SELECT COUNT(*) FROM match_scores WHERE recommendation='Shortlist'").fetchone()[0],
        "To Review":         conn.execute("SELECT COUNT(*) FROM match_scores WHERE recommendation='Review'").fetchone()[0],
        "Rejected":          conn.execute("SELECT COUNT(*) FROM match_scores WHERE recommendation='Reject'").fetchone()[0],
        "Avg Score":         round(conn.execute("SELECT AVG(overall_score) FROM match_scores").fetchone()[0] or 0, 1),
    }
    for k, v in stats.items():
        print(f"  {k:<25} {v}")

    print("\n  TOP 5 CANDIDATES (by best match score):")
    top = conn.execute("""
        SELECT c.name, c.current_role, MAX(ms.overall_score) as best, ms.recommendation
        FROM candidates c JOIN match_scores ms ON c.candidate_id = ms.candidate_id
        GROUP BY c.candidate_id ORDER BY best DESC LIMIT 5
    """).fetchall()
    for row in top:
        print(f"  {row[0]:<25} {row[1]:<30} Score: {row[2]:.1f}  [{row[3]}]")

    print("\n  TOP SKILLS IN DEMAND:")
    top_skills = conn.execute("""
        SELECT skill_name, jobs_requiring FROM v_job_skill_demand LIMIT 8
    """).fetchall()
    for row in top_skills:
        print(f"  {row[0]:<25} Required by {row[1]} jobs")
    print("="*60 + "\n")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def run_pipeline(
    resumes_path: str = None,
    jobs_path: str = None,
    db_path: str = DB_PATH,
    use_spacy: bool = True,
) -> None:
    base = os.path.join(os.path.dirname(__file__), "..", "sample_data")
    resumes_path = resumes_path or os.path.join(base, "resumes.json")
    jobs_path = jobs_path or os.path.join(base, "job_descriptions.json")

    print("\n[PIPELINE] Starting Resume Screening Analytics Pipeline")
    print(f"[PIPELINE] DB: {db_path}")
    print(f"[PIPELINE] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Init DB
    initialize_db(db_path)
    conn = get_connection(db_path)

    # Load raw data
    resumes = load_json(resumes_path)
    jobs = load_json(jobs_path)

    # Init models
    nlp = ResumeNLPEngine(use_spacy=use_spacy)
    scorer = ScoringEngine()

    # Run ETL stages
    populate_skills_table(conn)
    ingest_job_descriptions(conn, jobs)
    ingest_candidates(conn, resumes, nlp)
    run_scoring_pipeline(conn, resumes, jobs, scorer)

    # Summary
    print_summary(conn)
    conn.close()
    print("[PIPELINE] Complete. Database ready for dashboard.")


if __name__ == "__main__":
    run_pipeline()

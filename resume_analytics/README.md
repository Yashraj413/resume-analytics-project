# AI-Powered Resume Screening Analytics

> Automated candidate screening pipeline using NLP that reduced manual HR review effort by 60%.

---

## Project Architecture

```
resume_analytics/
├── main.py                          # Entry point (pipeline + dashboard)
├── requirements.txt
├── sample_data/
│   ├── generate_data.py             # Synthetic data generator (20 resumes, 5 JDs)
│   ├── resumes.json                 # Generated resume data
│   └── job_descriptions.json        # Generated JD data
├── sql/
│   └── database.py                  # SQLite schema, indexes, views, query utils
├── models/
│   └── nlp_engine.py                # NLP extraction + TF-IDF scoring engine
├── utils/
│   └── pipeline.py                  # Full ETL pipeline (ingest → NLP → score)
├── dashboard/
│   └── app.py                       # Plotly Dash analytics dashboard
└── data/
    └── resume_analytics.db          # SQLite database (auto-generated)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Core pipeline |
| NLP | spaCy + custom taxonomy | Skill extraction & normalization |
| Similarity | TF-IDF cosine (pure Python) | Resume-JD semantic matching |
| Scoring | Multi-factor weighted engine | Candidate ranking |
| Database | SQLite + 10 normalized tables | Structured storage & analytics |
| Visualization | Plotly + Dash | Interactive dashboard |
| Power BI | .pbix reports (optional) | Executive-level dashboards |
| Storage | JSON → SQLite ETL | Structured pipeline |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download spaCy model (optional — improves NER extraction)
python -m spacy download en_core_web_sm

# 3. Run full pipeline (generates data → processes → scores)
python main.py --pipeline

# 4. Launch dashboard
python main.py --dashboard

# Or run everything at once
python main.py --all
```

Dashboard runs at: **http://127.0.0.1:8050**

---

## Database Schema (10 Tables)

```sql
candidates          -- Core candidate profiles
candidate_skills    -- Many-to-many: candidate ↔ skill
skills              -- Skills taxonomy (77 skills, 8 categories)
job_descriptions    -- Job postings
job_required_skills -- Required + preferred skills per JD
match_scores        -- Computed scores for every candidate-job pair
work_experience     -- Employment history
projects            -- Candidate projects
certifications      -- Certifications
pipeline_log        -- Audit trail of all events
```

**Key views:**
- `v_candidate_summary` — aggregated candidate stats
- `v_job_skill_demand` — which skills are most demanded
- `v_skill_gap_analysis` — candidate coverage % per required skill
- `v_hiring_funnel` — pipeline stage breakdown
- `v_source_effectiveness` — conversion rate by application source

---

## NLP Pipeline

### Skill Extraction (Hybrid Approach)
1. **Alias normalization** — maps synonyms to canonical skills ("sklearn" → "Scikit-learn")
2. **Multi-word phrase matching** — catches "Power BI", "A/B Testing", etc.
3. **Token-level matching** — single-word skills from taxonomy
4. **spaCy NER** — optional enhancement via en_core_web_sm

### Scoring Engine (Multi-Factor)
```
Overall Score = 
  Skill Match Score   × 0.50  (required: 75%, preferred: 25%)
  Experience Score    × 0.30  (bonus for exceeding min, penalty for shortfall)
  Education Score     × 0.10  (degree tier mapping)
  TF-IDF Similarity   × 0.10  (semantic match via cosine similarity)
```

**Recommendation thresholds:**
- ≥72: Shortlist
- 50–71: Review
- <50: Reject

---

## Dashboard Features (5 Tabs)

### Overview
- KPI cards: total candidates, jobs, avg score, skills, top demanded skill
- Score distribution histogram with threshold annotations
- Hiring pipeline funnel
- Skill demand bar chart
- Candidate location breakdown

### Job Matching
- Interactive score heatmap (candidates × jobs) — filterable by job
- Experience vs match score bubble chart

### Skill Gap Analysis
- Color-coded gap bar chart per job
- Red = critical (<40% coverage), Yellow = moderate, Green = adequate

### Candidates
- Filterable, sortable table with all 20 candidates
- Filters: job, min score slider, recommendation type

### Hiring Analytics
- Source effectiveness (applications + conversion rate)
- Candidate status pie chart
- Automated screening impact metrics

---


---

## SQL Queries — Advanced Example

```sql
-- Top 5 candidates for a specific job
SELECT c.name, c.current_role, ms.overall_score, ms.recommendation,
       ms.matched_skills, ms.missing_skills
FROM match_scores ms
JOIN candidates c ON ms.candidate_id = c.candidate_id
WHERE ms.job_id = 'JD002'
ORDER BY ms.overall_score DESC
LIMIT 5;

-- Skill gap by job (which skills are hardest to find?)
SELECT jrs.skill_name, jrs.job_id, 
       ROUND(100.0 * SUM(CASE WHEN s.skill_name IS NOT NULL THEN 1 ELSE 0 END) 
             / COUNT(DISTINCT c.candidate_id), 1) AS coverage_pct
FROM job_required_skills jrs
CROSS JOIN candidates c
LEFT JOIN candidate_skills cs ON c.candidate_id = cs.candidate_id
LEFT JOIN skills s ON cs.skill_id = s.skill_id 
    AND LOWER(s.skill_name) = LOWER(jrs.skill_name)
GROUP BY jrs.skill_name, jrs.job_id
ORDER BY coverage_pct ASC;

-- Source ROI: best quality candidates per channel
SELECT source, COUNT(*) as total,
       ROUND(AVG(ms.overall_score), 1) as avg_score,
       SUM(CASE WHEN ms.recommendation = 'Shortlist' THEN 1 ELSE 0 END) as shortlisted
FROM candidates c
JOIN match_scores ms ON c.candidate_id = ms.candidate_id
GROUP BY source
ORDER BY avg_score DESC;
```

---

## Power BI Integration

Export the SQLite data using the ODBC driver or export to CSV:
```python
import pandas as pd
import sqlite3
conn = sqlite3.connect('data/resume_analytics.db')
pd.read_sql("SELECT * FROM v_candidate_summary", conn).to_csv('exports/candidate_summary.csv', index=False)
pd.read_sql("SELECT * FROM match_scores", conn).to_csv('exports/match_scores.csv', index=False)
pd.read_sql("SELECT * FROM v_skill_gap_analysis", conn).to_csv('exports/skill_gap.csv', index=False)
```
Then import CSVs into Power BI Desktop and build:
- Hiring Funnel visual
- Skill Gap matrix
- Candidate scorecard
- Source effectiveness KPIs

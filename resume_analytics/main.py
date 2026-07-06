"""
AI-Powered Resume Screening Analytics
Main entry point — runs full pipeline then launches dashboard.
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))


def run_pipeline_only():
    from sample_data.generate_data import generate_all_data
    import json
    data = generate_all_data()
    os.makedirs("sample_data", exist_ok=True)
    with open("sample_data/resumes.json", "w") as f:
        json.dump(data["resumes"], f, indent=2)
    with open("sample_data/job_descriptions.json", "w") as f:
        json.dump(data["job_descriptions"], f, indent=2)
    print("[MAIN] Sample data generated.")

    from utils.pipeline import run_pipeline
    run_pipeline()


def run_dashboard():
    from dashboard.app import app
    print("\n[MAIN] Launching Dashboard -> http://127.0.0.1:8050")
    app.run(debug=False, port=8050)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resume Screening Analytics")
    parser.add_argument("--pipeline", action="store_true", help="Run ETL pipeline only")
    parser.add_argument("--dashboard", action="store_true", help="Launch dashboard only")
    parser.add_argument("--all", action="store_true", help="Run pipeline then launch dashboard")
    args = parser.parse_args()

    if args.pipeline:
        run_pipeline_only()
    elif args.dashboard:
        run_dashboard()
    else:
        # Default: run everything
        run_pipeline_only()
        run_dashboard()

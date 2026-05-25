#!/usr/bin/env python3
"""
Updates README.md with a daily job report table showing today's new matches.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


README_PATH = Path(__file__).parent.parent / "README.md"
DATA_DIR = Path(__file__).parent.parent / "data"

SEARCHES = [
    {"name": "Japanese Jobs (Remote)", "filename": "japanese-jobs.csv"},
    {"name": "HR Jobs (Local - WA/OR)", "filename": "hr-jobs.csv"},
]


def get_todays_jobs(csv_path: Path) -> pd.DataFrame:
    """Get jobs scraped today."""
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    if "scraped_at" not in df.columns:
        return pd.DataFrame()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    df["scraped_date"] = df["scraped_at"].str[:10]
    return df[df["scraped_date"] == today]


def jobs_to_table(jobs: pd.DataFrame) -> str:
    """Convert jobs DataFrame to a markdown table."""
    if jobs.empty:
        return "_No new jobs today_\n"

    lines = ["| Title | Company | Location | Link |", "|-------|---------|----------|------|"]

    for _, row in jobs.iterrows():
        title = str(row.get("title", "")).replace("|", "/")
        company = str(row.get("company", "")).replace("|", "/")
        location = str(row.get("location", "")).replace("|", "/")
        url = row.get("job_url", "")

        if pd.isna(title):
            title = ""
        if pd.isna(company):
            company = ""
        if pd.isna(location):
            location = ""
        if pd.isna(url):
            url = ""

        link = f"[Apply]({url})" if url else ""
        lines.append(f"| {title} | {company} | {location} | {link} |")

    return "\n".join(lines) + "\n"


def generate_report() -> str:
    """Generate the daily job report."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sections = [f"## Daily Job Report ({today})\n"]

    for search in SEARCHES:
        csv_path = DATA_DIR / search["filename"]
        jobs = get_todays_jobs(csv_path)

        sections.append(f"### {search['name']} ({len(jobs)} new)\n")
        sections.append(jobs_to_table(jobs))

    return "\n".join(sections)


def update_readme():
    """Update README.md with the daily job report."""
    readme = README_PATH.read_text()

    start_marker = "<!-- DAILY_REPORT_START -->"
    end_marker = "<!-- DAILY_REPORT_END -->"

    report = generate_report()
    new_content = f"{start_marker}\n{report}\n{end_marker}"

    if start_marker in readme and end_marker in readme:
        pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
        readme = re.sub(pattern, new_content, readme, flags=re.DOTALL)
    else:
        readme = readme.rstrip() + f"\n\n{new_content}\n"

    README_PATH.write_text(readme)
    print(f"Updated {README_PATH} with daily report")


if __name__ == "__main__":
    update_readme()

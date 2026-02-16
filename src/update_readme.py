#!/usr/bin/env python3
"""
Updates README.md with links to CSV snapshots from the last 30 days.
"""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote


REPO = "ayakacall/prospector"
README_PATH = Path(__file__).parent.parent / "README.md"

WORKFLOWS = [
    {
        "name": "Japanese Jobs (Remote)",
        "filename": "japanese-jobs.csv",
        "commit_msg_pattern": "Japanese jobs",
    },
    {
        "name": "HR Jobs",
        "filename": "hr-jobs.csv",
        "commit_msg_pattern": "HR jobs",
    },
]


def get_csv_commits(filename: str, days: int = 30) -> list[dict]:
    """Get commits that modified a specific CSV file in the last N days."""
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    result = subprocess.run(
        [
            "git", "log",
            f"--since={since_date}",
            "--format=%H|%ad|%s",
            "--date=short",
            "--",
            f"data/{filename}",
        ],
        capture_output=True,
        text=True,
    )

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({
                "sha": parts[0],
                "date": parts[1],
                "message": parts[2],
            })

    return commits


def generate_flatgithub_link(filename: str, sha: str) -> str:
    """Generate a flatgithub.com link for a specific commit."""
    encoded_path = quote(f"data/{filename}")
    return f"https://flatgithub.com/{REPO}?filename={encoded_path}&sha={sha}"


def generate_links_section() -> str:
    """Generate the markdown section with all CSV links."""
    sections = []

    for workflow in WORKFLOWS:
        commits = get_csv_commits(workflow["filename"])

        section = f"### {workflow['name']}\n\n"

        if not commits:
            section += "_No data yet_\n"
        else:
            for commit in commits:
                link = generate_flatgithub_link(workflow["filename"], commit["sha"])
                section += f"- [{commit['date']}]({link})\n"

        sections.append(section)

    return "\n".join(sections)


def update_readme():
    """Update README.md with the latest CSV links."""
    readme = README_PATH.read_text()

    # Markers for the auto-generated section
    start_marker = "<!-- CSV_LINKS_START -->"
    end_marker = "<!-- CSV_LINKS_END -->"

    links_section = generate_links_section()
    new_content = f"{start_marker}\n## Job Data\n\n{links_section}\n{end_marker}"

    if start_marker in readme and end_marker in readme:
        # Replace existing section
        import re
        pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
        readme = re.sub(pattern, new_content, readme, flags=re.DOTALL)
    else:
        # Append section before the end
        readme = readme.rstrip() + f"\n\n{new_content}\n"

    README_PATH.write_text(readme)
    print(f"Updated {README_PATH}")


if __name__ == "__main__":
    update_readme()

#!/usr/bin/env python3
"""
Prospector Job Scraper

Scrapes job postings from multiple job boards using JobSpy
and outputs to CSV for viewing with flatgithub.com
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs


def load_existing_jobs(csv_path: Path) -> set[str]:
    """Load existing job URLs to avoid duplicates."""
    if not csv_path.exists():
        return set()

    df = pd.read_csv(csv_path)
    if "job_url" in df.columns:
        return set(df["job_url"].dropna().tolist())
    return set()


def scrape_new_jobs(
    search_term: str,
    location: str = "United States",
    sites: list[str] | None = None,
    results_wanted: int = 50,
    hours_old: int = 24,
    distance: int = 50,
    is_remote: bool = False,
) -> pd.DataFrame:
    """Scrape jobs from configured sites."""
    if sites is None:
        sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter"]

    remote_str = " (remote only)" if is_remote else ""
    print(f"Scraping jobs for: '{search_term}' in '{location}' (within {distance} miles){remote_str}")
    print(f"Sites: {sites}")
    print(f"Looking for jobs posted in last {hours_old} hours")

    jobs = scrape_jobs(
        site_name=sites,
        search_term=search_term,
        location=location,
        distance=distance,
        results_wanted=results_wanted,
        hours_old=hours_old,
        is_remote=is_remote,
        country_indeed="USA",
    )

    print(f"Found {len(jobs)} jobs")
    return jobs


def filter_new_jobs(jobs: pd.DataFrame, existing_urls: set[str]) -> pd.DataFrame:
    """Filter out jobs we've already seen."""
    if jobs.empty:
        return jobs

    new_jobs = jobs[~jobs["job_url"].isin(existing_urls)]
    print(f"New jobs after deduplication: {len(new_jobs)}")
    return new_jobs


def filter_by_title(jobs: pd.DataFrame, include_keywords: list[str] | None = None, exclude_keywords: list[str] | None = None) -> pd.DataFrame:
    """Filter jobs by title keywords."""
    if jobs.empty:
        return jobs

    original_count = len(jobs)

    if include_keywords:
        pattern = "|".join(include_keywords)
        jobs = jobs[jobs["title"].str.contains(pattern, case=False, na=False)]

    if exclude_keywords:
        pattern = "|".join(exclude_keywords)
        jobs = jobs[~jobs["title"].str.contains(pattern, case=False, na=False)]

    filtered_count = original_count - len(jobs)
    if filtered_count > 0:
        print(f"Title filter removed {filtered_count} jobs, keeping {len(jobs)}")

    return jobs


def filter_remote_only(jobs: pd.DataFrame) -> pd.DataFrame:
    """Keep only jobs that are explicitly remote."""
    if jobs.empty:
        return jobs

    original_count = len(jobs)

    mask = (
        jobs["title"].str.lower().str.contains("remote", na=False)
        | jobs["location"].str.lower().str.contains("remote", na=False)
    )

    # Also keep if job_type contains remote
    if "job_type" in jobs.columns:
        mask = mask | jobs["job_type"].str.lower().str.contains("remote", na=False)

    remote_jobs = jobs[mask]

    filtered_count = original_count - len(remote_jobs)
    if filtered_count > 0:
        print(f"Remote filter removed {filtered_count} non-remote jobs, keeping {len(remote_jobs)}")

    return remote_jobs


def filter_local_only(jobs: pd.DataFrame, allowed_states: list[str] | None = None) -> pd.DataFrame:
    """Filter out remote jobs and jobs outside allowed states."""
    if jobs.empty:
        return jobs

    original_count = len(jobs)

    # Remove jobs marked as remote
    mask = ~(
        jobs["title"].str.lower().str.contains("remote", na=False)
        | jobs["location"].str.lower().str.contains("remote", na=False)
    )
    jobs = jobs[mask]

    # If allowed_states provided, only keep jobs in those states
    if allowed_states:
        state_pattern = "|".join(allowed_states)
        jobs = jobs[jobs["location"].str.contains(state_pattern, case=False, na=False)]

    filtered_count = original_count - len(jobs)
    if filtered_count > 0:
        print(f"Local filter removed {filtered_count} jobs, keeping {len(jobs)}")

    return jobs


def save_jobs(jobs: pd.DataFrame, csv_path: Path, append: bool = True) -> None:
    """Save jobs to CSV, optionally appending to existing file."""
    if jobs.empty:
        print("No new jobs to save")
        return

    jobs = jobs.copy()
    jobs["scraped_at"] = datetime.utcnow().isoformat()

    columns = [
        "title",
        "company",
        "location",
        "job_type",
        "date_posted",
        "min_amount",
        "max_amount",
        "job_url",
        "site",
        "description",
        "scraped_at",
    ]

    columns = [c for c in columns if c in jobs.columns]
    jobs = jobs[columns]

    if append and csv_path.exists():
        existing = pd.read_csv(csv_path)
        jobs = pd.concat([existing, jobs], ignore_index=True)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    jobs.to_csv(csv_path, index=False)
    print(f"Saved {len(jobs)} total jobs to {csv_path}")


def main():
    search_term = os.environ.get("SEARCH_TERM", "japanese")
    location = os.environ.get("LOCATION", "United States")
    sites = os.environ.get("SITES", "indeed,linkedin,glassdoor").split(",")
    results_wanted = int(os.environ.get("RESULTS_WANTED", "50"))
    hours_old = int(os.environ.get("HOURS_OLD", "24"))
    distance = int(os.environ.get("DISTANCE", "50"))
    is_remote = os.environ.get("IS_REMOTE", "false").lower() == "true"
    local_only = os.environ.get("LOCAL_ONLY", "false").lower() == "true"
    output_file = os.environ.get("OUTPUT_FILE", "jobs.csv")

    include_titles = os.environ.get("INCLUDE_TITLES", "")
    exclude_titles = os.environ.get("EXCLUDE_TITLES", "")
    include_keywords = [k.strip() for k in include_titles.split(",") if k.strip()] or None
    exclude_keywords = [k.strip() for k in exclude_titles.split(",") if k.strip()] or None

    allowed_states_str = os.environ.get("ALLOWED_STATES", "")
    allowed_states = [s.strip() for s in allowed_states_str.split(",") if s.strip()] or None
    remote_only = os.environ.get("REMOTE_ONLY", "false").lower() == "true"

    data_dir = Path(__file__).parent.parent.parent / "data"
    csv_path = data_dir / output_file

    existing_urls = load_existing_jobs(csv_path)
    print(f"Existing jobs in database: {len(existing_urls)}")

    jobs = scrape_new_jobs(
        search_term=search_term,
        location=location,
        sites=sites,
        results_wanted=results_wanted,
        hours_old=hours_old,
        distance=distance,
        is_remote=is_remote,
    )

    new_jobs = filter_new_jobs(jobs, existing_urls)

    if local_only:
        new_jobs = filter_local_only(new_jobs, allowed_states=allowed_states)

    if remote_only:
        new_jobs = filter_remote_only(new_jobs)

    new_jobs = filter_by_title(new_jobs, include_keywords, exclude_keywords)

    save_jobs(new_jobs, csv_path, append=True)

    print(f"\n::notice::Found {len(new_jobs)} new jobs for '{search_term}'")

    return 0


if __name__ == "__main__":
    sys.exit(main())

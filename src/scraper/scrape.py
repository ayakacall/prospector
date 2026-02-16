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
    results_wanted: int = 100,
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


def filter_local_only(jobs: pd.DataFrame) -> pd.DataFrame:
    """Filter out remote jobs, keeping only local positions."""
    if jobs.empty:
        return jobs

    original_count = len(jobs)

    # Filter out jobs with "remote" in title or location (case-insensitive)
    mask = ~(
        jobs["title"].str.lower().str.contains("remote", na=False)
        | jobs["location"].str.lower().str.contains("remote", na=False)
    )
    local_jobs = jobs[mask]

    filtered_count = original_count - len(local_jobs)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} remote jobs, keeping {len(local_jobs)} local jobs")

    return local_jobs


def save_jobs(jobs: pd.DataFrame, csv_path: Path, append: bool = True) -> None:
    """Save jobs to CSV, optionally appending to existing file."""
    if jobs.empty:
        print("No new jobs to save")
        return

    # Add scraped timestamp
    jobs = jobs.copy()
    jobs["scraped_at"] = datetime.utcnow().isoformat()

    # Select and order columns for clean output
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

    # Only keep columns that exist
    columns = [c for c in columns if c in jobs.columns]
    jobs = jobs[columns]

    if append and csv_path.exists():
        existing = pd.read_csv(csv_path)
        jobs = pd.concat([existing, jobs], ignore_index=True)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    jobs.to_csv(csv_path, index=False)
    print(f"Saved {len(jobs)} total jobs to {csv_path}")


def main():
    # Configuration from environment variables
    search_term = os.environ.get("SEARCH_TERM", "japanese")
    location = os.environ.get("LOCATION", "United States")
    sites = os.environ.get("SITES", "indeed,linkedin,glassdoor").split(",")
    results_wanted = int(os.environ.get("RESULTS_WANTED", "100"))
    hours_old = int(os.environ.get("HOURS_OLD", "24"))
    distance = int(os.environ.get("DISTANCE", "50"))
    is_remote = os.environ.get("IS_REMOTE", "false").lower() == "true"
    local_only = os.environ.get("LOCAL_ONLY", "false").lower() == "true"
    output_file = os.environ.get("OUTPUT_FILE", "jobs.csv")

    # Output path
    data_dir = Path(__file__).parent.parent.parent / "data"
    csv_path = data_dir / output_file

    # Load existing jobs for deduplication
    existing_urls = load_existing_jobs(csv_path)
    print(f"Existing jobs in database: {len(existing_urls)}")

    # Scrape new jobs
    jobs = scrape_new_jobs(
        search_term=search_term,
        location=location,
        sites=sites,
        results_wanted=results_wanted,
        hours_old=hours_old,
        distance=distance,
        is_remote=is_remote,
    )

    # Filter to only new jobs
    new_jobs = filter_new_jobs(jobs, existing_urls)

    # Filter out remote jobs if local_only is set
    if local_only:
        new_jobs = filter_local_only(new_jobs)

    # Save results
    save_jobs(new_jobs, csv_path, append=True)

    # Output summary for GitHub Actions
    print(f"\n::notice::Found {len(new_jobs)} new jobs for '{search_term}'")

    return 0 if not new_jobs.empty else 0  # Always succeed


if __name__ == "__main__":
    sys.exit(main())

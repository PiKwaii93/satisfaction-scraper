"""Read-only deployment KPIs from GitHub Actions (no VM access)."""

import argparse
import json
import os
from datetime import datetime, timezone
from urllib.request import Request, urlopen


DEPLOY_STEP = "Deploy and check API and frontend"


def seconds_between(start, end):
    if not start or not end:
        return None
    return int((datetime.fromisoformat(end.replace("Z", "+00:00")) -
                datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds())


def classify_run(run, jobs):
    steps = [step for job in jobs for step in job.get("steps", [])]
    failed = next((step for step in steps if step.get("conclusion") == "failure"), None)
    deployed = next((step for step in steps if step.get("name") == DEPLOY_STEP), None)
    if run["conclusion"] == "success" and deployed and deployed.get("conclusion") == "success":
        phase = "deployed"
    elif failed:
        phase = "pre-deployment" if not deployed or deployed.get("conclusion") == "skipped" else "deployment"
    else:
        phase = "unknown"
    return {
        "run_id": run["id"],
        "sha": run["head_sha"],
        "created_at": run["created_at"],
        "conclusion": run["conclusion"],
        "deployed": phase == "deployed",
        "failure_phase": phase if run["conclusion"] != "success" else None,
        "failed_step": failed["name"] if failed else None,
        "cycle_seconds": seconds_between(run["created_at"], deployed.get("completed_at"))
        if phase == "deployed" else None,
        "workflow_seconds": seconds_between(run["created_at"], run.get("updated_at")),
        "url": run.get("html_url"),
    }


def summarize(rows):
    successes = [row for row in rows if row["conclusion"] == "success" and row["deployed"]]
    days = {row["created_at"][:10] for row in successes}
    return {
        "attempts": len(rows),
        "successful_deployments": len(successes),
        "success_rate": len(successes) / len(rows) if rows else None,
        "deployment_frequency_by_utc_day": {
            day: sum(row["created_at"].startswith(day) for row in successes) for day in sorted(days)
        },
        "cycle_seconds_by_run": {str(row["run_id"]): row["cycle_seconds"] for row in successes},
    }


def github_get(path, token):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "satisfaction-deployment-kpis"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request("https://api.github.com/" + path, headers=headers), timeout=20) as response:
        return json.load(response)


def collect(repo, limit, since, token):
    rows = []
    page = 1
    while len(rows) < limit:
        path = f"repos/{repo}/actions/workflows/deploy-test.yml/runs?event=workflow_dispatch&per_page=100&page={page}"
        runs = github_get(path, token)["workflow_runs"]
        if not runs:
            break
        for run in runs:
            if since and run["created_at"][:10] < since:
                return rows
            if run["status"] != "completed":
                continue
            jobs_path = f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100"
            jobs = github_get(jobs_path, token)["jobs"]
            rows.append(classify_run(run, jobs))
            if len(rows) == limit:
                break
        page += 1
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "PiKwaii93/satisfaction-scraper"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--since", help="Inclusive UTC date, YYYY-MM-DD")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 1000:
        parser.error("--limit must be between 1 and 1000")
    if args.since:
        try:
            datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            parser.error("--since must be YYYY-MM-DD")
    if not all(part and part.replace("-", "").replace("_", "").isalnum() for part in args.repo.split("/")) or args.repo.count("/") != 1:
        parser.error("--repo must be owner/name")
    rows = collect(args.repo, args.limit, args.since, os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    print(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "repository": args.repo,
                      "since": args.since, "summary": summarize(rows), "runs": rows}, indent=2))


if __name__ == "__main__":
    main()

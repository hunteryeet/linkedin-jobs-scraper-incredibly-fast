thonfrom dataclasses import dataclass
from typing import Any, Dict, List

@dataclass
class FilterCriteria:
    title_contains: List[str]
    locations: List[str]
    seniority_levels: List[str]
    employment_types: List[str]

def _matches_any(value: str, options: List[str]) -> bool:
    if not options:
        return True
    value_lower = value.lower()
    return any(opt.lower() in value_lower for opt in options)

def filter_jobs(jobs: List[Dict[str, Any]], criteria: FilterCriteria) -> List[Dict[str, Any]]:
    """
    Filter job dictionaries according to the provided criteria.
    All checks are case-insensitive and allow partial matches.
    """
    filtered: List[Dict[str, Any]] = []
    for job in jobs:
        title = str(job.get("job_title", ""))
        location = str(job.get("location", ""))
        seniority = str(job.get("seniority_level", ""))
        employment_type = str(job.get("employment_type", ""))

        if not _matches_any(title, criteria.title_contains):
            continue
        if not _matches_any(location, criteria.locations):
            continue
        if criteria.seniority_levels and seniority.lower() not in {
            lvl.lower() for lvl in criteria.seniority_levels
        }:
            continue
        if criteria.employment_types and employment_type.lower() not in {
            t.lower() for t in criteria.employment_types
        }:
            continue

        filtered.append(job)

    return filtered
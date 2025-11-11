thonimport argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Ensure local src directory is importable when running from repo root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from extractors.linkedin_parser import LinkedInJobScraper  # type: ignore
from extractors.filters import FilterCriteria, filter_jobs  # type: ignore
from utils.proxy_manager import ProxyManager  # type: ignore
from utils.data_exporter import DataExporter  # type: ignore

def load_settings(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("Settings file not found at %s, using defaults.", config_path)
        return {}
    except json.JSONDecodeError as exc:
        logging.error("Failed to parse settings.json: %s", exc)
        return {}

def build_search_url(base_url: str, query: Optional[str], location: Optional[str]) -> str:
    from urllib.parse import urlencode

    params = {}
    if query:
        params["keywords"] = query
    if location:
        params["location"] = location

    if not params:
        return base_url

    return f"{base_url}?{urlencode(params)}"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape LinkedIn job listings quickly and export results."
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Direct LinkedIn jobs search URL. If omitted, --query and --location are used.",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Job search query, e.g. 'Software Engineer'.",
    )
    parser.add_argument(
        "--location",
        type=str,
        help="Job location, e.g. 'New York, NY'.",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        help="Maximum number of jobs to scrape.",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "csv", "excel", "xml", "html"],
        help="Output format for scraped jobs.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help="Path to the output file. Extension does not determine the format.",
    )
    parser.add_argument(
        "--title-contains",
        nargs="*",
        help="Filter: job titles must contain one of these terms (case-insensitive).",
    )
    parser.add_argument(
        "--locations",
        nargs="*",
        help="Filter: keep only jobs whose location contains one of these values.",
    )
    parser.add_argument(
        "--seniority-levels",
        nargs="*",
        help="Filter: allowed seniority levels, e.g. Entry, Mid, Senior.",
    )
    parser.add_argument(
        "--employment-types",
        nargs="*",
        help="Filter: allowed employment types, e.g. Full-Time, Contract.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(CURRENT_DIR, "config", "settings.json"),
        help="Path to settings.json configuration file.",
    )
    return parser.parse_args()

def create_filter_criteria(args: argparse.Namespace) -> FilterCriteria:
    return FilterCriteria(
        title_contains=args.title_contains or [],
        locations=args.locations or [],
        seniority_levels=args.seniority_levels or [],
        employment_types=args.employment_types or [],
    )

def determine_output_path(
    args: argparse.Namespace, default_format: str, default_dir: str = "data"
) -> str:
    if args.output_file:
        return args.output_file
    os.makedirs(default_dir, exist_ok=True)
    return os.path.join(default_dir, f"linkedin_jobs.{default_format}")

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("linkedin_main")

    args = parse_args()
    settings = load_settings(args.config)

    max_jobs = args.max_jobs or settings.get("max_jobs", 1000)
    output_format = args.output_format or settings.get("output_format", "json")
    if output_format not in {"json", "csv", "excel", "xml", "html"}:
        logger.error("Unsupported output format configured: %s", output_format)
        sys.exit(1)

    output_path = determine_output_path(args, output_format)

    base_url = settings.get(
        "base_search_url", "https://www.linkedin.com/jobs/search"
    )

    if args.url:
        search_url = args.url
        logger.info("Using direct LinkedIn URL: %s", search_url)
    else:
        if not args.query and not args.location:
            logger.error(
                "Either --url or at least one of --query/--location must be provided."
            )
            sys.exit(1)
        search_url = build_search_url(base_url, args.query, args.location)
        logger.info("Built LinkedIn search URL: %s", search_url)

    proxy_list: List[str] = settings.get("proxies", [])
    proxy_manager = ProxyManager(proxy_list) if proxy_list else None

    scraper = LinkedInJobScraper(
        proxy_manager=proxy_manager,
        max_retries=settings.get("max_retries", 3),
        request_timeout=settings.get("request_timeout", 20),
        delay_range=tuple(settings.get("delay_range", [0.5, 1.5])),  # type: ignore[arg-type]
    )

    try:
        logger.info("Starting scrape: max_jobs=%d", max_jobs)
        jobs = scraper.scrape_search(search_url, max_jobs=max_jobs)
    except Exception as exc:
        logger.exception("Scraping failed: %s", exc)
        sys.exit(1)

    logger.info("Scraped %d jobs before filtering.", len(jobs))

    criteria = create_filter_criteria(args)
    filtered_jobs = filter_jobs(jobs, criteria)

    logger.info(
        "Filtered jobs: %d remaining after applying criteria.", len(filtered_jobs)
    )

    if not filtered_jobs:
        logger.warning("No jobs remained after filtering; nothing to export.")
        sys.exit(0)

    try:
        DataExporter.export(filtered_jobs, output_format, output_path)
        logger.info(
            "Exported %d jobs to '%s' as %s.",
            len(filtered_jobs),
            output_path,
            output_format,
        )
    except Exception as exc:
        logger.exception("Failed to export data: %s", exc)
        sys.exit(1)

if __name__ == "__main__":
    main()
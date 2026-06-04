from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
OUTPUT_DIR = ROOT / "data" / "api_samples"


P0_QUERIES = [
    "민법 제750조",
    "민법 제751조",
    "민법 제763조",
    "민법 제393조",
    "민법 제396조",
    "자동차손해배상 보장법 제3조",
]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_oc() -> str:
    oc = os.getenv("LAW_API_OC") or os.getenv("LAW_API_KEY")
    if not oc:
        print(
            "LAW_API_OC is missing. Add your open.law.go.kr OC value to .env, then rerun.",
            file=sys.stderr,
        )
        return ""
    return oc


def build_url(path: str, params: dict[str, Any]) -> str:
    base_url = os.getenv("LAW_API_BASE_URL", "https://www.law.go.kr/DRF").rstrip("/")
    return f"{base_url}/{path}?{urlencode(params, doseq=True)}"


def request_api(path: str, params: dict[str, Any], timeout: int) -> tuple[str, bytes]:
    url = build_url(path, params)
    request = Request(url, headers={"User-Agent": "CaseLens-MVP/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return url, response.read()


def parse_json_or_text(payload: bytes) -> Any:
    text = payload.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw_text": text}


def save_payload(name: str, url: str, payload: bytes) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    parsed = parse_json_or_text(payload)
    out = {
        "requested_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "url": mask_oc(url),
        "response": mask_secret_values(parsed),
    }
    path = OUTPUT_DIR / f"{name}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def mask_oc(url: str) -> str:
    oc = os.getenv("LAW_API_OC") or os.getenv("LAW_API_KEY") or ""
    return url.replace(oc, "***") if oc else url


def mask_secret_values(value: Any) -> Any:
    oc = os.getenv("LAW_API_OC") or os.getenv("LAW_API_KEY") or ""
    if isinstance(value, str):
        return value.replace(oc, "***") if oc else value
    if isinstance(value, list):
        return [mask_secret_values(item) for item in value]
    if isinstance(value, dict):
        return {key: mask_secret_values(item) for key, item in value.items()}
    return value


def first_item(value: Any, candidate_keys: list[str]) -> dict[str, Any] | None:
    if isinstance(value, dict):
        for key in candidate_keys:
            current = value.get(key)
            if isinstance(current, list) and current:
                return current[0] if isinstance(current[0], dict) else None
            if isinstance(current, dict):
                return current
        for child in value.values():
            found = first_item(child, candidate_keys)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = first_item(child, candidate_keys)
            if found:
                return found
    return None


def first_matching_item(
    value: Any,
    candidate_keys: list[str],
    field_name: str,
    expected_value: str,
) -> dict[str, Any] | None:
    if isinstance(value, dict):
        for key in candidate_keys:
            current = value.get(key)
            items = current if isinstance(current, list) else [current]
            for item in items:
                if isinstance(item, dict) and item.get(field_name) == expected_value:
                    return item
        for child in value.values():
            found = first_matching_item(child, candidate_keys, field_name, expected_value)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = first_matching_item(child, candidate_keys, field_name, expected_value)
            if found:
                return found
    return None


def find_key(value: Any, names: set[str]) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in names:
                return item
        for item in value.values():
            found = find_key(item, names)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_key(item, names)
            if found:
                return found
    return None


def find_first_key(value: Any, names: list[str]) -> Any:
    if isinstance(value, dict):
        for name in names:
            item = value.get(name)
            if item:
                return item
        for item in value.values():
            found = find_first_key(item, names)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_first_key(item, names)
            if found:
                return found
    return None


def call_and_save(name: str, path: str, params: dict[str, Any], timeout: int) -> Any:
    url, payload = request_api(path, params, timeout)
    saved = save_payload(name, url, payload)
    print(f"[ok] {name}: {saved}")
    return parse_json_or_text(payload)


def run_probe(args: argparse.Namespace) -> int:
    load_dotenv(ENV_PATH)
    oc = require_oc()
    if not oc:
        return 2

    output_type = os.getenv("LAW_API_OUTPUT_TYPE", "JSON")
    display = int(os.getenv("LAW_API_SAMPLE_DISPLAY", str(args.display)))
    common = {"OC": oc, "type": output_type}

    law_search = call_and_save(
        "01_law_search_minbeop",
        "lawSearch.do",
        {
            **common,
            "target": "eflaw",
            "query": "민법",
            "display": display,
            "page": 1,
            "nw": 3,
        },
        args.timeout,
    )

    law_item = first_matching_item(law_search, ["law", "Law", "법령"], "법령명한글", "민법")
    law_id = find_first_key(law_item, ["법령ID", "lawId"]) if law_item else None
    if law_id:
        call_and_save(
            "02_law_detail_minbeop",
            "lawService.do",
            {**common, "target": "eflaw", "ID": law_id},
            args.timeout,
        )
    else:
        print("[warn] Could not find law ID from law search response; skipped law detail.")

    case_search = call_and_save(
        "03_case_search_damages",
        "lawSearch.do",
        {
            **common,
            "target": "prec",
            "query": args.case_query,
            "search": 2,
            "display": display,
            "page": 1,
            "sort": "ddes",
        },
        args.timeout,
    )

    case_item = first_item(case_search, ["prec", "Prec", "판례"])
    case_id = find_first_key(case_item, ["판례일련번호", "ID"]) if case_item else None
    if case_id:
        call_and_save(
            "04_case_detail_first_result",
            "lawService.do",
            {**common, "target": "prec", "ID": case_id},
            args.timeout,
        )
    else:
        print("[warn] Could not find case ID from case search response; skipped case detail.")

    for index, query in enumerate(P0_QUERIES, start=1):
        safe_name = f"05_p0_case_search_{index:02d}"
        call_and_save(
            safe_name,
            "lawSearch.do",
            {
                **common,
                "target": "prec",
                "query": query,
                "search": 2,
                "display": display,
                "page": 1,
                "sort": "ddes",
            },
            args.timeout,
        )

    print("\nProbe complete. Review JSON files under data/api_samples.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe open.law.go.kr APIs for CaseLens MVP.")
    parser.add_argument("--case-query", default="손해배상", help="Sample precedent body-search query.")
    parser.add_argument("--display", type=int, default=5, help="Number of search results per sample.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds.")
    args = parser.parse_args()
    return run_probe(args)


if __name__ == "__main__":
    raise SystemExit(main())

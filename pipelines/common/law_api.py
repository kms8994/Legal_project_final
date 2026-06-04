from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LawApiClient:
    oc: str
    base_url: str = "https://www.law.go.kr/DRF"
    output_type: str = "JSON"
    timeout: int = 20
    pause_seconds: float = 0.15

    def request_json(self, path: str, params: dict[str, Any]) -> Any:
        url = self.build_url(path, params)
        request = Request(url, headers={"User-Agent": "CaseLens-MVP/0.1"})
        with urlopen(request, timeout=self.timeout) as response:
            payload = response.read()
        if self.pause_seconds > 0:
            time.sleep(self.pause_seconds)
        return parse_json_or_text(payload)

    def build_url(self, path: str, params: dict[str, Any]) -> str:
        common = {"OC": self.oc, "type": self.output_type}
        query = urlencode({**common, **params}, doseq=True)
        return f"{self.base_url.rstrip('/')}/{path}?{query}"


def parse_json_or_text(payload: bytes) -> Any:
    text = payload.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw_text": text}


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def first_value(item: dict[str, Any] | None, names: list[str]) -> Any:
    if not item:
        return None
    for name in names:
        value = item.get(name)
        if value not in (None, ""):
            return value
    return None


def exact_match_item(value: Any, field_names: list[str], expected: str) -> dict[str, Any] | None:
    for item in iter_dicts(value):
        for field_name in field_names:
            if normalize_space(str(item.get(field_name, ""))) == expected:
                return item
    return None


def normalize_space(value: str) -> str:
    return " ".join(value.split())

#!/usr/bin/env python3
"""Refresh the vendored Tag Manager discovery document.

Run this when Google revises the API. If the refreshed document adds a method,
tests/test_api_coverage.py will fail until src/coverage.py and the matching tool
are updated -- which is the point.

Usage:
    uv run scripts/refresh_discovery.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

DISCOVERY_URL = "https://tagmanager.googleapis.com/$discovery/rest?version=v2"
TARGET = (
    Path(__file__).resolve().parent.parent / "refs" / "tagmanager.v2.discovery.json"
)


def method_paths(document: dict[str, object]) -> set[str]:
    """Every method path in a discovery document, e.g. 'accounts.list'."""
    found: set[str] = set()

    def walk(resources: dict[str, object], prefix: str = "") -> None:
        for name, resource in resources.items():
            assert isinstance(resource, dict)
            path = f"{prefix}{name}"
            for method in resource.get("methods") or {}:
                found.add(f"{path}.{method}")
            walk(resource.get("resources") or {}, f"{path}.")  # type: ignore[arg-type]

    walk(document.get("resources") or {})  # type: ignore[arg-type]
    return found


def main() -> int:
    with urllib.request.urlopen(DISCOVERY_URL, timeout=30) as response:
        document = json.loads(response.read().decode("utf-8"))

    previous_revision = None
    previous_methods: set[str] = set()
    if TARGET.exists():
        previous = json.loads(TARGET.read_text())
        previous_revision = previous.get("revision")
        previous_methods = method_paths(previous)

    TARGET.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")

    revision = document.get("revision")
    if previous_revision == revision:
        print(f"No change: still revision {revision}")
        return 0

    print(f"Updated: {previous_revision} -> {revision}")

    current_methods = method_paths(document)
    added = sorted(current_methods - previous_methods)
    removed = sorted(previous_methods - current_methods)

    if added:
        print(f"\n{len(added)} method(s) added:")
        for method in added:
            print(f"  + {method}")
    if removed:
        print(f"\n{len(removed)} method(s) removed:")
        for method in removed:
            print(f"  - {method}")
    if not added and not removed:
        print("\nNo methods added or removed; this revision is documentation only.")
    else:
        print("\nUpdate src/coverage.py and the matching tools, then run the tests.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextMatch:
    manager: str
    bench_root: Path
    bench: str | None = None

    def as_dict(self, site: str | None = None) -> dict[str, object]:
        prefix = ["bench"]
        if self.manager == "pilot":
            assert self.bench is not None
            prefix = ["pilot", "-b", self.bench]
        return {
            "manager": self.manager,
            "bench": self.bench,
            "bench_root": str(self.bench_root),
            "site": site,
            "manager_prefix": prefix,
        }


class ContextResolver:
    def __init__(
        self,
        cwd: Path,
        pilot_roots: list[Path],
        bench_roots: list[Path],
    ) -> None:
        self.cwd = cwd.resolve()
        self.pilot_roots = pilot_roots
        self.bench_roots = bench_roots

    def resolve(self, site: str | None) -> dict[str, object]:
        if site:
            matches = self._site_matches(site)
            if len(matches) == 1:
                return self._resolved(matches[0], site)
            if matches:
                return {
                    "status": "ambiguous",
                    "site": site,
                    "matches": [match.as_dict(site) for match in matches],
                    "message": "The site exists in more than one bench. Select a bench explicitly.",
                }
            return {
                "status": "unresolved",
                "site": site,
                "matches": [],
                "message": "The site was not found in a known Pilot or Bench root.",
            }

        match = self._nearest_context()
        if match:
            return self._resolved(match, site)
        return {
            "status": "unresolved",
            "site": None,
            "matches": [],
            "message": "The working directory is not inside a known Pilot or Bench root.",
        }

    def _resolved(self, match: ContextMatch, site: str | None) -> dict[str, object]:
        executable = shutil.which(match.manager)
        if not executable:
            result = match.as_dict(site)
            result.update(
                {
                    "status": "unavailable",
                    "message": f"The selected {match.manager} CLI is not on PATH.",
                }
            )
            return result

        result = match.as_dict(site)
        result.update(
            {
                "status": "resolved",
                "message": f"Use {match.manager} for this context.",
            }
        )
        return result

    def _site_matches(self, site: str) -> list[ContextMatch]:
        matches: list[ContextMatch] = []
        for pilot_root in self.pilot_roots:
            benches_dir = pilot_root / "benches"
            for bench_root in sorted(benches_dir.iterdir()):
                if not is_pilot_bench(bench_root):
                    continue
                if has_site(bench_root, site):
                    matches.append(ContextMatch("pilot", bench_root, bench_root.name))

        for bench_root in self.bench_roots:
            if is_legacy_bench(bench_root) and has_site(bench_root, site):
                matches.append(ContextMatch("bench", bench_root))

        return unique_matches(matches)

    def _nearest_context(self) -> ContextMatch | None:
        for directory in [self.cwd, *self.cwd.parents]:
            if is_pilot_bench(directory):
                return ContextMatch("pilot", directory, directory.name)
            if is_legacy_bench(directory):
                return ContextMatch("bench", directory)
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve whether a Frappe site or working directory uses Pilot or Bench."
    )
    parser.add_argument("--site", help="Existing site name to locate across known benches.")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Working directory to inspect.")
    parser.add_argument(
        "--pilot-root",
        action="append",
        type=Path,
        default=[],
        help="Pilot installation root. Can be passed more than once.",
    )
    parser.add_argument(
        "--bench-root",
        action="append",
        type=Path,
        default=[],
        help="Legacy Bench root. Can be passed more than once.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.site:
        validate_site_name(args.site)

    pilot_roots = discover_pilot_roots(args.cwd, args.pilot_root)
    bench_roots = discover_bench_roots(args.cwd, args.bench_root)
    result = ContextResolver(args.cwd, pilot_roots, bench_roots).resolve(args.site)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "resolved" else 1


def discover_pilot_roots(cwd: Path, explicit_roots: list[Path]) -> list[Path]:
    candidates = [*explicit_roots, *environment_paths("PILOT_ROOT")]
    if pilot_binary := shutil.which("pilot"):
        candidates.append(Path(pilot_binary).resolve().parent.parent)

    for directory in [cwd.resolve(), *cwd.resolve().parents]:
        if is_pilot_bench(directory) and directory.parent.name == "benches":
            candidates.append(directory.parent.parent)
            break

    return [path for path in unique_paths(candidates) if (path / "benches").is_dir()]


def discover_bench_roots(cwd: Path, explicit_roots: list[Path]) -> list[Path]:
    candidates = [*explicit_roots, *environment_paths("FRAPPE_BENCH_ROOTS")]
    for directory in [cwd.resolve(), *cwd.resolve().parents]:
        if is_legacy_bench(directory):
            candidates.append(directory)
            break
    return [path for path in unique_paths(candidates) if is_legacy_bench(path)]


def environment_paths(name: str) -> list[Path]:
    value = os.environ.get(name, "")
    return [Path(item) for item in value.split(os.pathsep) if item]


def unique_paths(paths: list[Path]) -> list[Path]:
    unique: dict[Path, None] = {}
    for path in paths:
        unique[path.expanduser().resolve()] = None
    return list(unique)


def unique_matches(matches: list[ContextMatch]) -> list[ContextMatch]:
    unique: dict[tuple[str, Path], ContextMatch] = {}
    for match in matches:
        unique[(match.manager, match.bench_root.resolve())] = match
    return list(unique.values())


def is_pilot_bench(path: Path) -> bool:
    return path.is_dir() and (path / "bench.toml").is_file()


def is_legacy_bench(path: Path) -> bool:
    return (
        path.is_dir()
        and not (path / "bench.toml").exists()
        and (path / "Procfile").is_file()
        and (path / "apps").is_dir()
        and (path / "sites").is_dir()
    )


def has_site(bench_root: Path, site: str) -> bool:
    return (bench_root / "sites" / site / "site_config.json").is_file()


def validate_site_name(site: str) -> None:
    if not site or Path(site).name != site or "/" in site or "\\" in site or site in {".", ".."}:
        raise SystemExit("Site must be a name, not a path.")


if __name__ == "__main__":
    sys.exit(main())

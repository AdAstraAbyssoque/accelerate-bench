#!/usr/bin/env python3
"""Copy one task into an immutable site profile with explicit CPU visibility.

Requires Python 3.11+ and PyYAML (available in the Harbor environment).
Example: --source TASK --output NEW_TASK --site site-cpus.json
The site JSON contains main, public_judge (if present), and verifier CPU sets.
This prepares files only; it does not start Docker or change a running task.
"""

import argparse
import hashlib
import json
import shutil
import tomllib
from pathlib import Path

import yaml


def cpu_set(value):
    if not isinstance(value, str) or not value:
        raise ValueError("CPU sets must be nonempty strings such as 56-59")
    result = set()
    for group in value.split(","):
        fields = group.split("-")
        if len(fields) not in (1, 2) or any(
            not s.isascii() or not s.isdigit() for s in fields
        ):
            raise ValueError("Invalid CPU set: " + value)
        first, last = int(fields[0]), int(fields[-1])
        if last < first or last - first > 65535:
            raise ValueError("Invalid CPU interval: " + group)
        part = set(range(first, last + 1))
        if result & part:
            raise ValueError("Repeated CPU in set: " + value)
        result |= part
    return result


def inventory(root):
    result = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("Symlink source needs explicit review: " + str(p))
        if p.is_file():
            with p.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            result[p.relative_to(root).as_posix()] = digest
    return result


def stage(source, output, site):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output == source or source in output.parents:
        raise ValueError("Output must be a new directory outside the source")
    if (source / "site-resource-profile.json").exists():
        raise ValueError(
            "Start from a reference task, not an already staged site profile"
        )
    if set(site) - {"main", "public_judge", "verifier"}:
        raise ValueError("Unknown site resource keys")
    original = inventory(source)
    task = tomllib.loads((source / "task.toml").read_text())
    environment_path = Path("environment/docker-compose.yaml")
    environment = (
        yaml.safe_load((source / environment_path).read_text())
        if (source / environment_path).exists()
        else {"services": {"main": {}}}
    )
    services = environment["services"]
    private_path = Path("tests/docker-compose.yaml")
    private = (
        yaml.safe_load((source / private_path).read_text())
        if (source / private_path).exists()
        else {"services": {}}
    )
    counts = {
        "main": task["environment"]["cpus"],
        "verifier": task["verifier"]["environment"]["cpus"],
    }
    if "public-judge" in services:
        counts["public_judge"] = services["public-judge"]["cpus"]
    if set(site) != set(counts):
        raise ValueError("Provide exactly these CPU sets: " + ", ".join(sorted(counts)))
    parsed = {key: cpu_set(value) for key, value in site.items()}
    for key, count in counts.items():
        if type(count) not in (int, float) or count <= 0 or int(count) != count:
            raise ValueError(
                "Reference CPU visibility requires positive whole CPU counts"
            )
        if len(parsed[key]) != int(count):
            raise ValueError(
                f"{key} requires {count} visible CPUs, got {len(parsed[key])}"
            )
    # Main and public judge coexist; a separate verifier runs after their cleanup.
    if "public_judge" in parsed and parsed["main"] & parsed["public_judge"]:
        raise ValueError("Main and public judge CPU sets must be disjoint")
    services["main"]["cpuset"] = site["main"]
    if "public_judge" in parsed:
        services["public-judge"]["cpuset"] = site["public_judge"]
    private.setdefault("services", {}).setdefault("main", {})["cpuset"] = site[
        "verifier"
    ]
    # Preserve private network-sidecar hostname and all existing isolation settings.
    shutil.copytree(source, output)
    assert inventory(output) == original
    (output / environment_path).write_text(yaml.safe_dump(environment, sort_keys=False))
    (output / private_path).write_text(yaml.safe_dump(private, sort_keys=False))
    final = inventory(output)
    changed = {
        key
        for key in original.keys() | final.keys()
        if original.get(key) != final.get(key)
    }
    assert changed <= {environment_path.as_posix(), private_path.as_posix()}
    assert inventory(source) == original
    receipt = {
        "source": str(source),
        "output": str(output),
        "site": site,
        "declared_cpu_counts": counts,
        "source_inventory": original,
        "staged_inventory": final,
        "changed_paths": sorted(changed),
        "scope": "Site CPU placement only. Task logic, guards, quotas, model and scores unchanged. "
        "Verify available CPUs, concurrent reservations and actual agent/public/private "
        "container affinity before comparable evaluation. Does not prove performance isolation.",
    }
    (output / "site-resource-profile.json").write_text(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--site", required=True, type=Path)
    args = parser.parse_args()
    result = stage(args.source, args.output, json.loads(args.site.read_text()))
    print(
        json.dumps(
            {
                "output": result["output"],
                "changed_paths": result["changed_paths"],
                "site": result["site"],
            }
        )
    )

#!/usr/bin/env python3
"""Prepare, inspect, or explicitly run one canonical task using public Harbor/Docker."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml
from native_resource_profile import cpu_set, inventory, stage

HERE = Path(__file__).resolve().parent


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        while b := f.read(1024**2):
            h.update(b)
    return h.hexdigest()


def harbor(*args):
    if importlib.metadata.version("harbor") != "0.22.0":
        raise ValueError("Harbor 0.22.0 required")
    return [sys.executable, "-m", "harbor.cli.main", "run", *args]


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def verify_canonical(source, manifest):
    records = read(manifest)["files"]
    expected = {
        r["path"].split("/", 1)[1]: r["sha256"]
        for r in records
        if r["path"].startswith(source.name + "/")
    }
    if not expected or inventory(source) != expected:
        raise ValueError(
            "Task source differs from canonical manifest; hydrate missing external data first"
        )
    return len(expected)


def resolve(command):
    # Only Harbor's existing print-config branch is called here: no Docker/model work.
    p = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(p.stdout)


def prepare(a):
    source = a.task.resolve()
    workspace = a.work_dir.resolve()
    manifest = a.manifest.resolve()
    if workspace.exists() or workspace == source or source in workspace.parents:
        raise ValueError("Use a fresh workspace outside the task source")
    count = verify_canonical(source, manifest)
    task = tomllib.loads((source / "task.toml").read_text())
    if (
        task["agent"]["timeout_sec"] != 28800
        or task["verifier"]["environment_mode"] != "separate"
    ):
        raise ValueError("Expected canonical eight-hour/separate-verifier task")
    site = {"main": a.main_cpus, "verifier": a.verifier_cpus}
    if a.public_cpus is not None:
        site["public_judge"] = a.public_cpus
    workspace.mkdir(parents=True)
    staged = workspace / "task" / source.name
    profile = stage(source, staged, site)
    config = resolve(
        harbor(
            "--path",
            str(staged),
            "--agent",
            "claude-code",
            "--model",
            a.model,
            "--agent-kwarg",
            "reasoning_effort=high",
            "--agent-kwarg",
            "version=2.1.265",
            "--agent-env",
            "API_TIMEOUT_MS=7200000",
            "--agent-env",
            "CLAUDE_STREAM_IDLE_TIMEOUT_MS=7200000",
            "--agent-env",
            "CLAUDE_BYTE_STREAM_IDLE_TIMEOUT_MS=7200000",
            "--env",
            "docker",
            "--force-build",
            "--jobs-dir",
            str(workspace / "jobs"),
            "--job-name",
            "accelerate-" + source.name,
            "--n-attempts",
            "1",
            "--n-concurrent",
            "1",
            "--max-retries",
            "0",
            "--print-config",
        )
    )
    save(workspace / "job.json", config)
    cpath = source / "environment/docker-compose.yaml"
    compose = yaml.safe_load(cpath.read_text()) if cpath.exists() else {"services": {}}
    public = compose["services"].get("public-judge")
    receipt = {
        "task_id": source.name,
        "canonical_manifest_sha256": sha(manifest),
        "canonical_task_files": count,
        "canonical_source": str(source),
        "task_toml_sha256": sha(source / "task.toml"),
        "staged_task": str(staged),
        "staged_inventory": inventory(staged),
        "cpu_placement": site,
        "main_cpu": task["environment"]["cpus"],
        "main_memory_mb": task["environment"]["memory_mb"],
        "public_judge_original_limits": {
            k: public.get(k) for k in ["cpus", "mem_limit"]
        }
        if public
        else None,
        "private_environment": task["verifier"]["environment"],
        "agent_timeout_sec": 28800,
        "verifier_timeout_sec": task["verifier"]["timeout_sec"],
        "profile_changed_paths": profile["changed_paths"],
        "job_sha256": sha(workspace / "job.json"),
        "harbor_version": "0.22.0",
        "claude_code_version": "2.1.265",
        "model": a.model,
        "attempts": 1,
        "concurrency": 1,
        "max_retries": 0,
        "execution_started": False,
        "native_host_and_reference_validation": "Not established by print-config. See INSTALL-NATIVE.md.",
    }
    save(workspace / "native-preparation.json", receipt)
    print(
        json.dumps(
            {
                "workspace": str(workspace),
                "job_config": str(workspace / "job.json"),
                "task": source.name,
                "prepared": True,
                "executed": False,
            }
        )
    )


def validate_workspace(workspace):
    workspace = workspace.resolve()
    r = read(workspace / "native-preparation.json")
    if (
        sha(workspace / "job.json") != r["job_sha256"]
        or inventory(Path(r["staged_task"])) != r["staged_inventory"]
    ):
        raise ValueError("Prepared input/config changed; create a new workspace")
    # No credentials are serialized into job.json: standard provider environment is inherited only at run time.
    return workspace, r


def check_host(r):
    if platform.system() != "Linux" or platform.machine() not in ["x86_64", "amd64"]:
        raise ValueError(
            "Native execution requires Linux x86_64; static preparation is portable"
        )
    allowed = os.sched_getaffinity(0)
    sets = {k: cpu_set(v) for k, v in r["cpu_placement"].items()}
    if any(not v <= allowed for v in sets.values()):
        raise ValueError("Chosen CPU set is not available to this host process")
    # Avoid counting SMT siblings as distinct allocated physical cores.
    simultaneous = set().union(sets["main"], sets.get("public_judge", set()))
    for cpus in [simultaneous, sets["verifier"]]:
        for cpu in cpus:
            siblings = cpu_set(
                Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
                .read_text()
                .strip()
            )
            if len(siblings & cpus) > 1:
                raise ValueError("Choose one hardware thread per physical core")
    if (
        os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock").split(":", 1)[0]
        != "unix"
    ):
        raise ValueError("CPU-placement checks require a local Docker daemon")
    endpoint = subprocess.check_output(
        ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        text=True,
    ).strip()
    if not endpoint.startswith("unix://"):
        raise ValueError("Use a local Docker context for native CPU placement")
    if (
        subprocess.check_output(
            ["docker", "info", "--format", "{{.OSType}}"], text=True
        ).strip()
        != "linux"
    ):
        raise ValueError("Linux Docker daemon required")
    subprocess.run(["docker", "compose", "version"], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    q = sub.add_parser("prepare")
    q.add_argument("--task", type=Path, required=True)
    q.add_argument("--manifest", type=Path, default=HERE / "RELEASE-MANIFEST.json")
    q.add_argument("--work-dir", type=Path, required=True)
    q.add_argument("--model", required=True)
    q.add_argument("--main-cpus", required=True)
    q.add_argument("--public-cpus")
    q.add_argument("--verifier-cpus", required=True)
    for name in ["print-config", "run"]:
        q = sub.add_parser(name)
        q.add_argument("--work-dir", type=Path, required=True)
    a = p.parse_args()
    if a.action == "prepare":
        prepare(a)
        return
    workspace, r = validate_workspace(a.work_dir)
    if a.action == "print-config":
        print(
            json.dumps(
                resolve(
                    harbor("--config", str(workspace / "job.json"), "--print-config")
                ),
                indent=2,
            )
        )
        return
    check_host(r)
    if not any(
        os.environ.get(k) for k in ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"]
    ):
        raise ValueError(
            "Set a supported provider credential in the host environment; never in a config file"
        )
    if (workspace / "jobs").exists():
        raise ValueError(
            "Job output already exists; preserve it and do not repeat this attempt"
        )
    fd = os.open(
        workspace / "run-intent.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
    )
    with os.fdopen(fd, "w") as f:
        json.dump(
            {
                "task_id": r["task_id"],
                "job_sha256": r["job_sha256"],
                "attempts": 1,
                "automatic_retries": 0,
            },
            f,
        )
        f.flush()
        os.fsync(f.fileno())
    # Explicit foreground execution only. No daemon, launch loop, or automatic retry.
    code = subprocess.run(
        harbor("--config", str(workspace / "job.json"), "--yes"),
        check=False,
        cwd=workspace,
    ).returncode
    save(
        workspace / "process-exit.json",
        {"returncode": code, "valid_score_not_inferred_from_exit_code": True},
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()

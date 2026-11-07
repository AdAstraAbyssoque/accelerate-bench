# Native Linux evaluation

Run these commands from the repository root after downloading the task assets. Use Linux x86-64, Python 3.12+, local Docker Engine and Docker Compose v2. The daemon must enforce the task's original CPU sets, memory, namespaces, capabilities and seccomp settings. This entry point does not run evaluations through Docker Desktop or a remote Docker context.

## Install and verify

```sh
python3 public-release/fetch_external_data.py --only icon-grid-0013 \
  --cache ./asset-cache --hydrate ./canonical/tasks
python3 public-release/verify_source.py --source ./canonical/tasks
PYTHON_BIN=python3.12 bash public-release/install-native.sh .venv-native
```

The installer creates a new virtual environment and refuses to overwrite one. Direct dependencies pin Harbor 0.22.0 and the YAML parser; transitive dependencies are resolved from public PyPI. Harbor installs Claude Code 2.1.265 inside the task container. Dockerfile and CLI installation require network access; an installation failure is an infrastructure failure.

## Prepare a task

Choose free physical cores using the host topology and effective affinity. Do not count two SMT siblings as two allocated cores. Main and public judges run concurrently, so their CPU sets must be disjoint and their memory requirements are additive. Private judging is separate and can reuse the main CPU set.

For HPCG, four main plus four public cores are required. The CPU numbers below are examples, not reservations:

```sh
.venv-native/bin/python public-release/native_run.py prepare \
  --task ./canonical/tasks/hpcg-multigrid-pcg \
  --work-dir ./runs/hpcg-attempt-1 \
  --model 'anthropic/EXACT_MODEL_ID' \
  --main-cpus 0-3 --public-cpus 4-7 --verifier-cpus 0-3
.venv-native/bin/python public-release/native_run.py print-config \
  --work-dir ./runs/hpcg-attempt-1
```

Use the exact model identifier accepted by your Claude Code/Anthropic-compatible provider. This entry point is not a generic OpenAI-protocol adapter. Omit `--public-cpus` for tasks without a public judge. Roles requiring eight CPUs need eight physical cores. HPCG main/public memory is 6 + 6 GiB; QiboTN is 32 + 32 GiB, plus host/build overhead. Each task retains its original private resources and timeout, including QiboTN's 50,000-second private timeout.

Preparation verifies the original task files, copies them to a fresh run workspace, and applies only the separately recorded CPU placement. It preserves task instructions, build inputs, correctness/scoring logic, memory limits and private network settings. Regenerate prepared configurations when moving to a different host.

## Run explicitly

Set `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` through your host environment or secret manager. Set `ANTHROPIC_BASE_URL` for a compatible non-default endpoint. Never put credentials in a repository, task file, saved configuration or shared shell history.

```sh
.venv-native/bin/python public-release/native_run.py run \
  --work-dir ./runs/hpcg-attempt-1
```

The runner uses one task, one attempt, concurrency one, high reasoning effort and no automatic job retries. It checks the prepared files, local Linux Docker/Compose and CPU topology, then creates a permanent attempt intent before invoking Harbor. Preserve interrupted workspaces and reconcile them instead of reusing a completed or uncertain attempt.

Keep the complete run directory and audit the candidate, correctness gates, raw timings and environment as described in [REPRODUCIBILITY.md](../REPRODUCIBILITY.md). Configuration generation is not a capacity reservation or proof of a valid result.

## Validation scope

The pinned public installer and Harbor configuration interface have been exercised on fresh Linux environments. The unchanged HPCG main/public/private images and pinned Claude Code installer have also been built on a managed Linux host. Those checks establish installation and HPCG image compatibility on that host; independent-host resource enforcement, all 32 image builds and complete model-to-judge runs need qualification on the deployment used for your results.

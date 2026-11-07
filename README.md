# AccelerateBench

**Code optimization for real scientific computing workloads.** AccelerateBench contains 32 tasks with source code, reference implementations, public feedback and separate private correctness/performance evaluation. Each task retains its original CPU, memory and time budget; the model budget is eight hours.

[Project website](https://acceleratebench.com) · [Dataset and access request](https://huggingface.co/datasets/AdAstraAbyssoque/accelerate-bench) · [Citation](CITATION.cff)

This repository provides the native Docker runner, source verification tools and a separate Nexus Cloud configuration layer. Task assets are distributed through Hugging Face. The canonical task source version is `20261010-v5-timing3`.

## Get the tasks

Use Python 3.12 or later. Request access on the dataset page, provide your institution and evaluation purpose, and wait for approval. Normal model evaluation, reproduction, auditing and teaching are supported. The access form explains the commitments for controlled evaluation assets and their relationship to the existing component licenses.

```sh
python3 -m venv .venv-tools
. .venv-tools/bin/activate
python -m pip install -r requirements-download.txt -r requirements-tools.txt
hf auth login
python scripts/download_data.py
```

The downloader uses your normal Hugging Face login or `HF_TOKEN`. It never embeds a credential in a configuration file. It checks the release archive's exact size/SHA-256 and every canonical file's bytes, mode and path before installing `canonical/tasks/`. Existing task directories are preserved, including directories created concurrently. If a filesystem error interrupts installation, the partial tree is retained for inspection; the command reports failure. Allow space for the approximately 2.29 GB cached archive and the extracted tasks.

To verify a local archive without downloading or installing:

```sh
python scripts/download_data.py --archive /absolute/path/to/release.tar.gz --verify-only
```

Two ICON grid files are obtained separately from their original official source:

```sh
python public-release/fetch_external_data.py --only icon-grid-0013 \
  --cache ./asset-cache --hydrate ./canonical/tasks
python public-release/verify_source.py --source ./canonical/tasks
```

## Run on native Linux

Execution requires Linux x86-64, a local Docker Engine with Compose v2, and sufficient free physical cores and memory for all concurrently active roles. The pinned runner uses Harbor 0.22.0 and Claude Code 2.1.265 with an Anthropic-compatible connection.

See [native installation and execution](public-release/INSTALL-NATIVE.md) for credentials, CPU placement, model selection and retained results. Preparation is separate from execution. A concrete HPCG example is:

```sh
PYTHON_BIN=python3.12 bash public-release/install-native.sh .venv-native
.venv-native/bin/python public-release/native_run.py prepare \
  --task ./canonical/tasks/hpcg-multigrid-pcg \
  --work-dir ./runs/hpcg-attempt-1 --model 'anthropic/EXACT_MODEL_ID' \
  --main-cpus 0-3 --public-cpus 4-7 --verifier-cpus 0-3
```

The CPU numbers are examples; select available physical cores on your host. Main and public judges run together and need disjoint CPU sets. The separate private judge can reuse the main set. After reviewing the generated configuration, use the explicit `run` command documented in the native guide.

For MHM2, an optional [SAM-adapter source supplement](overlays/mhm2-reference-sam-adapter-v1/README.md) corrects read/contig coordinate serialization. Select it explicitly as `mhm2-reference-sam-adapter-v1` and record the new source and image identities. Its generator validates the original task and creates a separate directory; it preserves the canonical release and historical attempts. The shared role-image build entry remains a template requiring the operator's exact base-image bindings. Results from this source cohort must retain that identity when reported.

## Nexus Cloud configuration

The canonical source is shared between backends. `profiles/nexus/` defines outer sandbox budgets and role image references; `adapters/nexus/` renders SDK input templates. Main and public evaluation share the outer Cloud budget. This is a distinct experimental environment from native per-container resource isolation.

The following commands only prepare local inputs:

```sh
python tools/generate.py --task datalife-io-monitoring --model example-model \
  --protocol anthropic_messages --output generated/datalife
python tools/capacity_plan.py --plans generated/datalife/plan.json \
  --snapshot profiles/nexus/capacity-example.json
python tools/claim_intent.py --plans generated/datalife/plan.json
```

The generated template needs your Nexus SDK/deployment environment, exact role images, provider settings and current capacity. See the [adapter contract](adapters/nexus/README.md). The example capacity file is illustrative. These tools do not submit batches or certify all 32 tasks for a new Cloud environment. Preserve model/task/source/environment identities when scheduling and reporting results.

## Results and contamination checks

[Reproducibility guidance](REPRODUCIBILITY.md) describes the evidence needed to report a result. Keep infrastructure/API failures separate from valid scores, retain original attempts and report native and Cloud environments separately.

The release has one release-level and 32 task-level contamination markers. See [CONTAMINATION_NOTICE.md](CONTAMINATION_NOTICE.md). Scan explicitly selected local corpus files with:

```sh
python tools/scan_canaries.py --manifest canaries.json /path/to/corpus.jsonl
```

Markers support contamination detection; they do not prevent copying. A hit shows text presence, not proof of training or cheating, and absence is not proof of no leakage. Markers are additional release files and do not modify the frozen task instructions, judges or scoring.

## Development checks

The release-tooling CI checks archive validation, installation behavior, the 33 distributed canary markers and the optional source supplement's file bindings on Python 3.12 and 3.13. It runs without dataset access or model credentials. Run the downloader checks locally with:

```sh
python -m unittest discover -s tests -p test_download_data.py -v
```

After downloading and hydrating the task assets, the configuration-tool tests can also run with `python -m unittest discover -s tests -p test_tools.py -v`. These tooling checks do not run the benchmark or validate model scores.

## Licenses and contact

Author-owned project code and tools use [Apache-2.0](LICENSE). Task components retain their upstream terms; see [component licensing](public-release/LICENSING.md) and [third-party resolutions](public-release/THIRD-PARTY-RESOLUTIONS.json). Download access commitments do not replace those licenses. The paper uses CC BY 4.0.

Contact: Bowen Liu — [bliu690@connect.hkust-gz.edu.cn](mailto:bliu690@connect.hkust-gz.edu.cn); corresponding author Nuo Chen — [chennuo26@gmail.com](mailto:chennuo26@gmail.com).

## 中文

AccelerateBench 提供 32 道真实科学计算代码优化任务。GitHub 维护运行工具和独立的 Nexus 配置，题目资产通过 Hugging Face 申请下载。下载器核验发布包及逐文件完整性后恢复 `canonical/tasks/`；ICON 的两项网格文件需从原官方来源补齐。正常模型评测、复现、审计和教学均可申请。

原生 Linux 和 Nexus Cloud 的资源边界不同，结果应分别报告。Canary 用于检查文本污染，不保证阻止泄露，也不改变已有评测题目。使用前请阅读各组件原有许可、下载申请及复现说明。

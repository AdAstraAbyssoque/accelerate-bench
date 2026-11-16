# Release layout and integrity

The code repository contains the downloader, the native Harbor runner and its profile, provenance records and the frozen canonical manifest. The controlled task assets are delivered as Harbor task packages by the [Hugging Face dataset](https://huggingface.co/datasets/AdAstraAbyssoque/accelerate-bench). The exact archive name, size and SHA-256 are pinned in [data-release.json](../data-release.json).

The archive contains benchmark v1.1, the version evaluated in the paper. It starts from task source `20261010-v5-timing3`; for four tasks, the files that changed for v1.1 are taken from the task packages used in the v1.1 runs:

- `mhm2-metagenome-assembly`: task version 1.1.1, with a revised statement, revised correctness checks and the updated reference source archive;
- `fluidity-heat-checkpoint`: the output parser accepts all valid VTK appended encodings, and the Ubuntu packages the task depends on are bundled in `.fluidity-ppa/` instead of being installed from the online PPA;
- `su2-transonic-euler`: verifier time limit 14,000 s instead of 3,600 s, with command timeouts reported as evaluation errors;
- `io500-file-io`: the system-call trace parser accepts restarted `wait4` records, and strace runs with `--seccomp-bpf`.

The HF archive includes 32 task packages with 3,772 embedded canonical files. Besides the task packages and `canonical/manifest.json`, it contains only release notices: a README, licenses and third-party notices, citation metadata and the contamination markers. Two ICON grid destinations are hydrated from the original official source and checked against their frozen hashes, giving the complete 3,774-file task tree. Instructions, reference software, private judges, fixtures and scoring remain part of that tree. A judge's private execution role is distinct from whether its source is distributed.

The downloader verifies the whole archive, the embedded canonical manifest, every included task file's content/size/mode and the complete directory inventory. It rejects links, special members, traversal, duplicate entries, missing or unexpected canonical files, and drift in hashes or modes. It verifies through a temporary directory, exclusively creates the destination and links verified regular files without replacing destination entries. Existing `canonical/tasks/` directories are preserved, including concurrent creation. A filesystem error during installation leaves the partial destination for inspection and reports failure. Its `--verify-only` option performs full verification without installing.

Canary markers are an additional release layer outside canonical task paths. Their presence does not alter task checksums, prompts, correctness gates or scores. [CONTAMINATION_NOTICE.md](../CONTAMINATION_NOTICE.md) describes their purpose and limits.

## Component terms

The repository's Apache-2.0 license applies to author-owned project code and tools. Original third-party notices remain in task sources and archives. [THIRD-PARTY-RESOLUTIONS.json](THIRD-PARTY-RESOLUTIONS.json) supplements the initial filename-based inventory; an `unknown` inventory label is a classification gap, not a replacement license or a finding that use is forbidden.

- ABySS retains its original GPL-derived, non-commercial terms and complete notices. It is not relicensed as Apache-2.0; nested dependencies retain their own terms.
- ICON retains its BSD-3-Clause code notice, REUSE assignments and mixed component license texts. The separate grid is obtained from its official source rather than inferring a data redistribution license from the code license.
- FINUFFT, xsimd and xtl retain their separately rooted vendor notices. Benchmark integration and preprocessing wrappers are distinguished from those vendor trees in the provenance inventory.
- HPL acknowledgements, other mixed/copyleft notices and SmolLM2 model cards/notices remain with their components.
- The Ubuntu packages bundled with Fluidity keep their Debian copyright files. Fluidity, Zoltan, Spud and supermesh are LGPL or GPL licensed; the corresponding source packages are published in the dataset as `third-party-sources/fluidity-ppa-sources.tar`.

[DATA-PROVENANCE.md](DATA-PROVENANCE.md) records the official data sources, attribution and exact payload hashes. Access-use commitments on HF do not replace the existing component licenses. Downloaded archive bytes and notices should be retained together when redistributing material under the applicable terms.

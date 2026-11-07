# Release layout and integrity

The code repository contains execution tools, separate native/Nexus profiles, provenance records and the frozen canonical manifest. The controlled task assets are delivered by the [Hugging Face dataset](https://huggingface.co/datasets/AdAstraAbyssoque/accelerate-bench). The exact archive name, size and SHA-256 are pinned in [data-release.json](../data-release.json).

The HF archive includes 32 task packages with 3,704 embedded canonical files. Two ICON grid destinations are hydrated from the original official source and checked against their frozen hashes, giving the complete 3,706-file task tree. Instructions, reference software, private judges, fixtures and scoring remain part of that tree. A judge's private execution role is distinct from whether its source is distributed.

The downloader verifies the whole archive, the embedded canonical manifest, every included task file's content/size/mode and the complete directory inventory. It rejects links, special members, traversal, duplicate entries, missing or unexpected canonical files, and drift in hashes or modes. It verifies through a temporary directory, exclusively creates the destination and links verified regular files without replacing destination entries. Existing `canonical/tasks/` directories are preserved, including concurrent creation. A filesystem error during installation leaves the partial destination for inspection and reports failure. Its `--verify-only` option performs full verification without installing.

Canary markers are an additional release layer outside canonical task paths. Their presence does not alter task checksums, prompts, correctness gates or scores. [CONTAMINATION_NOTICE.md](../CONTAMINATION_NOTICE.md) describes their purpose and limits.

## Component terms

The repository's Apache-2.0 license applies to author-owned project code and tools. Original third-party notices remain in task sources and archives. [THIRD-PARTY-RESOLUTIONS.json](THIRD-PARTY-RESOLUTIONS.json) supplements the initial filename-based inventory; an `unknown` inventory label is a classification gap, not a replacement license or a finding that use is forbidden.

- ABySS retains its original GPL-derived, non-commercial terms and complete notices. It is not relicensed as Apache-2.0; nested dependencies retain their own terms.
- ICON retains its BSD-3-Clause code notice, REUSE assignments and mixed component license texts. The separate grid is obtained from its official source rather than inferring a data redistribution license from the code license.
- FINUFFT, xsimd and xtl retain their separately rooted vendor notices. Benchmark integration and preprocessing wrappers are distinguished from those vendor trees in the provenance inventory.
- HPL acknowledgements, other mixed/copyleft notices and SmolLM2 model cards/notices remain with their components.

[DATA-PROVENANCE.md](DATA-PROVENANCE.md) records the official data sources, attribution and exact payload hashes. Access-use commitments on HF do not replace the existing component licenses. Downloaded archive bytes and notices should be retained together when redistributing material under the applicable terms.

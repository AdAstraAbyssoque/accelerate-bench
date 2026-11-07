# Optional MHM2 SAM-adapter source cohort

This staging draft supplies the explicit `mhm2-reference-sam-adapter-v1` cohort for AccelerateBench's MHM2 task. It corrects serialization between SSW's contig-query alignment and SAM's read-query representation: insertion/deletion directions and clipping are constructed using the matching read/contig coordinates. It does not change alignment scoring, the correctness parser, recipes, timing formula, or budgets.

The supplement contains two source files, their unified patch, source manifests, and a local generator. It contains no model outputs or scores. The corrected initial candidate, public reference and private reference must all use the same source revision. This is a new protocol cohort, not a silent correction to historical results. A new evaluation must record the cohort, task/source hashes, actual three image IDs, model, environment and unique attempt identity. Existing model candidates and scores are immutable; no best-score selection or automatic retry is provided.

## Local generation

Python 3.11+ and the unmodified, complete released `mhm2-metagenome-assembly` task directory are required. Download/authorize the original data separately using the release's normal mechanism. This package does not download or execute anything.

```sh
# Default: validate exact canonical files and reproduce the corrected archive in memory.
python3 -B generate.py --cohort mhm2-reference-sam-adapter-v1 \
  --task-root /path/to/released/mhm2-metagenome-assembly

# Explicitly create a NEW directory. Never point at a live task or existing checkout.
python3 -B generate.py --cohort mhm2-reference-sam-adapter-v1 \
  --task-root /path/to/released/mhm2-metagenome-assembly \
  --materialize --output /path/to/new-mhm2-cohort

python3 -B generate.py --cohort mhm2-reference-sam-adapter-v1 \
  --validate-generated /path/to/new-mhm2-cohort
```

Generation changes only the three existing source-archive placements. All other 51 canonical files remain byte-identical, including `task.toml`, instruction, judge, hidden/private recipe logic and score calculation. The generated task is a disposable assembly from canonical plus this overlay; it is not a second independently maintained task. One corrected archive is stored in `image-context/`; the three task placements are hard links to that same file. Filesystem errors leave a visible partial directory, which must be reconciled rather than silently overwritten.

The original archive SHA-256 is `75f49c46a6e32c774feb401be9e58703ef65fed19265e5fb8db549d64f66476e`. The corrected archive is 1,027,475 bytes with SHA-256 `4b00b84d1730c4cb0612ef6211385a9121125f0c2565f38cd0daf704b5bab530`. Deterministic tar/gzip encoding preserves original member metadata; only `include/klign.hpp` changes and `include/reference_sam_adapter.hpp` is added. Its 240 regular-file hashes are in `source-files.json`.

## Role-specific image rebuild draft

`images/cohort-rebuild.py` is the exact previously validated image-local rebuild program. The shared Dockerfile merely parameterizes the original role base image and `main`, `public`, or `private` argument. This parameterized build entry is a draft; no new image build is performed by this supplement. Base images are deliberately unset in `cohort.json`: the operator must identify the original task's correct role bases and resolve immutable local image IDs. Never substitute a generic distribution image or the same base for every role.

Illustrative commands after independent review and resource admission:

```sh
# Supply locally verified immutable role image references; no registry address is assumed.
: "${MHM2_MAIN_BASE_IMAGE:?}" "${MHM2_PUBLIC_BASE_IMAGE:?}" "${MHM2_PRIVATE_BASE_IMAGE:?}"
: "${MHM2_BUILD_CPUSET:?}" "${MHM2_BUILD_CGROUP:?}"
export DOCKER_BUILDKIT=0
for role in main public private; do
  case "$role" in
    main) base="$MHM2_MAIN_BASE_IMAGE" ;;
    public) base="$MHM2_PUBLIC_BASE_IMAGE" ;;
    private) base="$MHM2_PRIVATE_BASE_IMAGE" ;;
  esac
  # Run each command with the original 3600-second whole-build deadline.
  docker build --network=none --cpu-period=100000 --cpu-quota=400000 \
    --cpuset-cpus="$MHM2_BUILD_CPUSET" --memory=6144m --memory-swap=6144m \
    --cgroup-parent="$MHM2_BUILD_CGROUP" \
    --build-arg BASE_IMAGE="$base" --build-arg ROLE="$role" \
    -t "acceleratebench-mhm2-sam-v1-${role}" /path/to/new-mhm2-cohort/image-context
 done
```

The scheduler/operator must impose and verify resource isolation and the external deadline; these example commands do not create a cgroup, reserve capacity, enforce the whole-build deadline or activate a task. Image-local compilation retains its original 2400-second bound, four jobs, and original UPC++ settings. Record each `/opt/accelerate-mhm2-adapter-cohort.json`, resolved image ID and source digest. Distinct role binaries need not be bit-identical.

Preserve 4 CPU/6144 MiB per main/public/private environment, 28,800-second agent budget, 9000-second private verifier budget, original networks and public HTTP endpoint/protocol. Do not reduce cases/repetitions or widen correctness thresholds. This package has no scheduler, authorization, intent or submission command. Dispatch remains the evaluation owner's responsibility with fresh capacity and exact attempt deduplication; the same local package cannot establish global exclusion on its own.

## Validation and scope

The repaired source has already passed an original-image reference build, 96 actual SSW fixtures, the full original private workflow, three role builds, and an actual public HTTP submission with both public recipes, two repetitions per role and eight legacy cases repeated twice. The public response retains complete correctness summaries and timing samples; it does not expose the original temporary FASTA/GFA/SAM/depth arrays. This supplement neither repeats those scientific runs nor claims newly generated image IDs have been tested.

A historical failed SAM was not retained, so the diagnosed adapter defect is not proof of the unique cause of every earlier failure. Historical candidates and unmodified canonical cohorts remain available. Final integration into a maintained release and owner-specific image bindings are pending; this draft does not alter them.

## Licenses

AccelerateBench-owned tooling remains under the supplied Apache-2.0 license. The MHM2-derived source and patched `klign.hpp` retain their original copyright and component-specific license terms. The patch does not relicense MHM2 or its bundled dependencies. Original source license files remain byte-identical in the generated archive; copies are provided under `third-party-notices/`. Apply the original release's notices and conditions as well. See `THIRD_PARTY_NOTICES.md` for exact copied-file hashes.

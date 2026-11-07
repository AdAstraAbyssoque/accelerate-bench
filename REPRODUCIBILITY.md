# Reproducing and reporting an evaluation

Record the exact model wire identifier and provider, source version and file hashes, runner/agent versions, environment profile, built image identifiers and hardware. A display name alone does not establish a model version. Keep provider credentials outside saved configurations and public artifacts.

Before running, validate the task's reference implementation and confirm the effective CPU placement and memory limits of each role. Main and public judges may coexist; reserve their combined requirements plus build/host overhead. Preserve the original per-task private-verifier timeout and the eight-hour model budget. A retry label does not start a fresh scientific budget for an existing attempt.

Retain the complete original attempt: input configuration, model/tool trace, public submissions, final candidate, private judge logs, raw case results and timings, resource observations, and cleanup evidence. Record a digest for the final candidate and show that the private judge evaluated those bytes. Preserve original archives before any repair.

A successful agent exit or a claimed speedup is not a score. Check the judge's actual correctness gates and timing scope, then recompute its original aggregation formula from raw measurements. A valid zero must be supported by execution of the intended candidate and the relevant correctness/performance gates. A missing verifier, failed reference build, API error or broken infrastructure remains an infrastructure failure with a missing accepted score.

Report native Linux and Nexus Cloud separately: the native runner preserves per-service resource settings, while Nexus profiles use outer sandbox budgets with shared main/public resources. Do not combine their timings as if they were the same hardware or isolation regime. A runtime compatibility change requires a versioned profile and new reference/candidate qualification; it must not silently replace the old cohort.

Preserve all attempts and declare any selection rule before aggregate reporting. Do not retry valid low scores to select the best result. Infrastructure recovery should reuse the verified original candidate when model work has already completed, retain the failure record, and identify the new verifier environment. Review logs for credentials and third-party or personal information before publishing them.

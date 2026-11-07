# Nexus integration boundary

`tools/generate.py` emits a source-bound deployment descriptor and an actual-field Nexus RunInput template; it does not fabricate a new submission API. This repository does not vendor Nexus or implement a new submission API. A deployment's existing reviewed launcher must translate the descriptor using its installed official SDK, pin that SDK/source/worker wheel, resolve role images and provider environment **in memory**, verify the full RunInput/TrialConfig, acquire fresh complete capacity, and claim the local intent before its one actual submission.

Known owning API in the qualified deployment is `nexus.extensions.harbor_trial.task.HarborTrialTaskInput`: `agent_timeout`, `verifier_timeout`, `timeout_multiplier`, `outer_resources`, `shared_cpu_budget`; image/provider/TaskFiles and retention need their actual SDK configurations too. These field names do not prove a public wheel contains the deployment's fixes. The backend must pass its own source/worker/package qualification; this repository makes no direct-submit or public SDK reproducibility claim.

Do not silently switch Anthropic Messages to OpenAI Chat, omit high effort, reassign a model route, resize task limits, or replace the private evaluator. `protocol` and wire model are explicit identities. Credentials and endpoint values belong only in the deployment environment, never generated source/profile/plan files.

A backend compatibility library, reference fix or changed scientific source is a distinct versioned cohort requiring complete reference/candidate acceptance. Original results, valid zeros, infrastructure/null and timeout outcomes remain separate. Fresh infrastructure attempts are not Harbor resume and do not reset a running task's eight-hour budget.

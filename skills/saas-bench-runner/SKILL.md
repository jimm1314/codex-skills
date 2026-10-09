---
name: saas-bench-runner
description: Safely preflight, launch, monitor, resume, summarize, and compare SaaS-Bench evaluations in native SaaS-Bench or Harbor adapter mode. Use when Codex is asked to run selected SaaS-Bench tasks, watch long-running evaluations with low-noise polling, print copyable Bash commands for inspecting logs, diagnose run state without modifying tasks, or compare existing native and Harbor results for integration parity.
---

# SaaS-Bench Runner

Run and observe SaaS-Bench evaluations without changing benchmark tasks or silently changing evaluation semantics. Treat every real launch as a costly external action and every comparison as an evidence exercise.

## Select the operation

- Use `preflight` for inspection only. Do not launch anything.
- Use `harbor` to run through the Harbor SaaS-Bench adapter.
- Use `native` to run the upstream SaaS-Bench controller directly.
- Use `parity compare` to compare two completed run directories without rerunning.
- Use `parity run` to orchestrate one native run and one Harbor run serially, then compare them. It is not a third evaluation engine.
- Use `resume` to monitor an existing run directory. Never start a replacement run implicitly.

If the request is vague, default to `preflight`. Require explicit user confirmation after showing the exact launch command whenever the operation creates VMs, calls models, retries trials, stops processes, or deletes remote resources.

## Enforce the safety contract

Read [references/safety-contract.md](references/safety-contract.md) before any launch, retry, stop, cleanup, or parity-run operation. Apply these rules even if an existing project script is more permissive:

- Never edit, regenerate, overwrite, patch, or normalize upstream or generated task content during a run workflow.
- Never use `--overwrite` in this Skill.
- Default to concurrency `1`, no automatic trial retry, and upstream-exact verifier behavior.
- Treat Judge remapping as a separately named experimental evaluator version. Never label it upstream-exact.
- Never print secret values or read an entire env file into the conversation. Check variable names only.
- Never automatically kill a process, delete a VM, or clean a result directory.
- Preserve raw results. Add interpretations; do not rewrite source result files.
- Do not run native and Harbor evaluations concurrently during parity work.

## Locate repositories and helpers

Resolve the Harbor and SaaS-Bench repositories from the user-provided paths or current workspace. Verify candidates from real files instead of assuming a fixed checkout layout.

Set the helper path from this Skill directory:

```bash
SKILL_ROOT="<absolute path containing this SKILL.md>"
```

The helpers use only the Python standard library and are read-only:

- `scripts/preflight.py`: validate repositories, task IDs, task hashes, credential-name presence, and active Harbor jobs.
- `scripts/monitor.py`: inspect once or poll with state-change suppression.
- `scripts/run_card.py`: print copyable post-launch Bash commands using the actual result directory.
- `scripts/summarize.py`: summarize a Harbor or native run without loading full traces.
- `scripts/compare.py`: compare existing native and Harbor artifacts.

## Preflight every launch

Run preflight before constructing a launch command:

```bash
python "$SKILL_ROOT/scripts/preflight.py" \
  --mode harbor \
  --harbor-repo <harbor-repo> \
  --saas-bench-repo <saas-bench-repo> \
  --task agriculture_003 \
  --judge-mode upstream-exact
```

For native mode, use `--mode native`; for a matched pair, use `--mode parity`. Add `--env-file <path>` only to check which variable names are declared. The helper never prints their values.

Stop before launch when:

- any requested task ID is unsafe or absent;
- upstream task files have Git changes;
- Harbor mode has a missing or byte-different generated instruction/verifier;
- an upstream-exact request contains an effective Judge remap;
- another active run would violate the agreed global concurrency;
- required credentials are absent from both the process environment and declared env-file keys.

Warnings about incomplete historical provenance do not authorize silent assumptions. Show them to the user.

## Build launch commands from current project evidence

Read the current repository README, CLI help, and selected config before composing a command. Do not copy a stale command from this Skill. Show a compact launch plan containing:

- mode and repository;
- exact task IDs and attempts;
- model and sampling parameters;
- max steps, failure limit, retry policy, and concurrency;
- Session Router endpoint name without token;
- verifier mode and Judge model policy;
- expected output root;
- the exact shell command.

Wait for confirmation after showing this plan. A prior request to create or inspect the Skill is not approval to start an evaluation.

For `parity run`, freeze one shared parameter table, run native first, wait for its terminal state, then run Harbor. If either side fails infrastructure validation, stop and report; do not compensate with an unapproved rerun.

## Monitor with bounded output

After launch, identify the actual result directory from command output or new filesystem state. Never guess it from a requested job name alone.

Inspect once:

```bash
python "$SKILL_ROOT/scripts/monitor.py" --mode auto --run-dir <run-dir> --once
```

Poll locally with low-noise output:

```bash
python "$SKILL_ROOT/scripts/monitor.py" --mode auto --run-dir <run-dir> \
  --follow --interval 30 --heartbeat 600 --step-delta 10
```

The poller prints immediately, then only after a meaningful status/error change, a configured step bucket change, or a heartbeat. When Codex owns the polling process, keep it in one persistent exec session and poll that session without repeatedly rereading full logs. Communicate a concise user update at least once per minute while actively working.

Use `--errors` to display only bounded, redacted error summaries. Do not send full traces or complete agent result JSON to the model unless a specific failure requires it.

## Always print the post-launch operation card

Immediately after obtaining the real run directory, run:

```bash
python "$SKILL_ROOT/scripts/run_card.py" --mode <harbor-or-native> --run-dir <run-dir>
```

Show its output to the user even when Codex is also monitoring. It must include:

- one-shot status and low-noise follow commands;
- existing main/error log tail commands;
- trial-log discovery commands when applicable;
- final summary command;
- a `$saas-bench-runner` resume prompt containing the absolute run directory.

Do not add kill, VM deletion, result deletion, env dumping, or credential-printing commands to the card.

## Summarize and compare

At terminal state, run:

```bash
python "$SKILL_ROOT/scripts/summarize.py" --mode auto --run-dir <run-dir>
```

For an existing matched pair, run:

```bash
python "$SKILL_ROOT/scripts/compare.py" \
  --native-run <native-run-dir> \
  --harbor-run <harbor-job-dir>
```

Report separately:

- execution compatibility: task set, model, max steps, attempts, statuses, check labels/weights, and scores;
- strict provenance: whether run-time task/verifier hashes, commits, Judge identity, and environment versions were actually recorded;
- stochastic outcome differences, which are not automatically integration defects;
- infrastructure errors, which are not model failures.

Never claim strict parity when provenance is missing. `compare.py` deliberately reports `NOT_PROVEN` when artifacts cannot prove exact run-time identity.

## Use evidence labels

Label conclusions as `已实际验证`, `仅静态检查`, `合理推断`, `尚未验证`, or `需要人工确认`. End with the shortest safe next action. Do not expand this Codex Skill into StepCode or Claude global locations until the user has tested this version and explicitly requests that separate installation.

# SaaS-Bench Runner Safety Contract

Read this file before any operation that launches, retries, stops, or cleans up an evaluation.

## Authorization boundaries

- Inspection, monitoring, summarization, and comparison are read-only.
- A real native or Harbor launch creates remote sessions and model traffic. Show the exact command and obtain explicit confirmation immediately before launch.
- A request to create, install, inspect, or test this Skill does not authorize an evaluation run.
- Retry, process termination, VM deletion, and result cleanup each require separate explicit authorization.

## Evaluation-integrity red lines

1. Do not modify anything under upstream `tasks/`.
2. Do not regenerate or overwrite generated Harbor tasks as part of running or monitoring.
3. In upstream-exact mode, send the on-disk verifier bytes unchanged. Any in-memory rewrite is a semantic modification.
4. Keep Judge-remap results under an explicit experimental label and separate output directory. Do not merge them into upstream-exact aggregates.
5. Preserve raw Agent and verifier outputs. Add derived validity/status fields only in a separate report.
6. Do not turn Judge, browser, VM, app, SQL, transport, or verifier infrastructure failures into unqualified model scores.
7. Do not claim parity from reward equality alone. Compare task/check contracts and record missing provenance.

## Safe defaults

- Global concurrency: `1` until capacity is explicitly validated.
- Trial attempts: user-specified; default `1`.
- Automatic trial retries: disabled.
- Judge mode: `upstream-exact`.
- Monitoring: 30-second filesystem poll, output every 10 steps or 10-minute heartbeat.
- Native and Harbor parity runs: serial, never overlapping.

Infrastructure retries that happen before Agent work may be proposed separately, but do not silently change repository configuration or the requested run contract.

## Secrets

- Check only whether credential variable names are present.
- Never print values from `.env`, process environments, config substitutions, request headers, cookies, or tokens.
- Never place secret-bearing shell commands in the post-launch operation card.
- Redact likely secret assignments in bounded error summaries.

## Stop conditions

Stop before launch and report when:

- a requested task path escapes its category directory;
- source tasks have Git changes;
- generated instruction/verifier bytes differ from upstream in Harbor or parity mode;
- selected configs contradict the declared Judge mode;
- active work would exceed the confirmed global concurrency;
- required repositories, task files, or credential names are missing.

During a run, report and wait for direction instead of auto-retrying when:

- the Judge/API schema fails;
- the browser or environment dies after Agent work began;
- task/verifier provenance changes;
- the run stalls beyond the agreed threshold;
- cancellation or cleanup would discard live state.

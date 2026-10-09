---
name: stepcode-fb
description: "Export current step-code session and print the feedback session ID"
---
<!-- stepcode-injected -->
Run the following shell command and print its stdout verbatim, with no extra
commentary, summary, reformatting, or invented URLs:

stepcode session fb "${STEPCODE_SESSION_ID:-${CODEX_SESSION_ID:-}}" --format plain

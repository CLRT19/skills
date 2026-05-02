---
name: claude-to-codex-history
description: Convert Claude Code session history into Codex-ready continuation artifacts. Use when a user asks to migrate, transfer, resume, import, archive, inspect, or continue Claude Code conversations/history in Codex, including by Claude session id, renamed session title, ~/.claude JSONL file, project directory, or search query.
---

# Claude To Codex History

Convert Claude Code JSONL sessions into artifacts Codex can use, including an optional installed Codex resume entry.

## Default Workflow

1. If the user wants `codex resume`, use **Same-Directory Resume Workflow**.
2. If the user only wants a portable artifact, export Markdown with `--include-predecessors -o <handoff.md>`.
3. If the user asks for raw machine-readable data, export `messages-jsonl`.
4. Only export standalone `codex-jsonl` when explicitly requested; it is archival unless installed into Codex.

## Target Human Workflow

Support this end-to-end flow:

1. User works in Claude Code inside a project directory.
2. User exits Claude Code and keeps either the Claude session ID or renamed session title.
3. User starts Codex from that same project directory.
4. User asks Codex to use this skill on the Claude session name or ID.
5. Codex converts the Claude session and installs a synthetic Codex resume session.
6. Codex reports the exact `codex resume <session-id>` command, thread name, and full handoff path.
7. User exits the current Codex chat.
8. User runs `codex resume`, selects the imported thread, or runs the exact command.

## Same-Directory Resume Workflow

Use this when the user says they exited Claude Code in a directory, started Codex in that same directory, and wants to convert a Claude session name or ID so they can later use `codex resume`.

Always run from the project directory. Preview candidates first:

```bash
SESSION_NAME_OR_ID="put-session-name-or-id-here"
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" --same-directory --list
```

If the match is clear, dry-run the install:

```bash
SESSION_NAME_OR_ID="put-session-name-or-id-here"
SHORT_NAME="put-short-readable-name-here"
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" \
  --same-directory \
  --include-predecessors \
  --tool-output-chars 4000 \
  --install-codex-session \
  --thread-name "Imported Claude: $SHORT_NAME" \
  --dry-run
```

Then install the resumable Codex session:

```bash
SESSION_NAME_OR_ID="put-session-name-or-id-here"
SHORT_NAME="put-short-readable-name-here"
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" \
  --same-directory \
  --include-predecessors \
  --tool-output-chars 4000 \
  --install-codex-session \
  --thread-name "Imported Claude: $SHORT_NAME"
```

Report the printed command to the user:

```bash
codex resume <printed-session-id>
```

Also report the thread name and `full_handoff_path` so the user can find the imported session in the resume picker and inspect older Claude history when needed.

After this, the user can exit the current Codex chat, run `codex resume`, find the imported thread, or run the exact `codex resume <id>` command.

## What Installation Does

`--install-codex-session` writes a synthetic Codex session containing a bounded continuation context as the first user message. It also writes the full Markdown handoff to `~/.codex/claude_imports/`, appends a row to `~/.codex/session_index.jsonl`, and creates a timestamped backup of that index first. It does not modify Codex SQLite state.

This is intentionally a high-compatibility mimic: Codex sees a normal interactive-style session with compact imported context, rather than thousands of fake tool events. The bounded context matters because a multi-day Claude transcript can exceed Codex's model context window and fail on resume.

## Other Commands

List matching Claude sessions:

```bash
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" --list
```

Create a full handoff from a renamed session, following compact-summary transcript references:

```bash
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" --include-predecessors -o /tmp/claude-handoff.md
```

Create normalized machine-readable messages:

```bash
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" --include-predecessors --format messages-jsonl -o /tmp/claude.messages.jsonl
```

Create a best-effort Codex rollout JSONL:

```bash
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" --include-predecessors --format codex-jsonl -o /tmp/claude.codex.jsonl
```

Install a best-effort native Codex resume entry:

```bash
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" --same-directory --include-predecessors --install-codex-session --thread-name "Imported Claude: $SHORT_NAME"
codex resume <printed-session-id>
```

Preview the native install without writing:

```bash
python3 scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" --same-directory --include-predecessors --install-codex-session --dry-run
```

Continue in Codex using the stable handoff:

```bash
codex -C /path/to/workspace "$(cat /tmp/claude-handoff.md)"
```

## Format Choice

- Use `markdown` by default. It is stable, readable, and works as a Codex prompt or memory.
- Use `messages-jsonl` for downstream scripts or audits.
- Use `codex-jsonl` only for best-effort archival. Codex's internal rollout schema can change, so do not promise `codex resume` compatibility from this file alone.
- Use `--install-codex-session` only when the user explicitly wants `codex resume` integration. It writes a synthetic Codex-shaped session containing compact continuation context, writes the full handoff as a sidecar Markdown file, appends `~/.codex/session_index.jsonl`, and backs up the index first.
- Use `--install-full-context` only for small sessions or explicit debugging. Large full-history installs can fail with a Codex context-window error on resume.

## Safety Rules

- Do not write into `~/.codex/sessions`, `~/.codex/session_index.jsonl`, or Codex SQLite state unless the user explicitly asks for native session installation.
- When using `--install-codex-session`, prefer `--dry-run` first and verify the planned paths. Never modify Codex SQLite state.
- If testing a resume import, use `codex exec resume <session-id> "<small verification prompt>"` and check whether it can answer from the installed compact context.
- Preserve raw Claude source paths in the generated handoff so another agent can re-open the original transcript if needed.
- Use `--redact-secrets` before sharing handoffs outside the user's machine.
- Use `--full-tools` or `--entire` only when the user truly wants full tool output; otherwise large logs are truncated for readability.

## Script Notes

The converter accepts a Claude JSONL path, a project directory, a session UUID, or a search string. Search strings are matched against `~/.claude/history.jsonl` first, then against project JSONL contents.

`--entire` is shorthand for `--include-predecessors --full-tools`; it recursively follows transcript paths embedded in Claude compact summaries.

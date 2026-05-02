---
name: claude-to-codex-history
description: Convert Claude Code session history into Codex-ready continuation artifacts. Use when a user asks to migrate, transfer, resume, import, archive, inspect, or continue Claude Code conversations/history in Codex, including by Claude session id, renamed session title, ~/.claude JSONL file, project directory, or search query.
---

# Claude To Codex History

Convert Claude Code JSONL sessions into artifacts Codex can use without relying on fragile internal state mutation.

## Default Workflow

1. Locate the Claude session with `scripts/claude_to_codex_history.py <query> --list`.
2. Export a stable Markdown handoff with `--entire -o <handoff.md>` when the user wants full continuity across compacted sessions.
3. Start or continue Codex with the generated handoff as prompt/context.
4. Only generate native Codex rollout JSONL when explicitly requested; treat it as archival or experimental unless the user asks to install it into `~/.codex/sessions`.

## Commands

List matching Claude sessions:

```bash
python3 scripts/claude_to_codex_history.py della --list
python3 scripts/claude_to_codex_history.py 784518f9-b1d6-4769-8b65-78ef7c3ac968 --list
```

Create a full handoff from a renamed session, following compact-summary transcript references:

```bash
python3 scripts/claude_to_codex_history.py della --entire -o /tmp/della-handoff.md
```

Create normalized machine-readable messages:

```bash
python3 scripts/claude_to_codex_history.py della --entire --format messages-jsonl -o /tmp/della.messages.jsonl
```

Create a best-effort Codex rollout JSONL:

```bash
python3 scripts/claude_to_codex_history.py della --entire --format codex-jsonl -o /tmp/della.codex.jsonl
```

Install a best-effort native Codex resume entry:

```bash
python3 scripts/claude_to_codex_history.py della --entire --install-codex-session --thread-name "Imported Claude: della"
codex resume <printed-session-id>
```

Preview the native install without writing:

```bash
python3 scripts/claude_to_codex_history.py della --entire --install-codex-session --dry-run
```

Continue in Codex using the stable handoff:

```bash
codex -C /path/to/workspace "$(cat /tmp/della-handoff.md)"
```

## Format Choice

- Use `markdown` by default. It is stable, readable, and works as a Codex prompt or memory.
- Use `messages-jsonl` for downstream scripts or audits.
- Use `codex-jsonl` only for best-effort archival. Codex's internal rollout schema can change, so do not promise `codex resume` compatibility from this file alone.
- Use `--install-codex-session` only when the user explicitly wants `codex resume` integration. It writes a synthetic Codex-shaped session containing the Markdown handoff, appends `~/.codex/session_index.jsonl`, and backs up the index first.

## Safety Rules

- Do not write into `~/.codex/sessions`, `~/.codex/session_index.jsonl`, or Codex SQLite state unless the user explicitly asks for native session installation.
- When using `--install-codex-session`, prefer `--dry-run` first and verify the planned paths. Never modify Codex SQLite state.
- Preserve raw Claude source paths in the generated handoff so another agent can re-open the original transcript if needed.
- Use `--redact-secrets` before sharing handoffs outside the user's machine.
- Use `--full-tools` or `--entire` only when the user truly wants full tool output; otherwise large logs are truncated for readability.

## Script Notes

The converter accepts a Claude JSONL path, a project directory, a session UUID, or a search string. Search strings are matched against `~/.claude/history.jsonl` first, then against project JSONL contents.

`--entire` is shorthand for `--include-predecessors --full-tools`; it recursively follows transcript paths embedded in Claude compact summaries.

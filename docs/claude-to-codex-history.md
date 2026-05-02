# Claude to Codex History

Convert Claude Code session history into Codex continuation artifacts.

The main workflow installs a synthetic Codex session so the user can resume it
with `codex resume`. It is designed for the common handoff path where Claude
Code and Codex are both started from the same project directory.

The installed Codex session intentionally contains compact recent context, not
the entire raw transcript. The full Claude handoff is written to
`~/.codex/claude_imports/` and printed as `full_handoff_path`; Codex can inspect
that file when older details are needed.

## Origin workflow

This skill is built around one general workflow: keep Claude Code and Codex
anchored to the same project directory so the imported Codex session resumes in
the workspace where the Claude Code work happened.

1. The user works with Claude Code in a project directory.
2. The user exits the Claude Code chat and identifies the Claude session by session ID or session name.
3. The user starts Codex from that same project directory.
4. The user asks Codex to use this skill on the Claude session name or ID.
5. Codex converts the Claude history into a Codex-compatible continuation session.
6. Codex tells the user the imported thread name, full handoff path, and exact `codex resume <session-id>` command.
7. The user exits the current Codex chat.
8. The user runs `codex resume`, finds the imported session manually, or runs the exact resume command Codex printed.

## Same-directory resume flow

1. Work in Claude Code inside the project directory.
2. Exit Claude Code and keep either the Claude session ID or renamed session title.
3. Start Codex from the same directory.
4. Ask Codex to use this skill on the session name or ID.
5. Codex previews candidates with `--same-directory --list`.
6. Codex installs a Codex resume session with `--same-directory --install-codex-session`.
7. Codex reports the printed `codex resume <session-id>` command, thread name, and full handoff path.
8. User exits the current Codex chat and resumes the imported session.

## Commands

Preview candidates:

```bash
SESSION_NAME_OR_ID="put-session-name-or-id-here"
SHORT_NAME="put-short-readable-name-here"
python3 ~/.codex/skills/claude-to-codex-history/scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" \
  --same-directory \
  --list
```

Dry-run install:

```bash
python3 ~/.codex/skills/claude-to-codex-history/scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" \
  --same-directory \
  --include-predecessors \
  --tool-output-chars 4000 \
  --install-codex-session \
  --thread-name "Imported Claude: $SHORT_NAME" \
  --dry-run
```

Install:

```bash
python3 ~/.codex/skills/claude-to-codex-history/scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" \
  --same-directory \
  --include-predecessors \
  --tool-output-chars 4000 \
  --install-codex-session \
  --thread-name "Imported Claude: $SHORT_NAME"
```

Resume:

```bash
codex resume <printed-session-id>
```

Optional non-interactive verification:

```bash
codex exec resume <printed-session-id> "Briefly state what prior context was imported."
```

## Notes

- `--same-directory` restricts lookup to Claude sessions associated with the current working directory and embeds that same directory as the Codex resume cwd.
- `--include-predecessors` follows Claude compact-summary links only under `~/.claude/projects`, avoiding unrelated dataset JSONL files.
- `--tool-output-chars 4000` keeps the imported session readable while preserving useful tool context.
- `--entire` is available for Markdown exports, but it disables tool-output truncation and can create a very large handoff.
- `--install-codex-session` writes a compact replay context by default so `codex resume` does not exceed the model context window.
- `--install-full-context` embeds the entire handoff into the resume session and is only safe for small sessions or debugging.
- `full_handoff_path` is the durable full transcript location for search, audit, and older details.
- The installer backs up `~/.codex/session_index.jsonl` before appending a new resume entry.
- The installer does not modify Codex SQLite state.

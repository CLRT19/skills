# Claude to Codex History

Convert Claude Code session history into Codex continuation artifacts.

The main workflow installs a synthetic Codex session so the user can resume it
with `codex resume`. It is designed for the common handoff path where Claude
Code and Codex are both started from the same project directory.

## Same-directory resume flow

1. Work in Claude Code inside the project directory.
2. Exit Claude Code and keep either the Claude session ID or renamed session title.
3. Start Codex from the same directory.
4. Ask Codex to use this skill on the session name or ID.
5. Codex previews candidates with `--same-directory --list`.
6. Codex installs a Codex resume session with `--same-directory --install-codex-session`.
7. Codex reports the printed `codex resume <session-id>` command and thread name.
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

## Notes

- `--same-directory` restricts lookup to Claude sessions associated with the current working directory and embeds that same directory as the Codex resume cwd.
- `--include-predecessors` follows Claude compact-summary links only under `~/.claude/projects`, avoiding unrelated dataset JSONL files.
- `--tool-output-chars 4000` keeps the imported session readable while preserving useful tool context.
- `--entire` is available, but it disables tool-output truncation and can create a very large imported context.
- The installer backs up `~/.codex/session_index.jsonl` before appending a new resume entry.
- The installer does not modify Codex SQLite state.

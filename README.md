# Personal Skills

A collection of custom coding-agent skills for extending Claude Code, Codex, and related local agent workflows.

## Skills

| Skill | Description | Docs |
|---|---|---|
| [youtube-watcher](youtube-watcher/) | Fetch YouTube video transcripts with auto language detection. Summarize, search, or extract info from videos in any language. Adopted from [michaelgathara/youtube-watcher](https://clawhub.ai/michaelgathara/youtube-watcher). | [docs/youtube-watcher.md](docs/youtube-watcher.md) |
| [bilibili-watcher](bilibili-watcher/) | Fetch Bilibili (B站) video transcripts via yt-dlp with browser cookie auth (Firefox by default). Handles Bilibili's login-gated subtitles, skips danmaku, and auto-detects language. Inspired by [donnycui/bilibili-youtube-watcher](https://clawhub.ai/donnycui/bilibili-youtube-watcher) and [jiashuoji838-afk/bilibili-watcher](https://clawhub.ai/jiashuoji838-afk/bilibili-watcher). | [docs/bilibili-watcher.md](docs/bilibili-watcher.md) |
| [claude-to-codex-history](claude-to-codex-history/) | Convert Claude Code JSONL session history into Codex continuation artifacts, including a same-directory workflow that installs a compact imported session visible through `codex resume` and stores the full handoff as a sidecar file. | [docs/claude-to-codex-history.md](docs/claude-to-codex-history.md) |

## Repo structure

```
skills/
  README.md                 # This file — skill index
  docs/                     # Per-skill documentation (not bundled with skill installs)
    youtube-watcher.md
    bilibili-watcher.md
    claude-to-codex-history.md
  youtube-watcher/          # Skill: YouTube transcript fetcher
    SKILL.md                # Skill definition (what Claude reads)
    _meta.json              # Skill metadata
    scripts/
      get_transcript.py
  bilibili-watcher/         # Skill: Bilibili transcript fetcher (cookie-authed)
    SKILL.md
    _meta.json
    scripts/
      get_transcript.py
  claude-to-codex-history/  # Skill: Claude Code -> Codex session handoff/import
    SKILL.md
    _meta.json
    scripts/
      claude_to_codex_history.py
```

Each skill lives in its own folder with a `SKILL.md` (the file the agent reads at runtime) and any supporting scripts. Detailed documentation for each skill is kept in `docs/` — separate from the skill folders so it does not get pulled into the agent context when a skill is loaded.

## Installing a skill

To use a skill locally with Claude Code, copy or symlink its folder into `~/.claude/skills/`:

```bash
# Symlink (recommended — stays in sync with this repo)
ln -s /path/to/skills/youtube-watcher ~/.claude/skills/youtube-watcher

# Or copy
cp -r /path/to/skills/youtube-watcher ~/.claude/skills/youtube-watcher
```

To use a skill locally with Codex, copy or symlink its folder into `~/.codex/skills/`:

```bash
ln -s /path/to/skills/claude-to-codex-history ~/.codex/skills/claude-to-codex-history
```

## Claude Code to Codex resume workflow

Use [claude-to-codex-history](claude-to-codex-history/) when a user wants to continue a Claude Code session in Codex and later use `codex resume`.

Expected workflow:

1. Work in Claude Code inside a project directory.
2. Exit Claude Code and keep the Claude session ID or renamed session title.
3. Start Codex from that same project directory.
4. Ask Codex to use `claude-to-codex-history` on the session name or ID.
5. Codex runs the converter with `--same-directory --install-codex-session`.
6. Codex prints a thread name, full handoff path, and exact `codex resume <session-id>` command.
7. Exit the current Codex chat.
8. Run `codex resume`, select the imported thread, or run the exact command.

Example command from inside the project directory:

```bash
SESSION_NAME_OR_ID="put-session-name-or-id-here"
SHORT_NAME="put-short-readable-name-here"
python3 ~/.codex/skills/claude-to-codex-history/scripts/claude_to_codex_history.py "$SESSION_NAME_OR_ID" \
  --same-directory \
  --include-predecessors \
  --tool-output-chars 4000 \
  --install-codex-session \
  --thread-name "Imported Claude: $SHORT_NAME"
```

The installed resume session contains bounded recent context so Codex can replay it without exceeding the model context window. The full Markdown handoff is printed as `full_handoff_path` and stored under `~/.codex/claude_imports/`.

## Adding a new skill

1. Create a new folder: `my-skill/`
2. Add `SKILL.md` with frontmatter (name, description, triggers) and instructions
3. Add any scripts or supporting files
4. Create `docs/my-skill.md` with human-readable documentation
5. Update this README's skill table

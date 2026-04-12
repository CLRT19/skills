# Personal Skills

A collection of custom [Claude Code skills](https://docs.anthropic.com/en/docs/claude-code/skills) for extending Claude's capabilities.

## Skills

| Skill | Description | Docs |
|---|---|---|
| [youtube-watcher](youtube-watcher/) | Fetch YouTube video transcripts with auto language detection. Summarize, search, or extract info from videos in any language. Adopted from [michaelgathara/youtube-watcher](https://clawhub.ai/michaelgathara/youtube-watcher). | [docs/youtube-watcher.md](docs/youtube-watcher.md) |

## Repo structure

```
skills/
  README.md                 # This file — skill index
  docs/                     # Per-skill documentation (not bundled with skill installs)
    youtube-watcher.md
  youtube-watcher/          # Skill: YouTube transcript fetcher
    SKILL.md                # Skill definition (what Claude reads)
    _meta.json              # Skill metadata
    scripts/
      get_transcript.py
```

Each skill lives in its own folder with a `SKILL.md` (the file Claude reads at runtime) and any supporting scripts. Detailed documentation for each skill is kept in `docs/` — separate from the skill folders so it doesn't get pulled into Claude's context when a skill is loaded.

## Installing a skill

To use a skill locally, copy or symlink its folder into `~/.claude/skills/`:

```bash
# Symlink (recommended — stays in sync with this repo)
ln -s /path/to/skills/youtube-watcher ~/.claude/skills/youtube-watcher

# Or copy
cp -r /path/to/skills/youtube-watcher ~/.claude/skills/youtube-watcher
```

## Adding a new skill

1. Create a new folder: `my-skill/`
2. Add `SKILL.md` with frontmatter (name, description, triggers) and instructions
3. Add any scripts or supporting files
4. Create `docs/my-skill.md` with human-readable documentation
5. Update this README's skill table

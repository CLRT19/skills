# bilibili-watcher

Fetch Bilibili (B站) video transcripts for summarization, Q&A, and content extraction. Mirrors the `youtube-watcher` skill but handles Bilibili's login-gated subtitle access.

## What it does

Given a Bilibili URL (BV, av, or `b23.tv`), this skill:

1. **Reads login cookies** from the user's browser via `yt-dlp --cookies-from-browser` (default: Firefox)
2. **Auto-detects** the subtitle language, preferring manual subs over AI subs, and skipping `danmaku` (user comment overlay — not a transcript)
3. **Downloads** the subtitle file (VTT format)
4. **Cleans** the VTT into plain readable text
5. **Outputs** a `[language: XX]` header so Claude knows which language to respond in

## Why this skill is different from youtube-watcher

**Bilibili gates subtitles behind login.** Without valid login cookies, yt-dlp can only retrieve `danmaku` (user comment overlay XML) — not a real transcript. This is a Bilibili platform policy since roughly 2022; their public subtitle API also returns `subtitles: []` without authentication.

The skill therefore requires the user to:
1. Be logged into bilibili.com in a supported browser
2. Have that browser's cookies readable by `yt-dlp --cookies-from-browser`

## Browser choice on macOS (important)

The default browser is **Firefox** because live testing on macOS revealed that other browsers have real obstacles:

| Browser | Status on macOS | Notes |
|---|---|---|
| **Firefox** (default) | Works out of the box | No encryption, no sandboxing — the reliable choice. |
| Chrome | Partial — fails silently | Chrome encrypts sensitive cookies (SESSDATA, bili_jct, DedeUserID) with macOS Keychain. yt-dlp extracts them but usually can't decrypt without a Keychain prompt, so you'll get `buvid3` only and see "Subtitles are only available when logged in" even when logged in. |
| Safari | Blocked by sandbox | Safari's `Cookies.binarycookies` lives inside `~/Library/Containers/com.apple.Safari/`. macOS blocks read access unless you grant **Full Disk Access** to your terminal in System Settings — a broad permission the skill avoids requiring. |
| Edge / Brave / Opera / Vivaldi | Usually works | Chromium-based but with simpler cookie stores than Chrome's Keychain-protected one. Pass via `--browser edge` etc. |

If you see `No Bilibili login cookies found in firefox`, log into bilibili.com in Firefox and retry. If you really want to use Chrome or Safari, follow the OS prompts that appear and expect friction.

## Language behavior

The skill follows the subtitle's language by default. Bilibili is almost always Chinese:

| Detected language | Summary language |
|---|---|
| `zh`, `zh-Hans`, `ai-zh` (AI-generated Chinese) | Chinese |
| `ja` | Japanese |
| `en` (rare on Bilibili) | English |

Override with `--lang XX` or tell Claude to respond in a specific language.

## Requirements

| Dependency | Version | Install |
|---|---|---|
| Python | 3.8+ | Pre-installed on macOS / `brew install python` |
| `yt-dlp` | latest | `brew install yt-dlp` or `pip install yt-dlp` |
| Browser with Bilibili login | Firefox recommended on macOS | `brew install --cask firefox`, then log into bilibili.com |

`yt-dlp` must be on your PATH. No additional Python packages are needed — the script uses only the standard library.

## Files

```
bilibili-watcher/
  SKILL.md                  # Skill definition (frontmatter + instructions for Claude)
  _meta.json                # Skill metadata
  scripts/
    get_transcript.py       # Main script — fetches, authenticates, cleans transcripts
```

## Usage examples

```bash
# Default: read Firefox cookies, auto-detect language
python3 bilibili-watcher/scripts/get_transcript.py "https://www.bilibili.com/video/BV1g7wJz8Ey4"

# Use a different browser
python3 bilibili-watcher/scripts/get_transcript.py --browser edge "https://www.bilibili.com/video/BV1g7wJz8Ey4"

# Force a specific subtitle language
python3 bilibili-watcher/scripts/get_transcript.py --lang zh-Hans "https://www.bilibili.com/video/BV1g7wJz8Ey4"

# Multi-part videos use the ?p= selector
python3 bilibili-watcher/scripts/get_transcript.py "https://www.bilibili.com/video/BV1xxxxxxxxx?p=2"

# Short links work too
python3 bilibili-watcher/scripts/get_transcript.py "https://b23.tv/xxxxx"
```

## How it works

1. Runs `yt-dlp --cookies-from-browser {browser} --list-subs` to enumerate available subtitle languages
2. Parses the output, **skipping `danmaku`** (user comment overlay) and translated auto-captions, preferring manual subs over AI subs
3. Downloads subtitles to a temp directory with `--cookies-from-browser {browser} --write-subs --write-auto-subs --sub-lang {lang} --convert-subs vtt`
4. Strips VTT headers, timestamps (supports both `HH:MM:SS.mmm` YouTube-style and `MM:SS.mmm` Bilibili-style), duplicate lines, and HTML tags
5. Prints clean text prefixed with `[language: XX]`

## Error modes

| Situation | Behavior |
|---|---|
| `yt-dlp` not installed | Error with install hint (`brew install yt-dlp` or `pip install yt-dlp`) |
| Not logged into Bilibili in the chosen browser | Clear error with retry instructions — no falling back to danmaku |
| Video has no subtitles at all (not auto-captioned) | Error suggesting user check the CC icon in the Bilibili player |
| Wrong browser name (e.g., `--browser firefox` when Firefox isn't installed) | yt-dlp's own error surfaces cleanly |

## Credits

References that informed this skill:
- [donnycui/bilibili-youtube-watcher](https://clawhub.ai/donnycui/bilibili-youtube-watcher) on ClawHub — dual-platform skill, uses yt-dlp without cookies (effectively returns danmaku only for Bilibili)
- [jiashuoji838-afk/bilibili-watcher](https://clawhub.ai/jiashuoji838-afk/bilibili-watcher) on ClawHub — Bilibili-only wrapper around yt-dlp, same cookie limitation

This skill diverges from both by adding explicit `--cookies-from-browser` auth (so real subtitles come through instead of danmaku), defaulting to Firefox to avoid macOS Chrome/Safari cookie pitfalls, skipping danmaku during language detection, and handling Bilibili's `MM:SS.mmm` VTT timestamp format.

## Version history

| Version | Changes |
|---|---|
| 1.0.0 | Initial release. yt-dlp + `--cookies-from-browser firefox` default, `[language: XX]` header output, danmaku filtering, Bilibili-compatible VTT cleaning. |

---
name: bilibili-watcher
description: Fetch and read transcripts from Bilibili (B站) videos. Use when you need to summarize a Bilibili video, answer questions about its content, or extract information from it.
author: CLRT19
version: 1.0.0
triggers:
  - "watch bilibili"
  - "summarize bilibili"
  - "bilibili transcript"
  - "bilibili summary"
  - "analyze bilibili video"
  - "b站"
  - "哔哩哔哩"
metadata: {"clawdbot":{"emoji":"📺","requires":{"bins":["yt-dlp"]},"install":[{"id":"brew","kind":"brew","formula":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp (brew)"},{"id":"pip","kind":"pip","package":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp (pip)"}]}}
---

# Bilibili Watcher

Fetch transcripts from Bilibili (B站) videos for summarization, QA, and content extraction. Mirrors the `youtube-watcher` skill but handles Bilibili's login-gated subtitle access.

## Usage

### Get Transcript

Retrieve the text transcript of a Bilibili video. The script auto-detects the subtitle language and reads login cookies from Firefox by default.

```bash
python3 {baseDir}/scripts/get_transcript.py "https://www.bilibili.com/video/BVxxxxxxxxxx"
```

Accepted URL formats:
- `https://www.bilibili.com/video/BVxxxxxxxxxx`
- `https://www.bilibili.com/video/avxxxxxxxx`
- `https://b23.tv/xxxxx` (short link)
- Any of the above with `?p=N` for multi-part video selectors

To override the language (rare — Bilibili is almost always Chinese):

```bash
python3 {baseDir}/scripts/get_transcript.py --lang zh "https://www.bilibili.com/video/BVxxxxxxxxxx"
```

To use a different browser for cookies (default is `firefox`):

```bash
python3 {baseDir}/scripts/get_transcript.py --browser chrome "https://www.bilibili.com/video/BVxxxxxxxxxx"
```

## Bilibili Login Requirement

**Bilibili gates subtitles behind login.** Without cookies, only `danmaku` (user comment overlay) is available — not a real transcript. The script reads login cookies from the user's browser via `yt-dlp --cookies-from-browser`.

**Default: Firefox** (reason: on macOS, Chrome encrypts cookies with Keychain and Safari's cookie file is in a sandboxed container requiring Full Disk Access — Firefox avoids both issues). User must be logged into bilibili.com in Firefox for the skill to work.

If the user sees `"Subtitles are only available when logged in"` or `"No Bilibili login cookies found"`:
1. Tell them to log into bilibili.com in Firefox (or supply `--browser` to pick another).
2. Retry.

If the video genuinely has no subtitles (Bilibili does not auto-caption every video), the script exits with a clear message. Suggest checking for the CC icon in the Bilibili player.

## Language Rules

**The script outputs a `[language: XX]` header indicating the detected transcript language. Follow these rules:**

1. **Always summarize and respond in the same language as the transcript**, unless the user explicitly asks for a different language.
   - Chinese transcript → Chinese summary
   - Japanese transcript → Japanese summary
   - English transcript → English summary (rare on Bilibili)
2. If the user requests a specific output language (e.g. "summarize in English"), follow the user's instruction instead.

## Examples

**Summarize a Bilibili video:**

1. Get the transcript:
   ```bash
   python3 {baseDir}/scripts/get_transcript.py "https://www.bilibili.com/video/BV1g7wJz8Ey4"
   ```
2. Read the `[language: XX]` header from the output.
3. Summarize in that same language (almost always Chinese for Bilibili).

**Find specific information:**

1. Get the transcript.
2. Search the text for keywords or answer the user's question.
3. Respond in the transcript's language unless the user indicates otherwise.

## Notes

- Requires `yt-dlp` installed and on PATH (`brew install yt-dlp` or `pip install yt-dlp`).
- Requires the user to be logged into Bilibili in a supported browser (Firefox by default).
- Prefers manual subtitles over AI-generated subtitles.
- Skips `danmaku` (user comment overlay) — it is not a transcript.
- Works with multi-part videos via `?p=N` URL selectors.

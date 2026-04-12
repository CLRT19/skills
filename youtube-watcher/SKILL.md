---
name: youtube-watcher
description: Fetch and read transcripts from YouTube videos. Use when you need to summarize a video, answer questions about its content, or extract information from it.
author: CLRT19
version: 1.1.0
triggers:
  - "watch youtube"
  - "summarize video"
  - "video transcript"
  - "youtube summary"
  - "analyze video"
metadata: {"clawdbot":{"emoji":"📺","requires":{"bins":["yt-dlp"]},"install":[{"id":"brew","kind":"brew","formula":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp (brew)"},{"id":"pip","kind":"pip","package":"yt-dlp","bins":["yt-dlp"],"label":"Install yt-dlp (pip)"}]}}
---

# YouTube Watcher

Fetch transcripts from YouTube videos to enable summarization, QA, and content extraction.

## Usage

### Get Transcript

Retrieve the text transcript of a video. The script auto-detects the video's native language and fetches subtitles in that language.

```bash
python3 {baseDir}/scripts/get_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

To override the language (e.g. if the user requests a specific language):

```bash
python3 {baseDir}/scripts/get_transcript.py --lang zh "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Language Rules

**The script outputs a `[language: XX]` header indicating the detected transcript language. Follow these rules:**

1. **Always summarize and respond in the same language as the transcript**, unless the user explicitly asks for a different language.
   - Chinese transcript -> Chinese summary
   - English transcript -> English summary
   - Japanese transcript -> Japanese summary
2. If the user requests a specific output language (e.g. "summarize in English"), follow the user's instruction instead.

## Examples

**Summarize a video:**

1. Get the transcript:
   ```bash
   python3 {baseDir}/scripts/get_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
   ```
2. Read the `[language: XX]` header from the output.
3. Summarize in that same language.

**Find specific information:**

1. Get the transcript.
2. Search the text for keywords or answer the user's question based on the content.
3. Respond in the transcript's language unless the user indicates otherwise.

## Notes

- Requires `yt-dlp` to be installed and available in the PATH.
- Works with videos that have closed captions (CC) or auto-generated subtitles.
- If a video has no subtitles, the script will fail with an error message.
- The script prefers manual subtitles over auto-generated ones.
- Native auto-generated subtitles are preferred over translated ones.

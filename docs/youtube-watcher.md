# youtube-watcher

Fetch YouTube video transcripts for summarization, Q&A, and content extraction.

## What it does

Given a YouTube URL, this skill:

1. **Auto-detects** the video's native subtitle language (manual subs preferred over auto-generated)
2. **Downloads** the transcript in that language
3. **Cleans** the raw VTT/subtitle format into plain readable text
4. **Outputs** a `[language: XX]` header so Claude knows which language to respond in

## Language behavior

The skill follows the video's original language by default:

| Video language | Transcript language | Summary language |
|---|---|---|
| Chinese | Chinese | Chinese |
| English | English | English |
| Japanese | Japanese | Japanese |

The user can override this with `--lang XX` or by asking Claude to respond in a specific language.

## Requirements

| Dependency | Version | Install |
|---|---|---|
| Python | 3.8+ | Pre-installed on macOS / `brew install python` |
| `yt-dlp` | latest | `brew install yt-dlp` or `pip install yt-dlp` |

`yt-dlp` must be on your PATH. No additional Python packages are needed — the script uses only the standard library.

## Files

```
youtube-watcher/
  SKILL.md                  # Skill definition (frontmatter + instructions for Claude)
  _meta.json                # Skill metadata
  scripts/
    get_transcript.py       # Main script — fetches and cleans transcripts
```

## Usage examples

```bash
# Auto-detect language
python3 youtube-watcher/scripts/get_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Force a specific language
python3 youtube-watcher/scripts/get_transcript.py --lang zh "https://www.youtube.com/watch?v=VIDEO_ID"
```

## How it works

1. Runs `yt-dlp --list-subs` to discover available subtitle tracks
2. Parses the output to find the native language (prefers manual subs > native auto-subs > translated auto-subs)
3. Downloads subtitles in VTT format using `yt-dlp --write-subs --write-auto-subs`
4. Strips VTT headers, timestamps, duplicate lines, and HTML tags
5. Outputs clean text prefixed with `[language: XX]`

## Credits

Adopted from [michaelgathara/youtube-watcher](https://clawhub.ai/michaelgathara/youtube-watcher) on ClawHub. Original skill by Michael Gathara. Modified with native language auto-detection and language-matching summarization rules.

## Version history

| Version | Changes |
|---|---|
| 1.1.0 | Auto-detect native language instead of hardcoding English. Added `--lang` override flag. Added `[language: XX]` output header. Updated SKILL.md with language-matching rules. |
| 1.0.0 | Initial version (English-only, from [michaelgathara/youtube-watcher](https://clawhub.ai/michaelgathara/youtube-watcher)) |

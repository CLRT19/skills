#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def clean_vtt(content: str) -> str:
    """
    Clean WebVTT content to plain text.
    Removes headers, timestamps, and duplicate lines.
    """
    lines = content.splitlines()
    text_lines = []

    timestamp_pattern = re.compile(
        r"\d{2}:\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}:\d{2}\.\d{3}"
    )

    for line in lines:
        line = line.strip()
        if not line or line == "WEBVTT" or line.isdigit():
            continue
        if timestamp_pattern.match(line):
            continue
        if line.startswith("NOTE") or line.startswith("STYLE"):
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue

        if text_lines and text_lines[-1] == line:
            continue

        line = re.sub(r"<[^>]+>", "", line)

        text_lines.append(line)

    return "\n".join(text_lines)


def detect_native_language(url: str) -> str:
    """
    Detect the video's native/original subtitle language.
    Checks manual subs first, then falls back to auto-generated subs.
    Returns the language code (e.g. 'en', 'zh', 'ja', 'ko').
    """
    cmd = [
        "yt-dlp",
        "--list-subs",
        "--skip-download",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
    except FileNotFoundError:
        print("Error: yt-dlp not found. Please install it.", file=sys.stderr)
        sys.exit(1)

    # Parse --list-subs output to find available languages
    # (We don't trust %(language)s metadata — it often returns "NA")
    # Look for manual subtitles first
    manual_section = False
    auto_section = False
    manual_langs = []
    auto_langs = []

    for line in output.splitlines():
        if "Available subtitles" in line and "automatic" not in line.lower():
            manual_section = True
            auto_section = False
            continue
        if "Available automatic captions" in line or "automatic" in line.lower():
            auto_section = True
            manual_section = False
            continue
        if manual_section or auto_section:
            stripped = line.strip()
            # Skip table header and separator lines
            if stripped.startswith("Language") or stripped.startswith("---"):
                continue
            # Language lines look like: "en     English   vtt, srt, ..."
            match = re.match(r"^([a-zA-Z]{2,}(?:-[a-zA-Z]+)*)\s+", stripped)
            if match:
                lang = match.group(1)
                # Skip translated auto-captions (e.g. "en-zh", "ja-zh")
                if "-" in lang and auto_section:
                    continue
                if manual_section:
                    manual_langs.append(lang)
                elif auto_section:
                    auto_langs.append(lang)

    # Prefer manual subs, then native auto-subs
    if manual_langs:
        return manual_langs[0]
    if auto_langs:
        return auto_langs[0]

    return "en"  # fallback


def get_transcript(url: str, lang: str = None):
    # Detect native language if not specified
    if not lang:
        lang = detect_native_language(url)

    print(f"[language: {lang}]")

    with tempfile.TemporaryDirectory() as temp_dir:
        cmd = [
            "yt-dlp",
            "--write-subs",
            "--write-auto-subs",
            "--skip-download",
            "--sub-lang",
            lang,
            "--output",
            "subs",
            url,
        ]

        try:
            subprocess.run(cmd, cwd=temp_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running yt-dlp: {e.stderr.decode()}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print("Error: yt-dlp not found. Please install it.", file=sys.stderr)
            sys.exit(1)

        temp_path = Path(temp_dir)
        vtt_files = list(temp_path.glob("*.vtt"))

        if not vtt_files:
            print("No subtitles found.", file=sys.stderr)
            sys.exit(1)

        vtt_file = vtt_files[0]

        content = vtt_file.read_text(encoding="utf-8")
        clean_text = clean_vtt(content)
        print(clean_text)


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube transcript.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--lang",
        default=None,
        help="Subtitle language code (e.g. en, zh, ja). Auto-detected if omitted.",
    )
    args = parser.parse_args()

    get_transcript(args.url, args.lang)


if __name__ == "__main__":
    main()

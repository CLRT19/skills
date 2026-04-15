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

    # Handles both "HH:MM:SS.mmm" (YouTube) and "MM:SS.mmm" (Bilibili) formats
    timestamp_pattern = re.compile(
        r"(?:\d{2}:)?\d{2}:\d{2}\.\d{3}\s-->\s(?:\d{2}:)?\d{2}:\d{2}\.\d{3}"
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


def _login_required(output: str) -> bool:
    return "Subtitles are only available when logged in" in output


def detect_native_language(url: str, browser: str) -> str:
    """
    Detect the subtitle language available for the Bilibili video.
    Requires login cookies via --cookies-from-browser.
    Skips 'danmaku' (comment overlay — not a transcript).
    Returns the language code (e.g. 'zh-Hans', 'zh', 'en').
    """
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", browser,
        "--list-subs",
        "--skip-download",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
    except FileNotFoundError:
        print("Error: yt-dlp not found. Install with: brew install yt-dlp  (or: pip install yt-dlp)", file=sys.stderr)
        sys.exit(1)

    if _login_required(output):
        print(
            f"Error: No Bilibili login cookies found in {browser}. "
            f"Log into bilibili.com in {browser}, then retry. "
            f"Or use --browser to pick another (chrome, safari, edge, brave).",
            file=sys.stderr,
        )
        sys.exit(1)

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
            if stripped.startswith("Language") or stripped.startswith("---"):
                continue
            match = re.match(r"^([a-zA-Z]{2,}(?:-[a-zA-Z]+)*)\s+", stripped)
            if match:
                lang = match.group(1)
                # Skip danmaku (comment overlay, not a transcript)
                if lang.lower() == "danmaku":
                    continue
                # Skip translated auto-captions in auto section
                if "-" in lang and auto_section and not lang.lower().startswith("zh"):
                    continue
                if manual_section:
                    manual_langs.append(lang)
                elif auto_section:
                    auto_langs.append(lang)

    if manual_langs:
        return manual_langs[0]
    if auto_langs:
        return auto_langs[0]

    return "zh"  # Bilibili default


def get_transcript(url: str, lang: str = None, browser: str = "firefox"):
    if not lang:
        lang = detect_native_language(url, browser)

    print(f"[language: {lang}]")

    with tempfile.TemporaryDirectory() as temp_dir:
        cmd = [
            "yt-dlp",
            "--cookies-from-browser", browser,
            "--write-subs",
            "--write-auto-subs",
            "--skip-download",
            "--sub-lang", lang,
            "--sub-format", "vtt/srt/best",
            "--convert-subs", "vtt",
            "--output", "subs",
            url,
        ]

        try:
            result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)
        except FileNotFoundError:
            print("Error: yt-dlp not found. Install with: brew install yt-dlp  (or: pip install yt-dlp)", file=sys.stderr)
            sys.exit(1)

        combined = (result.stdout or "") + (result.stderr or "")
        if _login_required(combined):
            print(
                f"Error: No Bilibili login cookies found in {browser}. "
                f"Log into bilibili.com in {browser}, then retry.",
                file=sys.stderr,
            )
            sys.exit(1)

        if result.returncode != 0:
            print(f"Error running yt-dlp:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)

        temp_path = Path(temp_dir)
        vtt_files = list(temp_path.glob("*.vtt"))

        if not vtt_files:
            print(
                "No subtitles found for this video. Bilibili does not auto-caption every video — "
                "check whether the CC icon is visible in the Bilibili player.",
                file=sys.stderr,
            )
            sys.exit(1)

        content = vtt_files[0].read_text(encoding="utf-8")
        print(clean_vtt(content))


def main():
    parser = argparse.ArgumentParser(description="Fetch Bilibili transcript.")
    parser.add_argument("url", help="Bilibili video URL (BV, av, or b23.tv)")
    parser.add_argument(
        "--lang",
        default=None,
        help="Subtitle language code (e.g. zh, zh-Hans, en). Auto-detected if omitted.",
    )
    parser.add_argument(
        "--browser",
        default="firefox",
        help="Browser to read login cookies from (default: firefox). "
             "Other options: chrome, safari, edge, brave, opera, vivaldi.",
    )
    args = parser.parse_args()

    get_transcript(args.url, args.lang, args.browser)


if __name__ == "__main__":
    main()

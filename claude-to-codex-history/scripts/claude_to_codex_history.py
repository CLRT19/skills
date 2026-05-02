#!/usr/bin/env python3
"""Convert Claude Code session JSONL into Codex-ready handoff artifacts."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RAW_PATH_RE = re.compile(r"(?P<path>/[^\s`'\"]+?\.jsonl)")
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Claude Code session history to Codex-ready handoff formats."
    )
    parser.add_argument(
        "session",
        nargs="?",
        help="Claude session id, title/search query, JSONL file, or project directory.",
    )
    parser.add_argument(
        "--claude-root",
        default=str(Path.home() / ".claude"),
        help="Claude config/history root. Default: ~/.claude",
    )
    parser.add_argument(
        "--project",
        help="Restrict search to project path substring or Claude project directory name.",
    )
    parser.add_argument(
        "--same-directory",
        action="store_true",
        help=(
            "Same-directory workflow: restrict Claude search to the current working "
            "directory and set the installed Codex session cwd to it."
        ),
    )
    parser.add_argument(
        "--resume-cwd",
        help="Cwd to embed in an installed Codex session. Default: Claude session cwd.",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use the latest Claude project JSONL when no session/query is supplied.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List candidate sessions and exit unless an output path is also supplied.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "messages-jsonl", "codex-jsonl"],
        default="markdown",
        help="Output format. Default: markdown.",
    )
    parser.add_argument("-o", "--output", help="Output path. Default: stdout.")
    parser.add_argument(
        "--include-predecessors",
        action="store_true",
        help="Recursively include JSONL paths referenced by Claude compact summaries.",
    )
    parser.add_argument(
        "--entire",
        action="store_true",
        help="Full continuity mode: include predecessors and do not truncate tool output.",
    )
    parser.add_argument(
        "--tool-output-chars",
        type=int,
        default=8000,
        help="Max chars per tool/log block unless --full-tools is set. Default: 8000.",
    )
    parser.add_argument(
        "--full-tools",
        action="store_true",
        help="Do not truncate tool/log output.",
    )
    parser.add_argument(
        "--redact-secrets",
        action="store_true",
        help="Redact common token/API-key patterns in rendered text.",
    )
    parser.add_argument(
        "--codex-session-id",
        help="Session id to embed when --format codex-jsonl is used. Default: uuid4.",
    )
    parser.add_argument(
        "--install-codex-session",
        action="store_true",
        help="Install a best-effort native Codex resume session under ~/.codex.",
    )
    parser.add_argument(
        "--codex-root",
        default=str(Path.home() / ".codex"),
        help="Codex config/session root for --install-codex-session. Default: ~/.codex",
    )
    parser.add_argument(
        "--thread-name",
        help="Thread name for the installed Codex resume entry.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="For --install-codex-session, print planned paths without writing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="For --install-codex-session, allow overwriting an existing session id/index entry.",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                records.append(
                    {
                        "type": "parse_error",
                        "timestamp": None,
                        "message": {
                            "role": "system",
                            "content": f"[JSON parse error at {path}:{line_no}: {exc}]",
                        },
                    }
                )
                continue
            records.append(obj)
    return records


def iso_time(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc).isoformat()
    except ValueError:
        return str(value)


def sort_key_time(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value / 1000 if value > 10_000_000_000 else value)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def maybe_truncate(text: str, limit: int) -> str:
    if limit < 0 or len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n[... truncated {omitted} chars ...]"


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED_SECRET]", text)
    return text


def render_block(value: Any, limit: int, redact_secrets: bool) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, indent=2)
        except TypeError:
            text = repr(value)
    text = maybe_truncate(text, limit)
    return redact(text) if redact_secrets else text


def render_content(content: Any, limit: int, redact_secrets: bool) -> str:
    parts: list[str] = []
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                parts.append(render_block(item, limit, redact_secrets))
                continue
            item_type = item.get("type", "")
            if item_type in {"text", "input_text", "output_text"}:
                parts.append(str(item.get("text") or item.get("content") or ""))
            elif item_type in {"thinking", "redacted_thinking"}:
                continue
            elif item_type == "tool_use":
                name = item.get("name", "<tool>")
                payload = render_block(item.get("input", {}), limit, redact_secrets)
                parts.append(f"[tool_use: {name}]\n```json\n{payload}\n```")
            elif item_type == "tool_result":
                payload = render_block(item.get("content", ""), limit, redact_secrets)
                suffix = " error" if item.get("is_error") else ""
                parts.append(f"[tool_result{suffix}]\n{payload}")
            else:
                parts.append(render_block(item, limit, redact_secrets))
    elif content is None:
        pass
    else:
        parts.append(render_block(content, limit, redact_secrets))
    text = "\n\n".join(part for part in parts if part is not None)
    return redact(text) if redact_secrets else text


def record_to_message(
    record: dict[str, Any], source: Path, limit: int, redact_secrets: bool
) -> dict[str, Any] | None:
    if record.get("type") not in {"user", "assistant"}:
        return None
    message = record.get("message") or {}
    role = message.get("role") or record.get("type")
    if role not in {"user", "assistant", "system"}:
        role = record.get("type", "user")
    content = render_content(message.get("content", ""), limit, redact_secrets).strip()
    if not content:
        return None
    return {
        "role": role,
        "content": content,
        "timestamp": iso_time(record.get("timestamp")),
        "source_path": str(source),
        "uuid": record.get("uuid"),
        "session_id": record.get("sessionId"),
        "cwd": record.get("cwd"),
        "git_branch": record.get("gitBranch"),
    }


def session_metadata(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "path": str(path),
        "session_id": path.stem,
        "mtime": iso_time(path.stat().st_mtime),
        "lines": len(records),
    }
    timestamps = [r.get("timestamp") for r in records if r.get("timestamp") is not None]
    if timestamps:
        meta["first_timestamp"] = iso_time(min(timestamps, key=sort_key_time))
        meta["last_timestamp"] = iso_time(max(timestamps, key=sort_key_time))
    for record in records:
        if record.get("cwd") and "cwd" not in meta:
            meta["cwd"] = record.get("cwd")
        if record.get("gitBranch") and "git_branch" not in meta:
            meta["git_branch"] = record.get("gitBranch")
        if record.get("version") and "claude_version" not in meta:
            meta["claude_version"] = record.get("version")
    return meta


def claude_project_files(root: Path) -> list[Path]:
    projects = root / "projects"
    if not projects.exists():
        return []
    return sorted(projects.glob("**/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def project_matches(path: Path, project_filter: str | None) -> bool:
    if not project_filter:
        return True
    project_filter = project_filter.lower()
    return project_filter in str(path).lower()


def find_session_file(root: Path, session_id: str) -> Path | None:
    direct = list((root / "projects").glob(f"**/{session_id}.jsonl"))
    if direct:
        return sorted(direct, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    for path in claude_project_files(root):
        if path.stem == session_id:
            return path
    return None


def history_candidates(root: Path, query: str, project_filter: str | None) -> list[dict[str, Any]]:
    history = root / "history.jsonl"
    if not history.exists():
        return []
    query_lower = query.lower()
    by_sid: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(history):
        session_id = str(record.get("sessionId") or "")
        display = str(record.get("display") or "")
        project = str(record.get("project") or "")
        haystack = "\n".join([session_id, display, project]).lower()
        if query_lower not in haystack:
            continue
        if project_filter and project_filter.lower() not in project.lower():
            continue
        path = find_session_file(root, session_id) if session_id else None
        if not path:
            continue
        by_sid[session_id] = {
            "session_id": session_id,
            "path": path,
            "project": project,
            "timestamp": record.get("timestamp"),
            "snippet": display.replace("\n", " ")[:220],
            "source": "history",
        }
    return sorted(by_sid.values(), key=lambda c: sort_key_time(c.get("timestamp")), reverse=True)


def content_candidates(root: Path, query: str, project_filter: str | None) -> list[dict[str, Any]]:
    query_lower = query.lower()
    candidates: list[dict[str, Any]] = []
    for path in claude_project_files(root):
        if not project_matches(path, project_filter):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        idx = text.lower().find(query_lower)
        if idx < 0:
            continue
        snippet = text[max(0, idx - 80) : idx + 160].replace("\n", " ")
        candidates.append(
            {
                "session_id": path.stem,
                "path": path,
                "project": path.parent.name,
                "timestamp": path.stat().st_mtime,
                "snippet": snippet,
                "source": "content",
            }
        )
    return sorted(candidates, key=lambda c: c["path"].stat().st_mtime, reverse=True)


def resolve_candidates(args: argparse.Namespace) -> list[dict[str, Any]]:
    root = Path(args.claude_root).expanduser()
    token = args.session
    if token:
        p = Path(token).expanduser()
        if p.exists():
            if p.is_file():
                return [{"session_id": p.stem, "path": p, "project": p.parent.name, "source": "path"}]
            paths = sorted(p.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
            return [
                {"session_id": path.stem, "path": path, "project": path.parent.name, "source": "dir"}
                for path in paths
            ]
        direct = find_session_file(root, token)
        if direct and project_matches(direct, args.project):
            return [{"session_id": direct.stem, "path": direct, "project": direct.parent.name, "source": "id"}]
        found = history_candidates(root, token, args.project)
        if found:
            return found
        return content_candidates(root, token, args.project)

    paths = [p for p in claude_project_files(root) if project_matches(p, args.project)]
    if args.latest and paths:
        p = paths[0]
        return [{"session_id": p.stem, "path": p, "project": p.parent.name, "source": "latest"}]
    return [
        {"session_id": p.stem, "path": p, "project": p.parent.name, "source": "all"}
        for p in paths[:50]
    ]


def print_candidates(candidates: list[dict[str, Any]]) -> None:
    for i, cand in enumerate(candidates, 1):
        path = cand["path"]
        timestamp = iso_time(cand.get("timestamp") or path.stat().st_mtime)
        print(f"{i:>3}  {cand['session_id']}  {timestamp}  {cand.get('source','')}  {path}")
        snippet = cand.get("snippet")
        if snippet:
            print(f"     {snippet}")


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def referenced_paths(path: Path, records: list[dict[str, Any]], claude_root: Path) -> list[Path]:
    refs: list[Path] = []
    projects_root = claude_root.expanduser().resolve() / "projects"
    for record in records:
        message = record.get("message") or {}
        content = message.get("content")
        try:
            rendered = json.dumps(content, ensure_ascii=False)
        except TypeError:
            rendered = str(content)
        for match in RAW_PATH_RE.finditer(rendered):
            ref = Path(match.group("path"))
            if (
                ref.exists()
                and ref.is_file()
                and ref.suffix == ".jsonl"
                and ref.resolve() != path.resolve()
                and is_under(ref, projects_root)
            ):
                refs.append(ref)
    return refs


def expand_predecessors(paths: Iterable[Path], include: bool, claude_root: Path) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        records = read_jsonl(path)
        if include:
            for ref in referenced_paths(path, records, claude_root):
                visit(ref)
        seen.add(resolved)
        ordered.append(path)

    for p in paths:
        visit(p)
    return ordered


def all_messages(
    session_paths: list[Path], limit: int, redact_secrets: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metas: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    for path in session_paths:
        records = read_jsonl(path)
        metas.append(session_metadata(path, records))
        for record in records:
            msg = record_to_message(record, path, limit, redact_secrets)
            if msg:
                messages.append(msg)
    return metas, messages


def build_markdown(metas: list[dict[str, Any]], messages: list[dict[str, Any]]) -> str:
    cwd = next((m.get("cwd") for m in metas if m.get("cwd")), "")
    lines: list[str] = []
    lines.append("# Claude Code Session Handoff")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    if cwd:
        lines.append(f"Suggested Codex cwd: `{cwd}`")
    lines.append("")
    lines.append("## How To Continue In Codex")
    lines.append("")
    lines.append("Use this file as the initial prompt/context for a new Codex session:")
    lines.append("")
    lines.append("```bash")
    if cwd:
        lines.append(f"codex -C {json.dumps(cwd)} \"$(cat /path/to/this-handoff.md)\"")
    else:
        lines.append('codex "$(cat /path/to/this-handoff.md)"')
    lines.append("```")
    lines.append("")
    lines.append("## Source Sessions")
    lines.append("")
    for meta in metas:
        lines.append(f"- `{meta.get('session_id')}`: `{meta.get('path')}`")
        if meta.get("first_timestamp") or meta.get("last_timestamp"):
            lines.append(
                f"  - time: {meta.get('first_timestamp','?')} to {meta.get('last_timestamp','?')}"
            )
        if meta.get("cwd"):
            lines.append(f"  - cwd: `{meta['cwd']}`")
        if meta.get("git_branch"):
            lines.append(f"  - git branch: `{meta['git_branch']}`")
    lines.append("")
    lines.append("## Transcript")
    lines.append("")
    for idx, msg in enumerate(messages, 1):
        stamp = msg.get("timestamp") or "unknown-time"
        role = msg.get("role", "user")
        source = Path(str(msg.get("source_path", ""))).name
        lines.append(f"### {idx}. {stamp} `{role}` ({source})")
        lines.append("")
        lines.append(msg.get("content", ""))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_messages_jsonl(messages: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(m, ensure_ascii=False) for m in messages) + "\n"


def build_codex_jsonl(
    metas: list[dict[str, Any]], messages: list[dict[str, Any]], session_id: str | None
) -> str:
    cid = session_id or str(uuid.uuid4())
    cwd = next((m.get("cwd") for m in metas if m.get("cwd")), os.getcwd())
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lines: list[str] = [
        json.dumps(
            {
                "timestamp": now,
                "type": "session_meta",
                "payload": {
                    "id": cid,
                    "timestamp": now,
                    "cwd": cwd,
                    "originator": "claude-to-codex-history",
                    "source": "converted-claude-code",
                    "model_provider": "openai",
                },
            },
            ensure_ascii=False,
        )
    ]
    for msg in messages:
        role = msg["role"] if msg["role"] in {"user", "assistant"} else "user"
        text_type = "output_text" if role == "assistant" else "input_text"
        timestamp = (msg.get("timestamp") or now).replace("+00:00", "Z")
        lines.append(
            json.dumps(
                {
                    "timestamp": timestamp,
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": role,
                        "content": [{"type": text_type, "text": msg.get("content", "")}],
                    },
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines) + "\n"


def codex_timestamp(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_resume_jsonl(session_id: str, cwd: str, handoff: str, thread_name: str) -> str:
    now = codex_timestamp()
    records = [
        {
            "timestamp": now,
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "timestamp": now,
                "cwd": cwd,
                "originator": "claude-to-codex-history",
                "cli_version": "converted",
                "source": "converted-claude-code",
                "model_provider": "openai",
            },
        },
        {
            "timestamp": now,
            "type": "event_msg",
            "payload": {
                "type": "thread_name_updated",
                "thread_id": session_id,
                "thread_name": thread_name,
            },
        },
        {
            "timestamp": now,
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Imported Claude Code history handoff. Treat this as prior session "
                            "context and continue from it when the user provides the next request.\n\n"
                            + handoff
                        ),
                    }
                ],
            },
        },
        {
            "timestamp": now,
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Claude Code history handoff imported. Ready to continue from this context.",
                    }
                ],
            },
        },
    ]
    return "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"


def index_contains(index_path: Path, session_id: str) -> bool:
    if not index_path.exists():
        return False
    with index_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                if json.loads(line).get("id") == session_id:
                    return True
            except json.JSONDecodeError:
                continue
    return False


def install_codex_session(
    handoff: str,
    metas: list[dict[str, Any]],
    session_id: str | None,
    codex_root: Path,
    thread_name: str | None,
    resume_cwd: str | None,
    dry_run: bool,
    force: bool,
) -> dict[str, str]:
    cid = session_id or str(uuid.uuid4())
    cwd = resume_cwd or next((m.get("cwd") for m in metas if m.get("cwd")), os.getcwd())
    name = thread_name or f"Imported Claude: {Path(str(metas[-1].get('path', 'session'))).stem}"
    now_local = datetime.now().astimezone()
    day_dir = codex_root.expanduser() / "sessions" / now_local.strftime("%Y") / now_local.strftime("%m") / now_local.strftime("%d")
    filename = f"rollout-{now_local.strftime('%Y-%m-%dT%H-%M-%S')}-{cid}.jsonl"
    session_path = day_dir / filename
    index_path = codex_root.expanduser() / "session_index.jsonl"
    backup_path = index_path.with_name(index_path.name + f".bak-{now_local.strftime('%Y%m%dT%H%M%S')}")
    if session_path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing session file: {session_path} (use --force)")
    if index_contains(index_path, cid) and not force:
        raise SystemExit(f"Session id already exists in {index_path}: {cid} (use --force)")
    if dry_run:
        return {
            "session_id": cid,
            "session_path": str(session_path),
            "index_path": str(index_path),
            "backup_path": str(backup_path),
            "thread_name": name,
            "dry_run": "true",
        }
    day_dir.mkdir(parents=True, exist_ok=True)
    session_path.write_text(build_resume_jsonl(cid, cwd, handoff, name), encoding="utf-8")
    if index_path.exists():
        shutil.copy2(index_path, backup_path)
    with index_path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "id": cid,
                    "thread_name": name,
                    "updated_at": codex_timestamp(),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return {
        "session_id": cid,
        "session_path": str(session_path),
        "index_path": str(index_path),
        "backup_path": str(backup_path) if index_path.exists() else "",
        "thread_name": name,
        "dry_run": "false",
    }


def write_output(text: str, output: str | None) -> None:
    if output:
        out = Path(output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"Wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def main() -> int:
    args = parse_args()
    if args.same_directory:
        args.project = args.project or os.getcwd()
        args.resume_cwd = args.resume_cwd or os.getcwd()
    if args.entire:
        args.include_predecessors = True
        args.full_tools = True
    limit = -1 if args.full_tools else args.tool_output_chars
    candidates = resolve_candidates(args)
    if not candidates:
        print("No Claude sessions matched.", file=sys.stderr)
        return 2
    if args.list:
        print_candidates(candidates)
        if not args.output:
            return 0
    chosen = [Path(candidates[0]["path"])]
    session_paths = expand_predecessors(chosen, args.include_predecessors, Path(args.claude_root))
    metas, messages = all_messages(session_paths, limit, args.redact_secrets)
    if args.install_codex_session:
        handoff = build_markdown(metas, messages)
        result = install_codex_session(
            handoff,
            metas,
            args.codex_session_id,
            Path(args.codex_root),
            args.thread_name,
            args.resume_cwd,
            args.dry_run,
            args.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not args.dry_run:
            print(f"\nResume with: codex resume {result['session_id']}", file=sys.stderr)
        return 0
    if args.format == "markdown":
        text = build_markdown(metas, messages)
    elif args.format == "messages-jsonl":
        text = build_messages_jsonl(messages)
    else:
        text = build_codex_jsonl(metas, messages, args.codex_session_id)
    write_output(text, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

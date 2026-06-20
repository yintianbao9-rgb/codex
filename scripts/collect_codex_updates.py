#!/usr/bin/env python3
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_SOURCES = [
    {"id": "codex_changelog", "title": "Codex Changelog", "url": "https://developers.openai.com/codex/changelog", "type": "official"},
    {"id": "codex_app", "title": "Codex App", "url": "https://developers.openai.com/codex/app", "type": "official"},
    {"id": "codex_cli", "title": "Codex CLI", "url": "https://developers.openai.com/codex/cli", "type": "official"},
    {"id": "codex_ide", "title": "Codex IDE", "url": "https://developers.openai.com/codex/ide", "type": "official"},
    {"id": "codex_auth", "title": "Codex Authentication", "url": "https://developers.openai.com/codex/auth", "type": "official"},
    {"id": "codex_config", "title": "Codex Config Reference", "url": "https://developers.openai.com/codex/config-reference", "type": "official"},
    {"id": "openai_codex_releases", "title": "openai/codex Releases", "url": "https://github.com/openai/codex/releases", "type": "github"},
    {"id": "chatgpt_release_notes", "title": "ChatGPT Release Notes", "url": "https://help.openai.com/en/articles/6825453-chatgpt-release-notes", "type": "official"},
    {"id": "openai_news", "title": "OpenAI News", "url": "https://openai.com/news/", "type": "industry"},
    {"id": "openai_research", "title": "OpenAI Research", "url": "https://openai.com/research/", "type": "industry"},
    {"id": "github_ai_ml", "title": "GitHub AI & ML Blog", "url": "https://github.blog/ai-and-ml/", "type": "industry"},
    {"id": "github_changelog", "title": "GitHub Changelog", "url": "https://github.blog/changelog/", "type": "industry"},
    {"id": "anthropic_news", "title": "Anthropic News", "url": "https://www.anthropic.com/news", "type": "industry"},
    {"id": "google_ai_developers", "title": "Google AI Developers Blog", "url": "https://developers.googleblog.com/en/search/?query=Gemini", "type": "industry"},
]


KEYWORDS = [
    "Codex",
    "ChatGPT",
    "agent",
    "agents",
    "automation",
    "automations",
    "browser",
    "Chrome",
    "CLI",
    "IDE",
    "GitHub",
    "MCP",
    "plugins",
    "skills",
    "memory",
    "model",
    "release",
    "developer",
    "Gemini",
    "Claude",
    "workflow",
    "computer use",
    "image generation",
    "config",
    "authentication",
]


def fetch(url: str) -> tuple[int | None, str, str | None]:
    req = Request(
        url,
        headers={
            "User-Agent": "baoge-ai-site-updater/0.2 (+https://yintianbao9-rgb.github.io/codex/)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(req, timeout=25) as resp:
            data = resp.read(2_000_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.status, data.decode(charset, errors="replace"), None
    except HTTPError as exc:
        return exc.code, "", str(exc)
    except URLError as exc:
        return None, "", str(exc)


def clean_text(html: str) -> str:
    html = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    entities = {
        "&nbsp;": " ",
        "&#160;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
    }
    for src, dst in entities.items():
        text = text.replace(src, dst)
    return re.sub(r"\s+", " ", text).strip()


def extract_title(html: str, fallback: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.S | re.I)
    if not match:
        return fallback
    return re.sub(r"\s+", " ", clean_text(match.group(1))).strip() or fallback


def extract_hits(text: str) -> list[dict]:
    hits = []
    lower = text.lower()
    seen = set()
    for keyword in KEYWORDS:
        idx = lower.find(keyword.lower())
        if idx == -1 or keyword.lower() in seen:
            continue
        seen.add(keyword.lower())
        start = max(0, idx - 140)
        end = min(len(text), idx + 280)
        hits.append({"keyword": keyword, "excerpt": text[start:end].strip()})
    return hits


def write_markdown_summary(path: Path, records: list[dict], stamp: str) -> None:
    failures = [r for r in records if r.get("error") or not r.get("status") or r.get("status", 999) >= 400]
    hit_count = sum(len(r.get("hits", [])) for r in records)
    lines = [
        "# baoge AI 行业与 Codex 更新采集摘要",
        "",
        f"- 采集时间 UTC：{stamp}",
        f"- 来源数量：{len(records)}",
        f"- 成功页面：{len(records) - len(failures)}",
        f"- 失败页面：{len(failures)}",
        f"- 关键词命中：{hit_count}",
        "",
        "## 重点命中",
    ]
    for record in records:
        if not record.get("hits"):
            continue
        lines.append(f"\n### {record['title']}")
        lines.append(f"- 类型：{record['type']}")
        lines.append(f"- URL：{record['url']}")
        for hit in record["hits"][:5]:
            lines.append(f"- **{hit['keyword']}**：{hit['excerpt'][:260]}")
    if failures:
        lines.extend(["", "## 本次失败源"])
        for failure in failures:
            lines.append(f"- {failure['title']}：{failure.get('status')} {failure.get('error')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", default=".")
    parser.add_argument("--output-dir", default="updates/archive")
    args = parser.parse_args()

    site_dir = Path(args.site_dir).resolve()
    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = site_dir / output_root

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = output_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for source in DEFAULT_SOURCES:
        status, html, error = fetch(source["url"])
        record = {**source, "fetched_at": stamp, "status": status, "error": error}
        if html:
            text = clean_text(html)
            record["page_title"] = extract_title(html, source["title"])
            record["hits"] = extract_hits(text)
            record["text_sample"] = text[:1400]
        else:
            record["hits"] = []
            record["text_sample"] = ""
        records.append(record)
        time.sleep(0.6)

    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    latest_json = data_dir / "codex_update_sources.json"
    latest_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    (out_dir / "sources.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "items.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    failures = [r for r in records if r.get("error") or not r.get("status") or r.get("status", 999) >= 400]
    (out_dir / "failures.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in failures) + ("\n" if failures else ""), encoding="utf-8")
    write_markdown_summary(out_dir / "summary.md", records, stamp)

    print(json.dumps({
        "stamp": stamp,
        "records": len(records),
        "failures": len(failures),
        "hits": sum(len(r.get("hits", [])) for r in records),
        "latest_json": str(latest_json),
        "output_dir": str(out_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

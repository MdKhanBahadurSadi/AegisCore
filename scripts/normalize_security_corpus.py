"""Deterministically normalize the explicitly acquired offline source corpus.

This utility reads only paths recorded in ``docs/source-review-manifest.json``.
It has no network, DNS, target-transport, embedding, LLM, or approval capability.
The transformations are intentionally lossy: code examples are excluded from
the normalized retrieval text and the original publisher files are retained in
``knowledge_base/raw`` for human review.
"""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from typing import Any


_SAFE_CWE_SECTIONS = {
    "Description": "Description",
    "Common_Consequences": "Common Consequences",
    "Potential_Mitigations": "Potential Mitigations",
}
_DROP_TAGS = {"script", "style", "pre", "code", "noscript", "svg"}
_BLOCK_TAGS = {
    "address", "article", "blockquote", "br", "dd", "div", "dl", "dt",
    "h1", "h2", "h3", "h4", "h5", "h6", "li", "ol", "p", "section",
    "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}


def _clean_lines(text: str) -> str:
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    blank = False
    for raw_line in text.split("\n"):
        line = re.sub(r"[\t\f\v ]+", " ", raw_line).strip()
        if not line:
            if lines and not blank:
                lines.append("")
            blank = True
            continue
        lines.append(line)
        blank = False
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def normalize_markdown(source_text: str) -> str:
    """Keep Markdown prose and headings while dropping code/example markup."""

    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("Markdown source must be non-empty text")
    text = source_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # Remove YAML front matter, used by the WSTG repository, only when a closed
    # front-matter block appears at the start of the file.
    if lines and lines[0].strip() == "---":
        closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if closing is not None:
            lines = lines[closing + 1 :]

    kept: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    for line in lines:
        fence = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence is not None:
            marker = fence.group(1)
            if fence_char is None:
                fence_char, fence_length = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char, fence_length = None, 0
            continue
        if fence_char is None:
            kept.append(line)
    if fence_char is not None:
        raise ValueError("Markdown source contains an unclosed code fence")
    text = "\n".join(kept)

    # Strip non-code HTML content that can carry executable examples, then
    # remove remaining inline code. Link labels are retained, destinations are
    # not needed because source provenance is recorded separately.
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<(script|style|pre|code)\b[^>]*>.*?</\1\s*>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"(?<!`)`+[^`\n]*`+(?!`)", " ", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s*\[[^\]]+\]:\s*\S+.*$", " ", text, flags=re.MULTILINE)
    text = re.sub(r"\{[%{].*?[%}]\}", " ", text)
    text = re.sub(r"</?[A-Za-z][^>]*>", " ", text)
    text = re.sub(r"(?<!\*)\*\*(.*?)\*\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!\*)\*(.*?)\*(?!\*)", r"\1", text)
    # Some publisher Markdown places an illustrative executable URL directly
    # in prose rather than in code markup. Drop that whole line from retrieval
    # text; the untouched publisher file remains available for human review.
    text = "\n".join(
        line for line in text.split("\n")
        if not re.search(r"(?i)\bjavascript\s*:\s*alert\s*\(", line)
    )
    return _clean_lines(text)


class _CWESectionParser(HTMLParser):
    """Extract only descriptive/mitigation CWE sections, excluding code."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, str | None]] = []
        self.sections: dict[str, list[str]] = {}

    def _active_section(self) -> str | None:
        for _tag, suppressed, selected_id in reversed(self.stack):
            if suppressed:
                return None
            if selected_id is not None:
                return selected_id
        return None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        parent_suppressed = bool(self.stack and self.stack[-1][1])
        suppressed = parent_suppressed or tag.casefold() in _DROP_TAGS
        candidate_id = attr_map.get("id")
        selected_id = candidate_id if not suppressed and candidate_id in _SAFE_CWE_SECTIONS else None
        self.stack.append((tag.casefold(), suppressed, selected_id))
        if selected_id is not None:
            self.sections.setdefault(selected_id, [])
            self.sections[selected_id].append("\n## " + _SAFE_CWE_SECTIONS[selected_id] + "\n")
        if not suppressed:
            section = self._active_section()
            if section is not None and tag.casefold() in _BLOCK_TAGS:
                self.sections[section].append("\n")
            if section is not None and tag.casefold() in {"td", "th"}:
                self.sections[section].append(" | ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.stack or not self.stack[-1][1]:
            section = self._active_section()
            if section is not None and tag.casefold() in _BLOCK_TAGS:
                self.sections[section].append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        match = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if match is None:
            return
        popped = self.stack[match:]
        was_visible = not any(item[1] for item in self.stack)
        self.stack = self.stack[:match]
        if was_visible and tag in _BLOCK_TAGS:
            section = self._active_section()
            if section is not None:
                self.sections[section].append("\n")
        if any(item[2] is not None for item in popped):
            section = self._active_section()
            if section is not None:
                self.sections[section].append("\n")

    def handle_data(self, data: str) -> None:
        section = self._active_section()
        if section is not None:
            self.sections[section].append(" " + data + " ")

    def handle_entityref(self, name: str) -> None:
        self.handle_data(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.handle_data(html.unescape(f"&#{name};"))


def normalize_cwe_html(source_text: str) -> str:
    """Extract CWE description, consequences, and mitigations from official HTML."""

    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("CWE HTML source must be non-empty text")
    parser = _CWESectionParser()
    parser.feed(source_text)
    parser.close()
    ordered = [
        _clean_lines("".join(parser.sections[key]))
        for key in _SAFE_CWE_SECTIONS
        if key in parser.sections
    ]
    if len(ordered) != len(_SAFE_CWE_SECTIONS):
        missing = sorted(set(_SAFE_CWE_SECTIONS) - parser.sections.keys())
        raise ValueError("CWE HTML is missing required selected sections: " + ", ".join(missing))
    return "\n\n".join(ordered)


def _repo_relative(root: Path, value: object, expected_parent: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value:
        raise ValueError("manifest path must be a non-empty string")
    normalized = value.replace("\\", "/")
    candidate = (root / Path(normalized)).resolve(strict=False)
    expected = (root / expected_parent).resolve(strict=True)
    try:
        relative = candidate.relative_to(expected).as_posix()
    except ValueError as exc:
        raise ValueError(f"manifest path escapes {expected_parent}") from exc
    if relative in {"", "."}:
        raise ValueError("manifest path must name a file")
    return candidate, relative


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _metadata_preamble(entry: dict[str, Any]) -> str:
    fields = (
        ("Publisher", entry.get("publisher")),
        ("Acquisition locator", entry.get("source_url")),
        ("Published canonical reference", entry.get("canonical_reference")),
        ("Version", entry.get("version")),
        ("Repository revision", entry.get("repository_revision")),
        ("Revision date", entry.get("revision_date")),
        ("License / terms", entry.get("license")),
        ("License information", entry.get("license_reference")),
        ("Copyright notice", entry.get("copyright_notice")),
        ("Acquired", entry.get("acquired_date")),
        ("Review state", entry.get("review_state")),
        ("Retrieval eligibility", entry.get("retrieval_eligibility")),
    )
    lines = [f"# {entry['title']}", "", "## Corpus provenance metadata", ""]
    for label, value in fields:
        rendered = "Unknown / not stated" if value is None else str(value)
        lines.append(f"- {label}: {rendered}")
    lines.extend(
        [
            f"- Intended use: {entry['intended_use']}",
            "- Limitations: " + " ".join(entry["limitations"]),
            "",
            "This file is a lossy normalized extract, not a verbatim copy of the publisher source. "
            "Use the linked raw source for review. It is a candidate reference, not approved guidance or proof.",
            "",
            "## Normalized publisher content",
            "",
        ]
    )
    return "\n".join(lines)


def normalize_entries(entries: list[dict[str, Any]], repository_root: Path) -> list[tuple[dict[str, Any], str, str]]:
    """Validate and prepare every acquired record before writing any output."""

    root = repository_root.resolve(strict=True)
    prepared: list[tuple[dict[str, Any], str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("acquisition_status") != "acquired":
            raise ValueError("only explicitly acquired manifest entries can be normalized")
        raw_path, _ = _repo_relative(root, entry.get("raw_path"), "knowledge_base/raw")
        normalized_path, normalized_rel = _repo_relative(root, entry.get("normalized_path"), "knowledge_base/normalized")
        if not raw_path.is_file():
            raise FileNotFoundError(f"acquired raw source is missing: {entry.get('raw_path')}")
        raw_bytes = raw_path.read_bytes()
        expected_raw = entry.get("raw_sha256")
        if not isinstance(expected_raw, str) or _sha256(raw_bytes) != expected_raw:
            raise ValueError(f"raw source hash does not match manifest: {entry.get('raw_path')}")
        source_text = raw_bytes.decode("utf-8", errors="strict")
        source_format = entry.get("source_format")
        if source_format == "markdown":
            publisher_text = normalize_markdown(source_text)
        elif source_format == "mitre-cwe-html":
            publisher_text = normalize_cwe_html(source_text)
        else:
            raise ValueError(f"unsupported source_format for {entry.get('source_id', entry.get('title'))}")
        content = _metadata_preamble(entry) + publisher_text + "\n"
        payload = content.encode("utf-8")
        if not publisher_text.strip():
            raise ValueError(f"normalization produced empty content for {entry.get('title')}")
        source_id = "src_" + hashlib.sha256(Path(normalized_rel).name.encode("utf-8")).hexdigest()
        prepared.append((entry, normalized_rel, content))
        entry["normalized_sha256"] = _sha256(payload)
        entry["normalized_bytes"] = len(payload)
        entry["source_id"] = source_id
        entry["ingested_local_path"] = Path(normalized_rel).name
    return prepared


def normalize_manifest(manifest_path: Path, repository_root: Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "aegiscore-source-review-manifest" or manifest.get("schema_version") != 1:
        raise ValueError("unsupported source manifest format or version")
    if manifest.get("default_review_state") != "candidate":
        raise ValueError("source manifest must default new records to candidate")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest entries must be a non-empty list")
    prepared = normalize_entries(entries, repository_root)
    for entry, relative_path, content in prepared:
        destination, _ = _repo_relative(repository_root.resolve(strict=True), f"knowledge_base/normalized/{relative_path}", "knowledge_base/normalized")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content.encode("utf-8"))
    manifest["corpus_status"] = "candidate_corpus"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return [entry["source_id"] for entry in entries]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    manifest = root / "docs" / "source-review-manifest.json"
    ids = normalize_manifest(manifest, root)
    print(f"Normalized {len(ids)} candidate sources; no sources were approved.")
    for source_id in ids:
        print(source_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Clean extracted wikitext. Keep numbers, numeric templates, and <math> blocks."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import mwparserfromhell
except ImportError as exc:
    raise SystemExit("Install mwparserfromhell: pip install mwparserfromhell") from exc

ROOT = Path(__file__).resolve().parents[2]
IN_DIR = ROOT / "data" / "extracted"
OUT_DIR = ROOT / "data" / "cleaned"

HEADING_H4 = re.compile(r"^====\s*(.+?)\s*====\s*$", re.MULTILINE)
HEADING_H3 = re.compile(r"^===\s*(.+?)\s*===\s*$", re.MULTILINE)
HEADING_H2 = re.compile(r"^==\s*(.+?)\s*==\s*$", re.MULTILINE)
REF_BLOCK = re.compile(r"<ref\b[^>]*>.*?</ref>", re.IGNORECASE | re.DOTALL)
REF_SELF = re.compile(r"<ref\b[^>]*/>", re.IGNORECASE)
MATH_BLOCK = re.compile(r"<math\b[^>]*>.*?</math>", re.IGNORECASE | re.DOTALL)
MEDIA_PREFIXES = ("file:", "image:", "media:", "category:")

KEEP_FIRST_PARAM = {
    "icon",
    "flag",
    "green",
    "red",
    "path",
    "plainlist",
    "nowrap",
    "hover box",
}
DROP_TEMPLATES = {
    "version",
    "sversion",
    "estatesnav",
    "add/strategy",
    "add",
    "achievement",
    "mechanics navbox",
    "multicolumn",
    "expand",
    "bonus table",
}


def _stash_math(wikitext: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def repl(match: re.Match) -> str:
        blocks.append(match.group(0))
        return f"@@MATH{len(blocks) - 1}@@"

    return MATH_BLOCK.sub(repl, wikitext), blocks


def _restore_math(text: str, blocks: list[str]) -> str:
    for i, block in enumerate(blocks):
        inner = re.sub(r"^<math\b[^>]*>|</math>$", "", block, flags=re.IGNORECASE | re.DOTALL)
        text = text.replace(f"@@MATH{i}@@", inner.strip())
    return text


def _protect_headings(wikitext: str) -> str:
    text = HEADING_H4.sub(r"@@H4@@\1@@ENDH@@", wikitext)
    text = HEADING_H3.sub(r"@@H3@@\1@@ENDH@@", text)
    text = HEADING_H2.sub(r"@@H2@@\1@@ENDH@@", text)
    return text


def _restore_headings(text: str) -> str:
    text = text.replace("@@H4@@", "\n#### ").replace("@@H3@@", "\n### ").replace("@@H2@@", "\n## ")
    return text.replace("@@ENDH@@", "\n")


def _drop_media_wikilinks(wikitext: str) -> str:
    """Remove File/Image links even when the caption contains nested [[links]]."""
    parsed = mwparserfromhell.parse(wikitext)
    for link in list(parsed.filter_wikilinks()):
        title = str(link.title).strip().lower()
        if title.startswith(MEDIA_PREFIXES):
            try:
                parsed.remove(link)
            except ValueError:
                parsed.replace(link, "")
    return str(parsed)


def _fix_leftover_wikilinks(text: str) -> str:
    text = re.sub(r"\[\[([^\]\n|]+)\|([^\]\n]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]\n]+)\]\]", r"\1", text)
    text = text.replace("[[", "").replace("]]", "")
    return text


def _flatten_templates(wikitext: str) -> str:
    parsed = mwparserfromhell.parse(wikitext)
    templates = list(parsed.filter_templates(recursive=True))
    for template in reversed(templates):
        try:
            name = template.name.strip_code().strip().lower()
        except (ValueError, AttributeError):
            continue
        first = str(template.params[0].value).strip() if template.params else ""
        if name in DROP_TEMPLATES:
            replacement = ""
        elif name in KEEP_FIRST_PARAM:
            replacement = first
        else:
            replacement = " ".join(str(p.value).strip() for p in template.params)
        try:
            parsed.replace(template, replacement)
        except ValueError:
            continue
    return str(parsed)


def clean_wikitext(wikitext: str) -> str:
    text, math_blocks = _stash_math(wikitext)
    text = _drop_media_wikilinks(text)
    text = REF_BLOCK.sub(" ", text)
    text = REF_SELF.sub(" ", text)
    text = _protect_headings(text)
    text = _flatten_templates(text)
    text = str(mwparserfromhell.parse(text).strip_code())
    text = _restore_headings(text)
    text = _restore_math(text, math_blocks)
    text = _fix_leftover_wikilinks(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> None:
    files = sorted(IN_DIR.glob("*.json"))
    if not files:
        raise SystemExit(f"No extracted JSON in {IN_DIR}. Run extract.py first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    math_kept = 0

    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        cleaned = clean_wikitext(record["wikitext"])
        if "@@MATH" in cleaned:
            print(f"warning: unresolved math sentinel in {path.name}")
        if MATH_BLOCK.search(record["wikitext"]):
            math_kept += 1
        out_record = {
            "pageid": record["pageid"],
            "revid": record.get("revid"),
            "title": record["title"],
            "url": record["url"],
            "text": cleaned,
        }
        out = OUT_DIR / path.name
        out.write_text(json.dumps(out_record, ensure_ascii=False, indent=2), encoding="utf-8")
        ok += 1

    leftover_pages = []
    for path in OUT_DIR.glob("*.json"):
        text = json.loads(path.read_text(encoding="utf-8"))["text"]
        if "[[" in text or "]]" in text:
            leftover_pages.append(path.name)
    print(f"Cleaned {ok} pages to {OUT_DIR}")
    print(f"Pages that had <math> in source: {math_kept}")
    if leftover_pages:
        print(f"WARNING: leftover [[ or ]] in {leftover_pages}")
    else:
        print("No leftover [[wikilinks]] in cleaned text.")


if __name__ == "__main__":
    main()

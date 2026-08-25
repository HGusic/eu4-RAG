import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "process"))
from clean import clean_wikitext


def test_nested_file_caption_is_removed():
    raw = (
        "[[File:Advisor_example.png|right|thumb|330px|"
        "Advisors are located on the [[government]] interface]]\n"
        "An '''advisor''' gives {{green|+1}} and 10%.\n"
        r"<math>\text{Hiring cost} = 22</math>"
        "\n"
    )
    out = clean_wikitext(raw)
    assert "interface]]" not in out
    assert "File:" not in out
    assert "]]" not in out
    assert "+1" in out
    assert "10%" in out
    assert "Hiring cost" in out


def test_broken_wikilink_brackets_are_stripped():
    raw = "Threat to [[cogs, so that troops move.\n"
    out = clean_wikitext(raw)
    assert "[[" not in out
    assert "]]" not in out
    assert "cogs" in out

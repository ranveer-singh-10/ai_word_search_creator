"""Tests for validate_words: only clean, unique, grid-sized words get through."""
import pytest

from wordsearch.validate import validate_words


def item(word, description="d"):
    return {"word": word, "description": description}


def test_valid_words_are_upper_cased_and_trimmed():
    valid, rejected = validate_words([item("  comet ", " Icy body ")], max_length=10)
    assert valid == [{"word": "COMET", "description": "Icy body"}]
    assert rejected == []


@pytest.mark.parametrize("word, reason", [
    ("Black hole", "not letters A-Z"),
    ("X-RAY", "not letters A-Z"),
    ("CAFÉ", "not letters A-Z"),
    ("", "not letters A-Z"),
    ("SUN", None),                       # exactly the minimum length is fine
    ("ON", "too short"),
    ("SUPERCALIFRAGILISTIC", "too long for grid"),
])
def test_each_rule(word, reason):
    valid, rejected = validate_words([item(word)], max_length=10)
    if reason is None:
        assert [v["word"] for v in valid] == [word]
    else:
        assert valid == []
        assert rejected == [{"word": word.strip().upper(), "reason": reason}]


def test_duplicates_are_rejected_case_insensitively():
    valid, rejected = validate_words([item("COMET"), item("comet")], max_length=10)
    assert [v["word"] for v in valid] == ["COMET"]
    assert rejected == [{"word": "COMET", "reason": "duplicate"}]


def test_missing_description_is_rejected():
    valid, rejected = validate_words([{"word": "COMET"}], max_length=10)
    assert valid == []
    assert rejected[0]["reason"] == "missing description"


def test_word_exactly_grid_size_is_allowed():
    valid, _ = validate_words([item("ABCDEFGH")], max_length=8)
    assert len(valid) == 1

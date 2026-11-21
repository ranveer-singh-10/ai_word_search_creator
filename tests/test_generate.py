"""Tests for the Claude call and puzzle assembly in generate.py."""
import pytest

from wordsearch import generate


def test_claude_called_once(fake_words):
    fake_words.returns([{"word": "COMET", "description": "Icy body"}])
    generate.generate_populated_wordsearch("Space", 8, "easy", 8)
    assert fake_words.call_count == 1


def test_generate_words_parses_structured_output(fake_claude):
    payload = {"category_suitable": True, "words": [{"word": "COMET", "description": "Icy body"}]}
    fake_claude.reply(payload)

    result = generate.generate_words("Space", "easy", 5, max_length=8)

    assert result["words"] == payload["words"]
    fmt = fake_claude.call_args.kwargs["output_config"]["format"]
    assert fmt["type"] == "json_schema"


def test_generate_words_raises_when_cut_off(fake_claude):
    fake_claude.reply('{"words": [', stop_reason="max_tokens")
    with pytest.raises(RuntimeError):
        generate.generate_words("Space", "easy")


def test_unsuitable_category_raises(fake_claude):
    fake_claude.reply({"category_suitable": False, "words": []})
    with pytest.raises(generate.UnsuitableCategoryError):
        generate.generate_words("something nasty", "easy")


def test_refusal_raises_unsuitable(fake_claude):
    fake_claude.reply("", stop_reason="refusal")
    with pytest.raises(generate.UnsuitableCategoryError):
        generate.generate_words("something nasty", "easy")


def test_errors_carry_usage_for_costing(fake_claude, usage):
    fake_claude.reply("", stop_reason="refusal")
    with pytest.raises(generate.UnsuitableCategoryError) as exc:
        generate.generate_words("something nasty", "easy")
    assert exc.value.usage is usage


def test_prompt_includes_child_safety_rule(fake_claude):
    fake_claude.reply({"category_suitable": True, "words": [{"word": "COMET", "description": "Icy body"}]})
    generate.generate_words("Space", "easy")
    system = fake_claude.call_args.kwargs["system"]
    assert "children" in system and "derogatory" in system

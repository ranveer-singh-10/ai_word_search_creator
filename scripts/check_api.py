"""Quick check that the Anthropic API key in .env works: python scripts/check_api.py"""
import anthropic

from wordsearch.config import DEFAULT_MODEL  # importing config also loads .env

client = anthropic.Anthropic()

msg = client.messages.create(
    model=DEFAULT_MODEL,
    max_tokens=200,
    messages=[{"role": "user", "content": "Give me 5 space-themed words as a JSON list."}],
)
print(next(block.text for block in msg.content if block.type == "text"))

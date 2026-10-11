import os

# generate.py creates the Anthropic client at import time; tests mock it, so any key will do.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

"""Settings in one place: the model, puzzle sizes, pricing and paths. Also loads .env."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # puts ANTHROPIC_API_KEY from .env into the environment

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"

DEFAULT_MODEL = "claude-haiku-5-5"

# Grid size and word count per difficulty. Tune these as you play-test.
GRID_SIZE = {"easy": 8, "medium": 10, "hard": 12}
WORD_COUNT = {"easy": 8, "medium": 10, "hard": 12}

# Shortest word allowed in a puzzle.
MIN_WORD_LENGTH = 3

# US dollars per million (input, output) tokens. Thinking tokens are billed as output.
# Check https://www.anthropic.com/pricing if you change DEFAULT_MODEL.
PRICE_PER_MILLION = {"claude-haiku-5-5": (0.10, 0.50)}

"""Tests for dynamic mode placement in paths.py. Randomised, so each rule is checked over many runs."""
import pytest

from wordsearch.directions import DIRECTIONS, ALLOWED_DIRECTIONS
from wordsearch.grid import EMPTY, generate_empty_grid, place_word
from wordsearch.paths import PATH_RULES, min_turns_for, path_spells, place_word_on_path

RUNS = 50


def steps(path):
    return [(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]


def runs(path):
    """Lengths, in moves, of each straight section of the path."""
    lengths = []
    previous = None
    for step in steps(path):
        if step == previous:
            lengths[-1] += 1
        else:
            lengths.append(1)
        previous = step
    return lengths


def place(difficulty, word, size=10):
    grid = generate_empty_grid(size)
    directions = [DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]]
    path = place_word_on_path(grid, word, directions, **PATH_RULES[difficulty])
    return grid, path


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_placed_path_spells_word_using_allowed_directions(difficulty):
    allowed = {DIRECTIONS[d] for d in ALLOWED_DIRECTIONS[difficulty]}
    for _ in range(RUNS):
        grid, path = place(difficulty, "TELESCOPE")
        assert path is not None
        assert path_spells(grid, "TELESCOPE", path)
        assert set(steps(path)) <= allowed


def test_easy_bends_exactly_once_with_runs_of_three_letters_or_more():
    for _ in range(RUNS):
        _, path = place("easy", "PLANET")
        sections = runs(path)
        assert len(sections) == 2
        assert min(sections) >= 2


def test_medium_bends_once_or_twice_with_runs_of_three_letters_or_more():
    for _ in range(RUNS):
        _, path = place("medium", "ASTRONAUT")
        sections = runs(path)
        assert 2 <= len(sections) <= 3
        assert min(sections) >= 2


@pytest.mark.parametrize("difficulty", ["easy", "medium"])
def test_short_words_stay_straight_on_bends(difficulty):
    for _ in range(RUNS):
        _, path = place(difficulty, "MOON")
        assert len(runs(path)) == 1


def test_hard_snake_always_turns_and_never_reuses_a_cell():
    for _ in range(RUNS):
        _, path = place("hard", "SUN")
        assert len(runs(path)) >= 2
        assert len(set(path)) == len(path)


def test_min_turns_for():
    assert min_turns_for("MOON", 2) == 0
    assert min_turns_for("COMET", 2) == 1
    assert min_turns_for("SUN", 1) == 1


def test_overlaps_only_on_matching_letters():
    grid = generate_empty_grid(5)
    for row in range(5):
        place_word(grid, "XXXXX", (row, 0), DIRECTIONS["right"])
    grid[2][2] = EMPTY
    grid[2][3] = "A"
    path = place_word_on_path(grid, "CAT", list(DIRECTIONS.values()))
    assert path is None                     # no room: only two usable cells
    assert grid[2][2] == EMPTY              # and the grid is left unchanged


def test_shares_a_matching_letter():
    grid = generate_empty_grid(3)
    for row in range(3):
        place_word(grid, "XXX", (row, 0), DIRECTIONS["right"])
    grid[0][0], grid[1][1], grid[2][0] = EMPTY, "A", EMPTY    # free cells force a bend through the A
    path = place_word_on_path(grid, "CAT", list(DIRECTIONS.values()), min_run=1)
    assert path is not None and tuple(path[1]) == (1, 1)
    assert path_spells(grid, "CAT", path)


def test_word_too_long_for_grid_is_not_placed():
    grid = generate_empty_grid(2)
    assert place_word_on_path(grid, "GALAXY", list(DIRECTIONS.values())) is None
    assert all(cell == EMPTY for row in grid for cell in row)


def test_search_gives_up_within_its_step_budget():
    grid = generate_empty_grid(12)
    path = place_word_on_path(grid, "ABCDEFGHIJKL", [DIRECTIONS["right"]], max_turns=0, max_steps=1)
    assert path is None


@pytest.mark.parametrize("path, ok", [
    ([(0, 0), (0, 1), (1, 1)], True),
    ([(0, 0), (0, 1), (2, 2)], False),      # gap between cells
    ([(0, 0), (0, 1), (0, 0)], False),      # reuses a cell
    ([(0, 0), (0, 1)], False),              # too short
    ([(0, 0), (0, 1), (0, 2)], False),      # wrong letter
])
def test_path_spells(path, ok):
    grid = [list("CAX"), list("XTX"), list("XXX")]
    assert path_spells(grid, "CAT", path) is ok

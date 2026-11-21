"""Tests for grid placement and filling. No Claude involved."""
import string

import pytest

from wordsearch import grid as grid_module
from wordsearch.directions import DIRECTIONS
from wordsearch.grid import (
    EMPTY,
    can_place,
    check_word_in_grid,
    fill_empty_squares,
    generate_empty_grid,
    next_cell,
    place_word,
    place_word_in_grid,
)

RIGHT, DOWN = DIRECTIONS["right"], DIRECTIONS["down"]


def test_empty_grid_is_square_and_empty():
    g = generate_empty_grid(5)
    assert len(g) == 5 and all(len(row) == 5 for row in g)
    assert all(cell == EMPTY for row in g for cell in row)


def test_rows_are_independent():
    g = generate_empty_grid(3)
    g[0][0] = "A"
    assert g[1][0] == EMPTY


def test_next_cell_stops_at_edge():
    g = generate_empty_grid(3)
    assert next_cell(g, (0, 1), RIGHT) == (0, 2)
    assert next_cell(g, (0, 2), RIGHT) is None
    assert next_cell(g, (0, 0), DIRECTIONS["up"]) is None


def test_can_place_rejects_running_off_the_grid():
    g = generate_empty_grid(4)
    assert can_place(g, "MOON", (0, 0), RIGHT)
    assert not can_place(g, "MOON", (0, 1), RIGHT)


def test_overlap_allowed_only_on_matching_letter():
    g = generate_empty_grid(5)
    place_word(g, "STAR", (0, 0), RIGHT)
    assert can_place(g, "TOP", (0, 1), DOWN)       # shares the T
    assert not can_place(g, "MOON", (0, 1), DOWN)  # M would overwrite T


@pytest.mark.parametrize("name", list(DIRECTIONS))
def test_placed_word_can_be_found(name):
    g = generate_empty_grid(6)
    assert place_word_in_grid(g, "COMET", [DIRECTIONS[name]])
    assert check_word_in_grid(g, "COMET", [DIRECTIONS[name]])


def test_word_longer_than_grid_is_not_placed():
    g = generate_empty_grid(4)
    assert not place_word_in_grid(g, "GALAXY", [RIGHT, DOWN])
    assert all(cell == EMPTY for row in g for cell in row)


def test_fill_leaves_placed_letters_and_fills_the_rest():
    g = generate_empty_grid(6)
    place_word(g, "COMET", (0, 0), RIGHT)
    fill_empty_squares(g, ["COMET"], "easy")

    assert "".join(g[0][:5]) == "COMET"
    assert all(cell in string.ascii_uppercase for row in g for cell in row)


def test_hard_filler_uses_hidden_word_letters(monkeypatch):
    monkeypatch.setattr(grid_module, "HARD_BIAS", 1.0)  # always pick decoy letters
    g = generate_empty_grid(6)
    fill_empty_squares(g, ["SUN"], "hard")
    assert {cell for row in g for cell in row} <= set("SUN")

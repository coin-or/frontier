"""Edge-case tests for store — corrupted files, zero-objective completeness."""

import tempfile
from pathlib import Path

import pytest

from engine.models import Option, Problem
from engine.store import Store


@pytest.fixture
def tmp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Store(tmpdir)


def test_list_skips_corrupted_json(tmp_store):
    """Corrupted JSON files should be silently skipped in list()."""
    # Save a valid problem
    p = Problem(name="Valid")
    tmp_store.save(p)
    # Write a corrupted JSON file
    (tmp_store.data_dir / "corrupted.json").write_text("{invalid json!!")
    result = tmp_store.list()
    assert len(result) == 1
    assert result[0]["name"] == "Valid"


def test_list_accepts_valid_json_as_problem(tmp_store):
    """Valid JSON gets parsed by Pydantic with defaults — this is expected behavior.

    Pydantic creates a valid Problem since all fields have defaults.
    """
    (tmp_store.data_dir / "not_a_problem.json").write_text('{"foo": "bar"}')
    result = tmp_store.list()
    # Pydantic fills all defaults, so it becomes a valid (empty) Problem
    assert len(result) == 1


def test_scores_completeness_zero_objectives(tmp_store):
    """Problem with options but no objectives → 0.0 completeness."""
    p = Problem(options=[Option(name="A")])
    tmp_store.save(p)
    result = tmp_store.list()
    assert result[0]["status"]["scores_complete"] == 0.0


def test_scores_completeness_empty_problem(tmp_store):
    """Empty problem (no objectives, no options) → 0.0 completeness."""
    p = Problem()
    tmp_store.save(p)
    result = tmp_store.list()
    assert result[0]["status"]["scores_complete"] == 0.0

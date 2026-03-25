"""Tests for JSON file store."""

import tempfile
from pathlib import Path

import pytest

from frontier.engine.models import Objective, Option, Problem, Score
from frontier.engine.store import Store


@pytest.fixture
def tmp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Store(tmpdir)


def test_save_load_round_trip(tmp_store):
    p = Problem(name="Test Problem")
    tmp_store.save(p)
    p2 = tmp_store.load(p.problem_id)
    assert p2.name == "Test Problem"
    assert p2.problem_id == p.problem_id


def test_load_nonexistent(tmp_store):
    with pytest.raises(FileNotFoundError):
        tmp_store.load("nonexistent-id")


def test_delete(tmp_store):
    p = Problem(name="To Delete")
    tmp_store.save(p)
    assert tmp_store.exists(p.problem_id)
    tmp_store.delete(p.problem_id)
    assert not tmp_store.exists(p.problem_id)


def test_delete_nonexistent(tmp_store):
    with pytest.raises(FileNotFoundError):
        tmp_store.delete("nonexistent-id")


def test_list_empty(tmp_store):
    assert tmp_store.list() == []


def test_list_multiple(tmp_store):
    p1 = Problem(name="First")
    p2 = Problem(name="Second")
    tmp_store.save(p1)
    tmp_store.save(p2)
    listing = tmp_store.list()
    assert len(listing) == 2
    names = {item["name"] for item in listing}
    assert names == {"First", "Second"}


def test_list_scores_completeness(tmp_store):
    p = Problem(
        name="Partial",
        objectives=[Objective(name="Rev", direction="maximize")],
        options=[Option(name="A"), Option(name="B")],
        scores=[Score(option="A", objective="Rev", value=5.0)],
    )
    tmp_store.save(p)
    listing = tmp_store.list()
    assert listing[0]["status"]["scores_complete"] == 0.5

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "worker" / "src"))

import pytest
from safe_kernel import CellRejected, execute_cells


def test_cells_share_variables_within_one_reconstructed_page():
    results = execute_cells([
        "returns = [0.01, -0.02, 0.03]",
        "print(round(mean(returns), 4))",
    ])
    assert results == [
        {"ok": True, "output": ""},
        {"ok": True, "output": "0.0067\n"},
    ]


def test_disallows_import_and_attribute_access():
    assert not execute_cells(["import os"])[0]["ok"]
    assert not execute_cells(["(1).__class__"])[0]["ok"]


def test_loop_and_growth_bounds_are_enforced():
    result = execute_cells(["items = [1]\nfor i in range(100):\n    items = items + items"])
    assert result[0]["ok"] is False
    assert "Collection growth" in result[0]["output"]
    too_many = execute_cells(["for a in range(2):\n    for b in range(2):\n        for c in range(2):\n            print(c)"])
    assert too_many[0]["ok"] is False


def test_range_is_bounded_and_cells_are_limited():
    result = execute_cells(["values = range(101)"])
    assert result[0]["ok"] is False
    with pytest.raises(CellRejected):
        execute_cells(["print(1)"] * 13)

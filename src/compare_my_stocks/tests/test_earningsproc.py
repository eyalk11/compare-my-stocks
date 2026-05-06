"""Tests for EarningProcessor — the Seeking Alpha (RapidAPI) earnings path.

Covers:
- get_earnings_ttm: builds the right URL + querystring and forwards them to
  RapidApi.get_json.
- get_dfs: parses a minimal Seeking Alpha-shaped response into the (revenue,
  income) DataFrame pair, with the expected datetime index, ticker column,
  and value-False filtering.
"""
import datetime
from unittest.mock import MagicMock, patch

import pandas
import pytest

from transactions.earningsproc import EarningProcessor


def _make_processor():
    """Bypass __init__ so we don't need a real manager / config tree."""
    return EarningProcessor.__new__(EarningProcessor)


def test_get_earnings_ttm_calls_seekingalpha_with_expected_querystring():
    proc = _make_processor()
    sentinel = {"ok": True}
    proc.get_json = MagicMock(return_value=sentinel)

    out = proc.get_earnings_ttm("TSLA")

    assert out is sentinel
    proc.get_json.assert_called_once()
    qs, url = proc.get_json.call_args[0]
    assert url == "https://seeking-alpha.p.rapidapi.com/symbols/get-financials"
    assert qs == {
        "symbol": "TSLA",
        "target_currency": "USD",
        "period_type": "ttm",
        "statement_type": "income-statement",
    }


def _sample_response():
    """Minimal Seeking Alpha-shaped payload that get_dfs knows how to walk."""
    return [
        {}, {}, {}, {},
        {
            "rows": [
                {
                    "cells": [
                        {"name": "12 Months Mar 2023", "value": "50000", "raw_value": 50000},
                        {"name": "12 Months Mar 2024", "value": "60000", "raw_value": 60000},
                        {"name": "12 Months Mar 2025", "value": False,   "raw_value": 0},
                    ],
                },
                {
                    "cells": [
                        {"name": "12 Months Mar 2023", "value": "5000", "raw_value": 5000},
                        {"name": "12 Months Mar 2024", "value": "6000", "raw_value": 6000},
                    ],
                },
            ],
        },
    ]


def test_get_dfs_parses_response_into_two_dataframes():
    proc = _make_processor()
    proc.get_earnings_ttm = MagicMock(return_value=_sample_response())

    # avoid the 0.8s sleep inside get_dfs
    with patch("time.sleep"):
        revdf, incdf = proc.get_dfs("TSLA")

    # revenue df: value=False entry filtered out, leaving 2 rows
    assert list(revdf.columns) == ["TSLA"]
    assert len(revdf) == 2
    assert revdf.index.tolist() == [
        datetime.datetime(2023, 3, 1),
        datetime.datetime(2024, 3, 1),
    ]
    assert revdf["TSLA"].tolist() == [50000, 60000]

    # income df: 2 rows, both kept
    assert list(incdf.columns) == ["TSLA"]
    assert len(incdf) == 2
    assert incdf["TSLA"].tolist() == [5000, 6000]


def test_get_dfs_returns_empty_on_malformed_response():
    """get_dfs swallows parse errors and returns two empty DataFrames."""
    proc = _make_processor()
    proc.get_earnings_ttm = MagicMock(return_value={"unexpected": "shape"})

    with patch("time.sleep"):
        revdf, incdf = proc.get_dfs("TSLA")

    assert isinstance(revdf, pandas.DataFrame) and revdf.empty
    assert isinstance(incdf, pandas.DataFrame) and incdf.empty

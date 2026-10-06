"""The synthetic generator must stay out of the production import path."""

import importlib

import pytest


def test_synthetic_generator_is_archived():
    with pytest.raises(ImportError, match="archive/synthetic"):
        importlib.reload(importlib.import_module("data.synthetic"))

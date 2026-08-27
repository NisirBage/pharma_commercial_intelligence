import pytest

from app.optimization.demand_input import _selected_model_record


def test_missing_registry_record_raises_clear_error(tmp_path):
    with pytest.raises(ValueError, match="No M4 registry record"):
        _selected_model_record("NOT_A_REAL_CLASS", tmp_path)

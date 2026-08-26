from app.forecasting.registry import ModelRecord, dataset_version_hash, load_registry, now_iso, save_record


def _sample_record() -> ModelRecord:
    return ModelRecord(
        model_name="ets",
        atc_class="M01AB",
        training_period="2014-01-02/2019-06-01",
        validation_period="2019-06-02/2019-06-15",
        forecast_horizon=14,
        features=[],
        hyperparameters={"seasonal_period": 7},
        evaluation_metrics={"mae": 1.2, "wape": 15.0},
        trained_at=now_iso(),
        dataset_version_hash="abc123",
    )


def test_save_and_load_record_roundtrip(tmp_path):
    record = _sample_record()
    path = save_record(record, registry_dir=tmp_path)
    assert path.exists()

    loaded = load_registry(registry_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0]["model_name"] == "ets"
    assert loaded[0]["atc_class"] == "M01AB"
    assert loaded[0]["evaluation_metrics"]["wape"] == 15.0


def test_load_registry_empty_directory_returns_empty_list(tmp_path):
    assert load_registry(registry_dir=tmp_path / "does_not_exist") == []


def test_dataset_version_hash_is_deterministic_and_changes_with_data(raw_fixture_dir, tmp_path):
    hash_a = dataset_version_hash(raw_fixture_dir)
    hash_b = dataset_version_hash(raw_fixture_dir)
    assert hash_a == hash_b  # same input -> same hash, always

    # copy fixtures and mutate one file -> hash must change
    import shutil

    mutated_dir = tmp_path / "mutated"
    shutil.copytree(raw_fixture_dir, mutated_dir)
    content = (mutated_dir / "saleshourly.csv").read_text(encoding="utf-8")
    (mutated_dir / "saleshourly.csv").write_text(content.replace("1/1/2020 8:00,1,2,3,4,5,6,7,8", "1/1/2020 8:00,9,9,9,9,9,9,9,9"), encoding="utf-8")

    hash_mutated = dataset_version_hash(mutated_dir)
    assert hash_mutated != hash_a

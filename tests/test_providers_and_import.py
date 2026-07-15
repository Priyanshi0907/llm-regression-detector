import sys
import json
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.providers.registry import get_provider, SUPPORTED_PROVIDERS, default_model_for
from src.providers.mock_provider import MockProvider
from src.dataset_importer import parse_cases, import_dataset, DatasetImportError


def test_all_providers_have_default_models():
    for p in SUPPORTED_PROVIDERS:
        assert default_model_for(p), f"{p} has no default model"


def test_get_provider_falls_back_to_mock_without_keys():
    # In this test environment there's no real Anthropic/Gemini key set,
    # so the registry must return a working mock instead of raising.
    provider = get_provider("anthropic")
    assert provider.is_available()


def test_get_provider_rejects_unknown_name():
    try:
        get_provider("not-a-real-provider")
        assert False, "should have raised"
    except ValueError:
        pass


def test_mock_provider_distinguishes_by_name():
    # Different providers should produce different (but each internally
    # deterministic) mock confidence for the same input.
    p1 = MockProvider("openai")
    p2 = MockProvider("gemini")
    assert p1.bias != p2.bias


def test_import_valid_csv():
    with tempfile.TemporaryDirectory() as d:
        csv_path = Path(d) / "cases.csv"
        csv_path.write_text(
            "id,input,expected_category,expected_summary,expected_difficulty,notes\n"
            "T1,test email,billing,a billing issue,easy,\n"
        )
        cases = parse_cases(csv_path)
        assert len(cases) == 1
        assert cases[0].id == "T1"
        assert cases[0].expected_category.value == "billing"


def test_import_rejects_invalid_category():
    with tempfile.TemporaryDirectory() as d:
        csv_path = Path(d) / "cases.csv"
        csv_path.write_text(
            "id,input,expected_category,expected_summary,expected_difficulty,notes\n"
            "T1,test email,not_a_category,a summary,easy,\n"
        )
        try:
            parse_cases(csv_path)
            assert False, "should have raised"
        except DatasetImportError:
            pass


def test_import_rejects_duplicate_ids():
    with tempfile.TemporaryDirectory() as d:
        csv_path = Path(d) / "cases.csv"
        csv_path.write_text(
            "id,input,expected_category,expected_summary,expected_difficulty,notes\n"
            "T1,email one,billing,summary one,easy,\n"
            "T1,email two,technical,summary two,easy,\n"
        )
        try:
            parse_cases(csv_path)
            assert False, "should have raised"
        except DatasetImportError:
            pass


def test_import_and_merge():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        existing = d / "existing.json"
        existing.write_text(json.dumps({
            "dataset_version": "v1", "created": "x", "notes": "",
            "cases": [{
                "id": "TC001", "input": "old", "expected_category": "billing",
                "expected_summary": "old summary", "expected_difficulty": "easy", "notes": "",
            }],
        }))
        new_file = d / "new.csv"
        new_file.write_text(
            "id,input,expected_category,expected_summary,expected_difficulty,notes\n"
            "TC002,new email,technical,new summary,easy,\n"
        )
        output = d / "merged.json"
        summary = import_dataset(new_file, output, merge_with=existing)
        assert summary["total_cases"] == 2
        assert summary["added"] == 1
        assert output.exists()


if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

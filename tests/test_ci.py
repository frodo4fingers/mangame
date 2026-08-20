"""CI commands are part of the cross-platform contract."""

from pathlib import Path

CI = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text(
    encoding="utf-8"
)


def test_the_matrix_runs_pytest_with_its_selected_python() -> None:
    assert "uv run --locked --extra dev --python ${{ matrix.python }} python -m pytest -q" in CI
    assert "uv run pytest -q" not in CI


def test_the_wheel_smoke_does_not_need_a_qt_runtime() -> None:
    assert 'files("mangame").joinpath("assets", "emblems")' in CI
    assert "from mangame.ui import emblems" not in CI

"""Cross-cutting tests for error reporting and build dependencies."""

from __future__ import annotations

import importlib.util
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from helpers import build, copy_test_root, create_app, purge_modules
from sphinx.errors import SphinxError

from sphinxcontrib.prefect._render import note_source_dependency

FLOW_ROOT = Path(__file__).parent / "roots" / "test-flow"
DAG_ROOT = Path(__file__).parent / "roots" / "test-dag"


_PACKAGE_PREFIXES = ("fixture_pkg", "dag_pkg", "index_pkg")


@pytest.fixture(autouse=True)
def isolate_fixture_packages() -> Any:
    """Import fresh fixture packages from each temporary source tree."""
    purge_modules(*_PACKAGE_PREFIXES)
    yield
    purge_modules(*_PACKAGE_PREFIXES)


def hide_myst(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make MyST unavailable, whether or not the extra is installed."""
    if importlib.util.find_spec("myst_parser") is not None:
        monkeypatch.setattr(
            "sphinxcontrib.prefect._description._load_myst",
            lambda: None,
        )


def fail_description_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make reading ``description.rst`` raise an ``OSError``."""
    original = Path.read_text

    def read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if path.name == "description.rst":
            raise OSError("permission denied")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)


def apply_case_setup(
    case: FailureCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply the monkeypatches a failure case needs."""
    if case.hide_myst:
        hide_myst(monkeypatch)
    if case.read_error:
        fail_description_read(monkeypatch)


def assert_directive_location(text: str) -> None:
    """Assert that *text* starts a diagnostic at the directive's source line.

    Sphinx reports the test root's ``index.rst`` as ``index.rst.rst`` in this
    environment; accept either spelling but require the directive's line.
    """
    assert re.search(r"index\.rst(?:\.rst)?:4:", text)


@dataclass(frozen=True)
class FailureCase:
    """One recoverable failure path and the diagnostic it must produce."""

    name: str
    root: Path
    body: str
    message: str
    source: str | None = None
    config: str = ""
    hide_myst: bool = False
    read_error: bool = False


FAILURE_CASES = (
    FailureCase(
        "import-failure",
        FLOW_ROOT,
        "Broken\n======\n\n.. prefect-flow:: fixture_pkg.missing.main\n",
        "Could not import module",
    ),
    FailureCase(
        "missing-attribute",
        FLOW_ROOT,
        "Broken\n======\n\n.. prefect-flow:: fixture_pkg.flows.missing\n",
        "Could not find 'missing'",
        source="fixture_pkg/flows.py",
    ),
    FailureCase(
        "wrong-object-type",
        FLOW_ROOT,
        "Broken\n======\n\n.. prefect-flow:: fixture_pkg.flows.not_a_flow\n",
        "not a Prefect flow",
        source="fixture_pkg/flows.py",
    ),
    FailureCase(
        "malformed-marker",
        FLOW_ROOT,
        "Broken\n======\n\n.. prefect-flow:: fixture_pkg.flows.malformed_markers\n",
        "Malformed main-flow frontmatter",
        source="fixture_pkg/flows.py",
    ),
    FailureCase(
        "missing-description-file",
        FLOW_ROOT,
        "Broken\n======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: missing.rst\n",
        "Could not find description file",
        source="missing.rst",
    ),
    FailureCase(
        "unreadable-description-file",
        FLOW_ROOT,
        "Broken\n======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: description.rst\n",
        "Could not read description file",
        source="description.rst",
        read_error=True,
    ),
    FailureCase(
        "missing-myst-parser",
        FLOW_ROOT,
        "Broken\n======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: description.md\n",
        "sphinx-contrib-prefect[markdown]",
        source="description.md",
        hide_myst=True,
    ),
    FailureCase(
        "missing-dag-arguments",
        DAG_ROOT,
        "DAG\n===\n\n.. prefect-flow:: dag_pkg.flows.needs_arguments\n   :show-dag:\n",
        "requires sample arguments",
        source="dag_pkg/flows.py",
    ),
    FailureCase(
        "invalid-dag-arguments",
        DAG_ROOT,
        "DAG\n===\n\n.. prefect-flow:: dag_pkg.flows.needs_arguments\n   :show-dag:\n",
        "configured sample arguments do not match",
        source="dag_pkg/flows.py",
        config=(
            "prefect_dag_sample_args = "
            '{"dag_pkg.flows.needs_arguments": {"unknown": 1}}'
        ),
    ),
    FailureCase(
        "invalid-dag-argument-config",
        DAG_ROOT,
        "DAG\n===\n\n.. prefect-flow:: dag_pkg.flows.pipeline\n   :show-dag:\n",
        "prefect_dag_sample_args must be a mapping",
        source="dag_pkg/flows.py",
        config="prefect_dag_sample_args = []",
    ),
    FailureCase(
        "dag-execution-failure",
        DAG_ROOT,
        "DAG\n===\n\n"
        ".. prefect-flow:: dag_pkg.flows.unsupported_submit\n"
        "   :show-dag:\n",
        "Could not generate the runtime DAG",
        source="dag_pkg/flows.py",
    ),
    FailureCase(
        "dynamic-model",
        FLOW_ROOT,
        "Models\n======\n\n.. prefect-flow:: fixture_pkg.flows.with_dynamic_model\n",
        "not an importable class",
        source="fixture_pkg/flows.py",
    ),
    FailureCase(
        "pydantic-v1-model",
        FLOW_ROOT,
        "Models\n======\n\n.. prefect-flow:: fixture_pkg.legacy.legacy_flow\n",
        "uses Pydantic v1",
        source="fixture_pkg/legacy.py",
    ),
)


@pytest.mark.parametrize(
    "case", FAILURE_CASES, ids=[case.name for case in FAILURE_CASES]
)
def test_recoverable_failure_warns_and_continues(
    make_app: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: FailureCase,
) -> None:
    apply_case_setup(case, monkeypatch)
    src = copy_test_root(case.root, tmp_path, case.body, config=case.config)

    app = build(make_app, src)

    assert app.statuscode == 0
    warnings = app.warning.getvalue()
    assert case.message in warnings
    assert_directive_location(warnings)
    if case.source is not None:
        assert str(src / case.source) in warnings


@pytest.mark.parametrize(
    "case", FAILURE_CASES, ids=[case.name for case in FAILURE_CASES]
)
def test_recoverable_failure_raises_in_strict_mode(
    make_app: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: FailureCase,
) -> None:
    apply_case_setup(case, monkeypatch)
    config = f'{case.config}\nprefect_on_error = "error"'
    src = copy_test_root(case.root, tmp_path, case.body, config=config)
    app = create_app(make_app, src)

    with pytest.raises(SphinxError, match=re.escape(case.message)) as excinfo:
        app.build()

    error = str(excinfo.value)
    assert_directive_location(error)
    if case.source is not None:
        assert str(src / case.source) in error


class RecordingEnv:
    """Minimal environment that records dependency registrations."""

    def __init__(self) -> None:
        self.dependencies: list[str] = []

    def note_dependency(self, path: str) -> None:
        self.dependencies.append(path)


def test_note_source_dependency_falls_back_to_the_code_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def flow_body() -> None:
        pass

    monkeypatch.setattr(
        "sphinxcontrib.prefect._errors.inspect.getsourcefile",
        lambda *_: None,
    )
    directive = SimpleNamespace(env=RecordingEnv())

    note_source_dependency(directive, flow_body)  # type: ignore[arg-type]

    assert directive.env.dependencies == [flow_body.__code__.co_filename]


def test_note_source_dependency_registers_the_source_file() -> None:
    def flow_body() -> None:
        pass

    directive = SimpleNamespace(env=RecordingEnv())

    note_source_dependency(directive, flow_body)  # type: ignore[arg-type]

    assert directive.env.dependencies == [flow_body.__code__.co_filename]


def test_editing_flow_source_rebuilds_the_page(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = copy_test_root(
        FLOW_ROOT,
        tmp_path,
        "Rebuild\n=======\n\n.. prefect-flow:: fixture_pkg.flows.main\n",
    )
    first = build(make_app, src)
    assert "Run the main fixture flow." in (first.outdir / "index.html").read_text(
        encoding="utf-8"
    )

    flow_source = src / "fixture_pkg" / "flows.py"
    flow_source.write_text(
        flow_source.read_text(encoding="utf-8").replace(
            "Run the main fixture flow.",
            "Run the edited fixture flow.",
        ),
        encoding="utf-8",
    )
    # Force the dependency timestamp ahead of the document's recorded mtime.
    future = time.time() + 5
    os.utime(flow_source, (future, future))
    purge_modules(*_PACKAGE_PREFIXES)

    second = build(make_app, src)

    assert "Run the edited fixture flow." in (second.outdir / "index.html").read_text(
        encoding="utf-8"
    )


def test_editing_an_external_description_rebuilds_the_page(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = copy_test_root(
        FLOW_ROOT,
        tmp_path,
        "Rebuild\n=======\n\n"
        ".. prefect-flow:: fixture_pkg.flows.main\n"
        "   :description-from: description.rst\n",
    )
    first = build(make_app, src)
    assert "This description comes from an external <em>file</em>." in (
        first.outdir / "index.html"
    ).read_text(encoding="utf-8")

    description = src / "description.rst"
    description.write_text(
        "This description was edited.\n",
        encoding="utf-8",
    )
    future = time.time() + 5
    os.utime(description, (future, future))

    second = build(make_app, src)

    assert "This description was edited." in (second.outdir / "index.html").read_text(
        encoding="utf-8"
    )


def test_model_deduplication_does_not_leak_between_builds(
    make_app: Any,
    tmp_path: Path,
) -> None:
    src = copy_test_root(
        FLOW_ROOT,
        tmp_path,
        "Models\n======\n\n.. prefect-flow:: fixture_pkg.flows.with_parameters\n",
    )
    first = build(make_app, src)
    assert 'id="fixture_pkg.models.Profile"' in (first.outdir / "index.html").read_text(
        encoding="utf-8"
    )

    second = make_app(
        "html",
        srcdir=src,
        builddir=src / "_build_second",
        warningiserror=False,
    )
    second.build()

    assert "duplicate" not in second.warning.getvalue().lower()
    assert 'id="fixture_pkg.models.Profile"' in (
        second.outdir / "index.html"
    ).read_text(encoding="utf-8")

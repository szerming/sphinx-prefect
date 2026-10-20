# Release checklist

This checklist covers a `sphinx-contrib-prefect` release. Publishing to PyPI is
a **human step**: it needs maintainer credentials and cannot be performed by
CI.

## 1. Prepare the release

- Confirm the supported version ranges in `pyproject.toml` match the
  [specification's compatibility matrix](specs/0001-sphinx-prefect-v0.1.md#8-compatibility).
- Move the entries under `Unreleased` in [`CHANGELOG.md`](https://github.com/szerming/sphinx-prefect/blob/main/CHANGELOG.md)
  into a new version section and add the release date.
- Bump `__version__` in `src/sphinxcontrib/prefect/__init__.py`. Hatchling reads
  the version from that file, so no other version declaration exists.
- Update the status line and any version-specific wording in
  [`README.md`](https://github.com/szerming/sphinx-prefect/blob/main/README.md)
  and the [usage guide](guide.md).

## 2. Run the release checks

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run sphinx-build -W -b html docs docs/_build/html
uv run sphinx-build -W -b html examples/demo examples/demo/_build/html
uv build
```

`uv build` writes both a wheel and an sdist to `dist/`. Verify their contents:

```bash
uv run python -m zipfile -l dist/sphinx_contrib_prefect-*.whl
tar -tzf dist/sphinx_contrib_prefect-*.tar.gz
```

The wheel must contain `sphinxcontrib/prefect/` and must not contain
`sphinxcontrib/__init__.py`: `sphinxcontrib` is a PEP 420 namespace package.
The wheel metadata must declare the Python, Sphinx, Prefect, Pydantic, PyYAML,
`sphinxcontrib-mermaid`, and `sphinxcontrib-pydantic` ranges, the MIT license,
and the classifiers from `pyproject.toml`.

Install the wheel into a clean environment and build the example once more:

```bash
uv venv /tmp/sphinx-contrib-prefect-release
uv pip install --python /tmp/sphinx-contrib-prefect-release/bin/python dist/sphinx_contrib_prefect-*.whl
/tmp/sphinx-contrib-prefect-release/bin/python -m sphinx -W -b html \
  examples/demo /tmp/sphinx-contrib-prefect-release/example
```

## 3. Commit and tag

```bash
git add CHANGELOG.md src/sphinxcontrib/prefect/__init__.py
git commit -m "Release vX.Y.Z"
git tag -a vX.Y.Z -m "sphinx-contrib-prefect vX.Y.Z"
git push origin main
git push origin vX.Y.Z
```

## 4. Upload to PyPI (human step)

A maintainer with PyPI credentials performs the upload. CI, agents, and
contributors must not publish on their own.

```bash
uv publish
```

Alternatively, use `twine upload dist/*`. Upload from the tagged commit so the
artifacts match the tag.

## 5. Verify the published release

```bash
uv venv /tmp/sphinx-contrib-prefect-verify
uv pip install --python /tmp/sphinx-contrib-prefect-verify/bin/python \
  "sphinx-contrib-prefect==X.Y.Z"
/tmp/sphinx-contrib-prefect-verify/bin/python -m sphinx -W -b html \
  examples/demo /tmp/sphinx-contrib-prefect-verify/example
```

Check that the PyPI project page shows the expected description, license,
classifiers, and links. Create a GitHub release from the tag with the changelog
section as its notes.

## 6. After the release

- Confirm the CI badge and the docs build remain green on `main`.
- Open a new `Unreleased` section in `CHANGELOG.md` and bump the development
  version only when the next release starts.

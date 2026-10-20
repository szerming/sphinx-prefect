# Changelog

All notable changes to `sphinx-contrib-prefect` are documented in this file.
The project follows [Semantic Versioning](https://semver.org/) and
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- `prefect-flow`, `prefect-params`, `prefect-dag`, and `prefect-flow-index`
  directives.
- Flow metadata, reStructuredText docstring descriptions, and external RST or
  MyST Markdown descriptions selected with `:description-from:`.
- Scalar parameter tables and `sphinxcontrib-pydantic` model documentation for
  nested, recursive, and root-model parameters.
- Runtime Mermaid flow graphs from Prefect's visualization tracker, with
  `:show-dag:`, `:no-dag:`, `prefect_dag_enabled`, and
  `prefect_dag_sample_args`.
- Subflow, task, and unknown-node sections with stable entrypoint anchors and
  cross-reference links.
- Main-flow docstring markers (`@mainflow`, YAML frontmatter, and `:mainflow:`)
  and module scanning for `prefect-flow-index`.
- A `prefect_on_error` warn/error policy, source-located diagnostics,
  `env.note_dependency()` rebuild tracking, and parallel-safety metadata.
- A buildable example project under `examples/demo`.
- Documentation, a release checklist, package classifiers, and CI jobs that
  build the docs and example and verify wheel contents.
- A manually triggered `Publish to PyPI` workflow that reruns the checks and
  requires approval in the protected `pypi` environment before publishing with
  trusted publishing.

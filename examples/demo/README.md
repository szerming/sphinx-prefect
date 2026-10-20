# sphinx-contrib-prefect demo

A Sphinx project that exercises every directive in `sphinx-contrib-prefect`:

- `index.rst` uses `prefect-flow-index` to discover three main flows from
  `demo.flows`. The flows demonstrate the `@mainflow` line, YAML frontmatter,
  and `:mainflow:` field marker forms.
- `standalone.rst` uses `prefect-flow` with `:show-dag:` to render the nested
  `ReportConfig` model, the parameter table, the runtime graph, and the
  observed subflow and task sections.
- `variants.rst` uses `prefect-params` and `prefect-dag` directly.

Build it from this directory:

```bash
uv run --project ../.. sphinx-build -W -b html . _build/html
```

Open `_build/html/index.html` to inspect the result. Graph generation executes
the flow body; `prefect_dag_sample_args` in `conf.py` supplies the required
`ReportConfig` value.

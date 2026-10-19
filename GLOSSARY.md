# sphinx-contrib-prefect

A Sphinx extension that documents Prefect flows, their parameters, and the tasks and subflows observed in a flow graph.

## Language

**Main Flow**:
A flow selected as a documentation root, either explicitly or through a main-flow marker during a module scan.
_Avoid_: Entry flow, root flow, parent flow

**Subflow**:
A flow invoked from inside another flow.
_Avoid_: Child flow, nested flow

**Task**:
A unit of work invoked by a flow and decorated with Prefect's task decorator.
_Avoid_: Step, job, operation

**Flow Graph**:
The directed graph observed during one sample execution of a flow, rendered as Mermaid.
_Avoid_: Pipeline, DAG (except when quoting Prefect), workflow

**Flow Entrypoint**:
The importable `module.qualname` path that identifies a flow object.
_Avoid_: Flow address, object path

**Main-Flow Marker**:
Docstring metadata that marks a flow for selection during a module scan.
_Avoid_: Main annotation, magic string

**External Description**:
A flow description read from a file selected with `:description-from:`,
instead of from the flow docstring.
_Avoid_: Override description, file docstring

**Module Scan**:
Importing configured Python modules and inspecting their flow objects to find marked main flows.
_Avoid_: Auto-discovery, flow crawl

**Runtime DAG**:
A flow graph produced by executing a flow under Prefect's visualization tracker.
_Avoid_: Live DAG, execution DAG

**Static Analysis**:
Deriving a flow graph from source or object structure without executing the flow.
_Avoid_: Offline analysis (ambiguous; see Offline)

**Parameter Table**:
A generated table of a flow's or task's parameters, showing names, types,
requiredness, defaults, and descriptions.
_Avoid_: Signature table, arguments table

**Pydantic Model Documentation**:
Rendered documentation for a Pydantic model used as a flow or task parameter.
_Avoid_: Model spec, schema docs

**Unknown Node**:
A graph node that cannot be matched to a flow or task object in the scanned modules.
_Avoid_: External node (unless it is known to be external)

**Offline**:
Operating without a Prefect server or network access. Offline does not imply that no user code executes.
_Avoid_: Side-effect-free

**Side-Effect-Free**:
Not executing user flow or task code during documentation generation.
_Avoid_: Offline

**Sample Arguments**:
Values supplied to a flow so a runtime DAG can execute it.
_Avoid_: Test inputs, dummy args

**Cross-Reference**:
A link from a documented flow or task mention to its generated section.
_Avoid_: Backlink, hyperlink

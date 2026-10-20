Directive variants
==================

``prefect-params`` renders the flow's metadata, parameter table, and Pydantic
model blocks without the description or a runtime graph:

.. prefect-params:: demo.flows.health_check

``prefect-dag`` always attempts runtime graph generation and renders the graph
plus the subflow and task sections it observes, without the flow description or
parameter table:

.. prefect-dag:: demo.flows.weekly_digest

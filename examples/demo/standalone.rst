Standalone flow page
====================

The ``prefect-flow`` directive documents one flow by entrypoint. Here
``:show-dag:`` opts into runtime graph generation and uses the sample arguments
configured in ``conf.py``. The graph executes the flow body, so this page
demonstrates the side effects documented in the usage guide.

.. prefect-flow:: demo.flows.build_report
   :show-dag:

   The flow description, parameter table, nested ``ReportConfig`` model, graph,
   subflows, and tasks are all generated from the flow object.

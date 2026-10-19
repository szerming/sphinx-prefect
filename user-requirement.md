# sphinx contrib for documenting prefect flow
I want to write a sphinx contrib to document prefect flow.
It is able to generate documents from the main workflow, and tracing from the main flow, 
discover the subflows and tasks.

As part of discovery, for the purpose of document generation, it will
- Generate a full description and purpose for the main flow - this can either be extract from the doc string, of - to be discussed - combined from other sources.
- Using build in prefect DAG generation, to generate the mermaid diagram for the flow graph
- document all flows and subflows, from their docstrings and parameters, 
- and if the parameters are pydantic models, generate their full description for the models

# How to identify main flow
Prefect does not have a native way to identify main flow - this is to be discussed. I think this can be either
from a specified namespace, e.g. prefect.flows.main, to discover all @flow, or 
from a predefined annotation, like @mainflow; or through some magic string in the docstring of the @flow function.

# Source for the full description
The full description for the main flow should allow markdown like rich input: I am thinking
maybe pulling from the docstring for the main flow is good enough, however, I am also concern that if it is a lengthy documentation, i.e. to document a complex flow, 
then putting it there might degrade the code readability.

# Generating DAG
I am thinking of using the already good mermaid generation that Prefect already has.

# Output
This should be a sphinx contrib extension.



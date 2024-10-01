import click
import pathlib

from openff.evaluator import unit
from openff.evaluator.properties import Density, EnthalpyOfMixing
from openff.evaluator.client import RequestOptions


def modify_workflow_schema(original_schema):
    """
    Modify a schema to run faster for testing.
    """
    workflow_schema = original_schema.workflow_schema
    new_workflow_schema = []
    for schema in workflow_schema.protocol_schemas:
        if "simulation" in schema.id:
            protocol = schema.to_protocol()
            protocol.steps_per_iteration = 10000000
            schema = protocol.schema

        if schema.id == "conditional_group":
            protocol = schema.to_protocol()
            simulation_protocol = protocol.protocols["production_simulation"]
            simulation_protocol.steps_per_iteration = 10000000
            schema = protocol.schema

        if schema.id == "conditional_group_mixture":
            protocol = schema.to_protocol()
            simulation_protocol = protocol.protocols["production_simulation_mixture"]
            simulation_protocol.steps_per_iteration = 10000000
            schema = protocol.schema

        if schema.id == "conditional_group_component_$(component_replicator)":
            protocol = schema.to_protocol()
            simulation_protocol = protocol.protocols["production_simulation_component_$(component_replicator)"]
            simulation_protocol.steps_per_iteration = 10000000
            schema = protocol.schema
        
        new_workflow_schema.append(schema)

    workflow_schema.protocol_schemas = new_workflow_schema
    workflow_schema.replace_protocol_types(
        {"BaseBuildSystem": "BuildSmirnoffSystem"},
    )
    original_schema.workflow_schema = workflow_schema
    return original_schema

@click.command()
@click.option(
    "--output-file",
    type=str,
    default="options.json",
    help="The output file for the options",
)
def main(
    output_file: str = "options.json",
):
    estimation_options = RequestOptions()
    estimation_options.calculation_layers = ["SimulationLayer"]
    density_schema = Density.default_simulation_schema(n_molecules=1000)
    density_schema = modify_workflow_schema(density_schema)
    estimation_options.add_schema(
        "SimulationLayer", Density, density_schema
    )

    enthalpy_schema = EnthalpyOfMixing.default_simulation_schema(n_molecules=1000)
    enthalpy_schema = modify_workflow_schema(enthalpy_schema)
    estimation_options.add_schema(
        "SimulationLayer", EnthalpyOfMixing, enthalpy_schema
    )
    print(type(estimation_options))
    pathlib.Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as file:
        file.write(estimation_options.json())


if __name__ == "__main__":
    main()

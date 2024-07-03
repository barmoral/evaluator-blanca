
"""
Evaluator workflow to Load and Filter Data Sets, Estimate Data Sets, Analyze Data Sets
Applied to calculations of Heats of Mixing.
"""

# Core Imports & Setup

import os
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

import logging
logging.getLogger("openff.toolkit").setLevel(logging.ERROR)

from openff import toolkit, evaluator

from openff.units import unit

# 0) Registering Custom ThermoML Property of Osmotic Coefficient
from openff.evaluator import properties
from openff.evaluator.datasets.thermoml import thermoml_property
from openff.evaluator.datasets import PhysicalProperty, PropertyPhase

@thermoml_property("Osmotic coefficient", supported_phases=PropertyPhase.Liquid)
class OsmoticCoefficient(PhysicalProperty):
    """A class representation of a osmotic coeff property"""

    @classmethod
    def default_unit(cls):
        return unit.dimensionless
    
...

custom_thermoml_props = [
    OsmoticCoefficient,
]

for custom_prop_cls in custom_thermoml_props:    
    setattr(properties, custom_prop_cls.__name__, custom_prop_cls)

# 1) Loading data sets

## Extracting Data from ThermoML or json file 
from openff.evaluator.datasets import PhysicalProperty, PropertyPhase, PhysicalPropertyDataSet
from openff.evaluator.datasets.thermoml import thermoml_property, ThermoMLDataSet

data_set_initial = PhysicalPropertyDataSet.from_json("training-properties-with-water.json")

## Filtering data sets
from openff.evaluator.datasets.curation.components.filtering import FilterByPropertyTypes, FilterByPropertyTypesSchema

data_set_hmix= FilterByPropertyTypes.apply(
    data_set_initial, FilterByPropertyTypesSchema(property_types=["EnthalpyOfMixing"]))

## Saving filtered data set to json file
data_set_path = Path('filtered_dataset_hmix.json')
data_set_hmix.json(data_set_path, format=True)

# 2) Estimating data sets

## Loading data set and applying FF parameters
from openff.evaluator.forcefield import SmirnoffForceFieldSource

### load data
data_set_path = Path('filtered_dataset_hmix.json')
data_set = PhysicalPropertyDataSet.from_json(data_set_path)

### load FF
ff_path = "openff-2.0.0.offxml"
force_field_source = SmirnoffForceFieldSource.from_path(ff_path)

## Defining calculation Schemas
from openff.evaluator.properties import Density, EnthalpyOfMixing
from openff.evaluator.client import RequestOptions

### density_schema = Density.default_simulation_schema(n_molecules=256)
h_mix_schema = EnthalpyOfMixing.default_simulation_schema(n_molecules=256)

### Create an options object which defines how the data set should be estimated.
estimation_options = RequestOptions()

### Specify that we only wish to use molecular simulation to estimate the data set.
estimation_options.calculation_layers = ["SimulationLayer"]

### Add our custom schemas, specifying that the should be used by the 'SimulationLayer' estimation_options.add_schema("SimulationLayer", "Density", density_schema)
estimation_options.add_schema("SimulationLayer", "EnthalpyOfMixing", h_mix_schema)

## Launching a Server and Client
from openff.evaluator.backends import ComputeResources
from openff.evaluator.backends.dask import DaskLocalCluster
from openff.evaluator.server import EvaluatorServer
from openff.evaluator.client import EvaluatorClient
from openff.evaluator.client import ConnectionOptions

### define client to submit queries
port = 8119
evaluator_client = EvaluatorClient(ConnectionOptions(server_port=port))

### define available / preferred resources
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
resources = ComputeResources(
    number_of_threads=1,
    number_of_gpus=1,
    preferred_gpu_toolkit=ComputeResources.GPUToolkit.CUDA,
)

with DaskLocalCluster(number_of_workers=1, resources_per_worker=resources) as calculation_backend:
    ### spin up server
    evaluator_server = EvaluatorServer(calculation_backend=calculation_backend, delete_working_files=False, port=port)
    evaluator_server.start(asynchronous=True)

    ### estimate data set by submitting calculation schemas to newly-created server
    request, exception = evaluator_client.request_estimate(
        property_set=data_set,
        force_field_source=force_field_source,
        options=estimation_options,
    )

    ### Wait for the results.
    results, exception = request.results(synchronous=True, polling_interval=30)
    assert exception is None

    a = results.estimated_properties.json("estimated_dataset_hmix.json", format=True)
    print(a)

    # 3) Analysing data sets
    

"""
Evaluator workflow to Load and Filter Data Sets, Estimate Data Sets, Analyze Data Sets
Applied to calculations of Heats of Mixing and Density of Water.
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

data_set_hmix_dens= FilterByPropertyTypes.apply(
    data_set_initial, FilterByPropertyTypesSchema(property_types=["EnthalpyOfMixing","Density"]))

## Saving filtered data set to json file
data_set_path = Path('filtered_dataset_hmix_dens.json')
data_set_hmix_dens.json(data_set_path, format=True)

# 2) Estimating data sets

## Loading data set and applying FF parameters
from openff.evaluator.forcefield import SmirnoffForceFieldSource

### load data
data_set_path = Path('filtered_dataset_hmix_dens.json')
data_set = PhysicalPropertyDataSet.from_json(data_set_path)

### load FF
ff_path = "openff-2.0.0.offxml"
force_field_source = SmirnoffForceFieldSource.from_path(ff_path)

## Defining calculation Schemas
from openff.evaluator.properties import Density, EnthalpyOfMixing
from openff.evaluator.client import RequestOptions

### density_schema = Density.default_simulation_schema(n_molecules=256)
density_schema = Density.default_simulation_schema(n_molecules=256)
h_mix_schema = EnthalpyOfMixing.default_simulation_schema(n_molecules=256)

### Create an options object which defines how the data set should be estimated.
estimation_options = RequestOptions()

### Specify that we only wish to use molecular simulation to estimate the data set.
estimation_options.calculation_layers = ["SimulationLayer"]

### Add our custom schemas, specifying that the should be used by the 'SimulationLayer' estimation_options.add_schema("SimulationLayer", "Density", density_schema)
estimation_options.add_schema("SimulationLayer", "Density", density_schema)
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

    a = results.estimated_properties.json("estimated_dataset_hmix_dens.json", format=True)
    print(a)

 # 3) Analysing data sets
    
## Loading the data sets
experimental_data_set_path = "filtered_dataset_hmix_dens.json"
estimated_data_set_path = "estimated_dataset_hmix_dens.json"

experimental_data_set = PhysicalPropertyDataSet.from_json(experimental_data_set_path)
estimated_data_set = PhysicalPropertyDataSet.from_json(estimated_data_set_path)

## Extracting the results
properties_by_type = {
    "Density": [],
    "EnthalpyOfMixing": []
}

for experimental_property in experimental_data_set:
    ### Find the estimated property which has the same id as the
    ### experimental property.
    estimated_property = next(
        x for x in estimated_data_set if x.id == experimental_property.id
    )
    ### Add this pair of properties to the list of pairs
    property_type = experimental_property.__class__.__name__
    properties_by_type[property_type].append((experimental_property, estimated_property))

## Plotting the results
from matplotlib import pyplot

#### Create the figure we will plot to.
figure, axes = pyplot.subplots(nrows=1, ncols=2, figsize=(8.0, 4.0))

### Set the axis titles
axes[0].set_xlabel('OpenFF 1.0.0')
axes[0].set_ylabel('Experimental')
axes[0].set_title('Density $kg m^{-3}$')

axes[1].set_xlabel('OpenFF 1.0.0')
axes[1].set_ylabel('Experimental')
axes[1].set_title('$H_{vap}$ $kJ mol^{-1}$')

### Define the preferred units of the properties


preferred_units = {
    "Density": unit.kilogram / unit.meter ** 3,
    "EnthalpyOfVaporization": unit.kilojoule / unit.mole
}

for index, property_type in enumerate(properties_by_type):

    experimental_values = []
    estimated_values = []

    preferred_unit = preferred_units[property_type]

    ### Convert the values of our properties to the preferred units.
    for experimental_property, estimated_property in properties_by_type[property_type]:

        experimental_values.append(
            experimental_property.value.to(preferred_unit).magnitude
        )
        estimated_values.append(
            estimated_property.value.to(preferred_unit).magnitude
        )

    axes[index].plot(
        estimated_values, experimental_values, marker='x', linestyle='None'
    )

figure.savefig('hmix_dens_calcs.png')
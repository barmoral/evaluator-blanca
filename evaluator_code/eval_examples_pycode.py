#Core Imports and Setup
import os
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

import logging
logging.getLogger("openff.toolkit").setLevel(logging.ERROR)

from openff import toolkit, evaluator

####################################################################################

# 0) Registering Custom ThermoML Properties
from openff.units import unit
from openff.evaluator import properties
from openff.evaluator.datasets.thermoml import thermoml_property
from openff.evaluator.datasets import PhysicalProperty, PropertyPhase

@thermoml_property("Osmotic coefficient", supported_phases=PropertyPhase.Liquid)
class OsmoticCoefficient(PhysicalProperty):
    """A class representation of a osmotic coeff property"""

    @classmethod
    def default_unit(cls):
        return unit.dimensionless


custom_thermoml_props = [
    OsmoticCoefficient,
]

for custom_prop_cls in custom_thermoml_props:    
    setattr(properties, custom_prop_cls.__name__, custom_prop_cls)

####################################################################################

# 1) - Loading ThermoML Data Sets

from openff.evaluator.datasets import PhysicalProperty, PropertyPhase
from openff.evaluator.datasets.thermoml import thermoml_property
from openff.units import unit
from openff.evaluator.datasets.thermoml import ThermoMLDataSet

# 1.1) Extracting Data from ThermoML
data_set = ThermoMLDataSet.from_doi( # defaults from exaple notebook
    "10.1016/j.fluid.2013.10.034",
    "10.1021/je1013476",
)

# 1.2) Filtering data set
from openff.evaluator.datasets.curation.components.filtering import FilterByPropertyTypes, FilterByPropertyTypesSchema
from openff.evaluator.datasets.curation.components.filtering import FilterByTemperature, FilterByTemperatureSchema
from openff.evaluator.datasets.curation.components.filtering import FilterByPressure, FilterByPressureSchema
from openff.evaluator.datasets.curation.components.filtering import FilterBySmiles, FilterBySmilesSchema

    ## Property
data_set = FilterByPropertyTypes.apply(
    data_set, FilterByPropertyTypesSchema(property_types=["Density"])
)

    ## Temperature
data_set = FilterByTemperature.apply(
    data_set, FilterByTemperatureSchema(minimum_temperature=298.0, maximum_temperature=330.0)
)

    ## Pressure
data_set = FilterByPressure.apply(
    data_set, FilterByPressureSchema(minimum_pressure=100.0, maximum_pressure=101.426)
)

    ## Solvent
data_set = FilterBySmiles.apply(
    data_set, FilterBySmilesSchema(smiles_to_include=["CCO", "CC(C)O"])
)

print("Length of data set after filtering = ",len(data_set))

# 1.3) Build pandas dataframe from filtered data set

pandas_data_set = data_set.to_pandas()
pandas_data_set[
    [
        "Temperature (K)",
        "Pressure (kPa)",
        "Component 1",
        "Density Value (g / ml)",
        "Source",
    ]
].head()

# 1.4) Adding extra data

    # 1.4.1) Defining new properties
from openff.evaluator.datasets import MeasurementSource, PropertyPhase
from openff.evaluator.substances import Substance
from openff.evaluator.thermodynamics import ThermodynamicState
from openff.evaluator.properties import EnthalpyOfVaporization
from openff.units import unit

        ## define thermo state
thermodynamic_state = ThermodynamicState(
    temperature=298.15 * unit.kelvin, pressure=1.0 * unit.atmosphere
)

        ## define compounds 
ethanol = Substance.from_components("CCO")
isopropanol = Substance.from_components("CC(C)O")

        ## define source of measurements
source = MeasurementSource(doi="10.1016/S0021-9614(71)80108-8")

        ## define measurement values
ethanol_hvap = EnthalpyOfVaporization(
    thermodynamic_state=thermodynamic_state,
    phase=PropertyPhase.Liquid | PropertyPhase.Gas,
    substance=ethanol,
    value=42.26 * unit.kilojoule / unit.mole,
    uncertainty=0.02 * unit.kilojoule / unit.mole,
    source=source,
)
isopropanol_hvap = EnthalpyOfVaporization(
    thermodynamic_state=thermodynamic_state,
    phase=PropertyPhase.Liquid | PropertyPhase.Gas,
    substance=isopropanol,
    value=45.34 * unit.kilojoule / unit.mole,
    uncertainty=0.02 * unit.kilojoule / unit.mole,
    source=source,
)
data_set.add_properties(ethanol_hvap, isopropanol_hvap)

    # 1.4.2) Inspecting and saving new properties
        ## save for future use
data_set_path = Path('filtered_dataset_pycode.json')
data_set.json(data_set_path, format=True)

        ## inspect new properties
pandas_data_set = data_set.to_pandas()
pandas_data_set

####################################################################################

# 2) Estimating Data Sets 

# 2.1) Loading data set and FF parameters
from openff.evaluator.datasets import PhysicalPropertyDataSet
from openff.evaluator.forcefield import SmirnoffForceFieldSource

    ## load data
data_set_path = Path('filtered_dataset_pycode.json')
data_set = PhysicalPropertyDataSet.from_json(data_set_path)

    ## load FF
force_field_path = "openff-1.0.0.offxml"
force_field_source = SmirnoffForceFieldSource.from_path(force_field_path)

# 2.2) Defining Calculation Schemas
from openff.evaluator.properties import Density, EnthalpyOfVaporization
from openff.evaluator.client import RequestOptions

density_schema = Density.default_simulation_schema(n_molecules=256)
h_vap_schema = EnthalpyOfVaporization.default_simulation_schema(n_molecules=256)

    ## Create an options object which defines how the data set should be estimated.
estimation_options = RequestOptions()

    ## Specify that we only wish to use molecular simulation to estimate the data set.
estimation_options.calculation_layers = ["SimulationLayer"]

    ## Add our custom schemas, specifying that the should be used by the 'SimulationLayer'
estimation_options.add_schema("SimulationLayer", "Density", density_schema)
estimation_options.add_schema("SimulationLayer", "EnthalpyOfVaporization", h_vap_schema)


# 3) Launching a Server and Client
from openff.evaluator.backends import ComputeResources
from openff.evaluator.backends.dask import DaskLocalCluster
from openff.evaluator.server import EvaluatorServer
from openff.evaluator.client import EvaluatorClient

    # define client to submit queries
evaluator_client = EvaluatorClient()

    # define available / preferred resources
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
resources = ComputeResources(
    number_of_threads=1,
    number_of_gpus=1,
    preferred_gpu_toolkit=ComputeResources.GPUToolkit.CUDA,
)

with DaskLocalCluster(number_of_workers=1, resources_per_worker=resources) as calculation_backend:
    # spin up server
    evaluator_server = EvaluatorServer(calculation_backend=calculation_backend)
    evaluator_server.start(asynchronous=True)

    # estimate data set by submitting calculation schemas to newly-created server
    request, exception = evaluator_client.request_estimate(
        property_set=data_set,
        force_field_source=force_field_source,
        options=estimation_options,
    )

    # Wait for the results.
    results, exception = request.results(synchronous=True, polling_interval=30)
    assert exception is None

a = results.estimated_properties.json("estimated_dataset_pycode.json", format=True)

#SanityCheck
print("It works")
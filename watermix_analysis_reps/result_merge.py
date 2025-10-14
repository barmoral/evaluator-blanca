import json
from pathlib import Path

force_field='Sage2.3.0'
water_model_dir='OPC3'
import json

for i in range(1,4,1):
    # List of input files
    input_files = [
        f"{force_field}/{water_model_dir}/rep-{i}/results-worker0.json",
        f"{force_field}/{water_model_dir}/rep-{i}/results-worker1.json",
        f"{force_field}/{water_model_dir}/rep-{i}/results-worker2.json"
    ]

    # Initialize merged structure
    merged_result = None

    # Loop through each file
    for file_path in input_files:
        with open(file_path, "r") as f:
            data = json.load(f)

        if merged_result is None:
            # Initialize with the structure from the first file
            merged_result = data
        else:
            # Append properties to the merged result
            merged_result["estimated_properties"]["properties"].extend(
                data["estimated_properties"]["properties"]
            )

    # Output file
    with open(f"{force_field}/{water_model_dir}/results-r{i}.json", "w") as f:
        json.dump(merged_result, f, indent=2)

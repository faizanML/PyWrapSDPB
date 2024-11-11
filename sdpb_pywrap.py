# SDP Solver Pipeline

#This notebook provides a pipeline to run SDP using Docker and process the results.

# Import necessary libraries
import subprocess
import os
import shutil
import re
import numpy as np
import json


base_path = os.getcwd()
#THIS GENERATES THE JSON FILE INPUT FOR SDPB 

def convert_to_strings(data):
    """Recursively convert all numeric values in a nested structure to strings."""
    if isinstance(data, list):
        return [convert_to_strings(item) for item in data]  # Recursion for lists
    elif isinstance(data, (int, float)):
        return str(data)  # Convert numbers to strings
    return data  # Return other types (like str) unchanged

def generate_json_file(objective, normalization, pols_array, input_json):
    json_file_path = os.path.join(base_path, input_json)
    damped_rational_base = "0.3678794411"
    damped_rational_constant = "1"
    poles = []

    objective_str = convert_to_strings(objective)
    normalization_str = convert_to_strings(normalization)
    pols_array_str = convert_to_strings(pols_array)

    pmp_data = {
        "objective": objective_str,
        "normalization": normalization_str,
        "PositiveMatrixWithPrefactorArray":
        [   {"DampedRational": {
        "base": damped_rational_base,
        "constant": damped_rational_constant,
        "poles": poles},
        "polynomials": polynomials
            } for polynomials in pols_array_str] }
    
    with open(json_file_path, 'w') as f:
        json.dump(pmp_data, f, indent=4)


#THIS SECTION FOR SDP TO TAKE IN THE JSON FILE AND RUN 
# Define utility functions
def delete_directories(directories_to_delete):
    for directory in directories_to_delete:
        dir_path = os.path.join(base_path, directory)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)

def run_pmp2sdp(input_json, sdp_dir, procs, prec):
    pmp2sdp_command = [
        "docker", "run", "-v", f"{base_path}:/usr/local/share/sdpb",
        "bootstrapcollaboration/sdpb:master", 
        "mpirun", "--allow-run-as-root", "-n", str(procs),  # Use p processes
        "pmp2sdp", "--precision", str(prec),
        "-i", f"/usr/local/share/sdpb/{input_json}",
        "-o", f"/usr/local/share/sdpb/{sdp_dir}"
    ]
    # Set number of threads per process using environment variable
    subprocess.run(pmp2sdp_command)

def run_sdpb(sdp_dir, procs, prec):
    sdpb_command = [
        "docker", "run", "-v", f"{base_path}:/usr/local/share/sdpb",
        "bootstrapcollaboration/sdpb:master", 
        "mpirun", "--allow-run-as-root", "-n", str(procs),  # Use p processes
        "sdpb", f"--precision={prec}",
        "-s", f"/usr/local/share/sdpb/{sdp_dir}"
    ]
    # Set number of threads per process using environment variable
    subprocess.run(sdpb_command)


def read_primal_objective(output_file_path):
    pObj = None
    with open(output_file_path, 'r') as f:
        content = f.read()
        match = re.search(r"primalObjective = ([\-\d\.e]+);", content)
        if match:
            pObj = np.float64(match.group(1))
    return pObj

def read_solution(solution_file_path):
    with open(solution_file_path, 'r') as f:
        lines = f.readlines()[1:]  # Skip the first line
    pSol = np.array([np.float64(line.strip()) for line in lines])
    return pSol

# Cell 3: Define the main function
def sdpb_run(procs, prec, objective, normalization, pols_array):
    input_json = "pmp_input.json"
    sdp_dir = "sdp"
    output_path = "sdp_out"
    ck_path =  "sdp.ck"
    directories_to_delete = [sdp_dir, output_path, ck_path]

    generate_json_file(objective, normalization, pols_array, input_json)
    
    # Step 0: Delete previous directories
    delete_directories(directories_to_delete)
    
    # Step 1: Run pmp2sdp
    run_pmp2sdp(input_json, sdp_dir, procs, prec)
    
    # Step 2: Run SDPB
    run_sdpb(sdp_dir, procs, prec)
    
    # Step 3: Print outputs
    output_file_path = os.path.join(base_path, output_path, "out.txt")
    solution_file_path = os.path.join(base_path, output_path, "y.txt")
    
    # Read primal objective and solution
    pObj = read_primal_objective(output_file_path)
    pSol = read_solution(solution_file_path)

    return pObj,pSol
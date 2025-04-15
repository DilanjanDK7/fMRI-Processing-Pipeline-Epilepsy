# Comprehensive Pipeline Documentation

**Author:** Dilanjan DK  
**Email:** ddiyabal@uwo.ca

## Introduction

This document provides a detailed explanation of the Epilepsy fMRI Processing Pipeline, complementing the overview found in the main `README.md`. It covers the architecture, workflow stages, configuration nuances, and usage instructions.

## Pipeline Architecture

The pipeline is designed as a two-stage process orchestrated by a central Python script and launched via a Bash wrapper.

1.  **Bash Wrapper (`run_pipeline.sh`):**
    *   Serves as the primary entry point for the user.
    *   Parses basic input/output directory arguments and passes others to the Python script.
    *   Performs essential dependency checks:
        *   Python 3 and Pip existence.
        *   Required Python packages (`pybids`, `snakemake`, `dcm2bids`) installation (attempts `pip install --user` if missing).
        *   Docker installation and daemon status.
        *   Existence of the Python orchestrator script.
    *   Executes the Python orchestrator script (`run_combined_pipeline.py`).

2.  **Python Orchestrator (`run_combined_pipeline.py`):**
    *   Handles detailed command-line argument parsing (using `argparse`).
    *   Manages the overall workflow logic.
    *   **DICOM Conversion (Optional):** If the `--is_dicom` flag is set, it calls `dcm2bids` via a subprocess to convert input DICOMs to a BIDS structure in the specified output directory (`<output_dir>/bids_converted/`). Requires a `dcm2bids` configuration JSON.
    *   **fMRIPrep Stage:**
        *   Calls the `fmriprep` Snakemake workflow (`fmriprep/Snakefile`) using a `subprocess`.
        *   Sets the Snakemake working directory to `fmriprep/` using `--directory`.
        *   Overrides the input BIDS directory and the derivatives output directory via Snakemake's `--config` flag.
        *   Passes the `--cores` argument.
        *   **Skipping Denoising:** Generates specific target output file paths corresponding only to the `run_fmriprep` rule's outputs. This makes Snakemake skip the dependent `run_fmridenoise` rule.
        *   Adds `-p` flag for Snakemake verbosity (prints shell commands).
    *   **Feature Extraction Stage:**
        *   Calls the feature extraction wrapper script (`Feature_extraction_Container/run_container_pipeline.sh`) using a `subprocess`.
        *   Passes the fMRIPrep derivatives directory (`<output_dir>/derivatives`) as the `--input` argument to the wrapper.
        *   Passes `--cores` and optional `--features` arguments.
    *   Includes options to skip either the fMRIPrep or Feature Extraction stages entirely.

3.  **fMRIPrep Sub-pipeline (`fmriprep/`):**
    *   Managed by `fmriprep/Snakefile`.
    *   **Configuration:** Reads default parameters from `fmriprep/config/pipeline_config.yaml`. Requires `license.txt` in the same directory.
    *   **Core Rule (`run_fmriprep`):**
        *   Takes BIDS data path and derivatives path (passed via `--config` by the orchestrator) as input/output parameters.
        *   Uses `docker run` to execute the `nipreps/fmriprep:25.0.0` container.
        *   Mounts input data, output directory, and the Freesurfer license file (`fmriprep/config/license.txt`) into the container.
        *   Runs fMRIPrep with specified parameters (output spaces, resources). Uses `workflow.cores` for CPU allocation. Includes `-v` flag for fMRIPrep verbosity.
    *   **Other Rules:** Includes rules for checking reports (`check_fmriprep_reports`) and fixing permissions (`fix_permissions`). The denoising rule (`run_fmridenoise`) exists but is currently bypassed by the orchestrator script's targeting strategy.
    *   **Output:** Generates standard fMRIPrep BIDS-Derivatives outputs within the specified derivatives directory.

4.  **Feature Extraction Sub-pipeline (`Feature_extraction_Container/`):**
    *   Managed by the `Feature_extraction_Container/run_container_pipeline.sh` wrapper script.
    *   **Wrapper Script Logic:**
        *   Parses arguments (`--input`, `--cores`, `--features`, etc.).
        *   Checks for and potentially builds (via `run_container.sh build`) a custom Docker image named `fmri-feature-extraction`.
        *   Constructs arguments for running Snakemake *inside* the `fmri-feature-extraction` container.
        *   Mounts the input directory (fMRIPrep derivatives) as `/data/input` inside the container.
        *   Mounts the internal workflow definitions (`Feature_extraction_Container/workflows`) as `/app/workflows`.
        *   Generates Snakemake target paths based on requested features, pointing to locations *inside* the container (e.g., `/data/output/...`).
        *   Calls `run_container.sh run` which presumably handles the `docker run` execution with all the mounts and the internal `snakemake` command.
    *   **Internal Workflow:** A Snakemake workflow (`workflows/Snakefile`) runs *inside* the container, reading configuration (`workflows/config/config.yaml`, potentially modified by `--param` arguments) and calculating features like ALFF, ReHo, etc., based on the data in `/data/input`.
    *   **Output:** The wrapper script and internal workflow are assumed to place the final feature outputs back into the *mounted input directory* structure (e.g., `<output_dir>/derivatives/sub-*/func/Analytical_metrics/...`). *Note: The exact mechanism for output persistence back to the host relies on the implementation within `run_container.sh` or the Dockerfile used to build the image.*

## Prerequisites (Detailed)

*   **Python 3 & Pip:** Ensure `python3` and `pip` (or `python3 -m pip`) are available in your PATH. A recent version (3.8+) is advisable. Consider using a virtual environment (`venv` or `conda`) for managing dependencies, although the setup script currently uses `pip install --user`.
*   **Docker:** Docker Community Edition (CE) or Docker Engine must be installed and the service/daemon must be running. You typically need to be part of the `docker` group (or run commands with `sudo`, though this is not recommended for the main pipeline script). Test with `docker run hello-world` and `docker info`.
*   **Git:** Needed if cloning the repository from a Git source.
*   **Python Packages:**
    *   `pybids`: Used by the orchestrator to read BIDS dataset information (subjects, tasks).
    *   `snakemake`: The workflow management system used by both sub-pipelines. The orchestrator calls the `snakemake` command.
    *   `dcm2bids`: Required *only* if you intend to use the `--is_dicom` flag for automatic DICOM-to-BIDS conversion.

## Setup (Detailed)

1.  **Get the Code:** Clone via Git or download the source code archive. Navigate into the project's root directory (`Epilepsy_Pipeline_Final`).
2.  **Permissions:** Run `chmod +x run_pipeline.sh` and `chmod +x Feature_extraction_Container/run_container_pipeline.sh`. This ensures the shell scripts can be executed directly.
3.  **Freesurfer License:** Obtain your `license.txt` file from Freesurfer and place it *exactly* here: `fmriprep/config/license.txt`.

## Configuration (Detailed)

*   **`fmriprep/config/pipeline_config.yaml`:**
    *   `tasks`: List the task identifiers (e.g., "rest", "nback") present in your BIDS data that you want fMRIPrep to process.
    *   `preprocessing/fs_license_path`: Should remain `/opt/freesurfer/license.txt` as this is the path *inside* the container.
    *   `preprocessing/output_space`: Defines the standard space(s) for normalization. `MNI152NLin2009cAsym` is a common default. Consult fMRIPrep documentation for options.
    *   `preprocessing/n_cpus`, `preprocessing/mem_mb`: These are *defaults* used if not overridden. The `run_fmriprep` rule is now set to use `workflow.cores` for `n_cpus`, meaning the `--cores N` argument passed to `run_pipeline.sh` takes precedence for CPU allocation. Memory (`mem_mb`) might still be read from here unless overridden differently.
    *   `denoise/*`: Configuration for the denoising step. Since it's currently skipped by the orchestrator, these values are not actively used but would need correct container/parameter specification if denoising were re-enabled.
*   **`Feature_extraction_Container/workflows/config/config.yaml`:**
    *   This file controls the parameters for the *feature extraction* steps running inside the second container (e.g., frequency bands for ALFF, neighborhood size for ReHo). Review and modify this file according to your desired feature parameters.
    *   Remember that parameters here can be overridden at runtime using the `--param KEY=VALUE` argument passed to `run_pipeline.sh` (which forwards it to `run_container_pipeline.sh`).
*   **`dcm2bids` Configuration File:** If converting DICOMs, this JSON file maps DICOM series descriptions to BIDS imaging modalities and task names. Creating this file requires understanding your specific DICOM structure and acquisition protocols. Refer to `dcm2bids` documentation.

## Usage (Detailed)

Run from the project root directory:

```bash
./run_pipeline.sh <input_directory> <output_directory> [OPTIONS...]
```

*   The script first checks dependencies.
*   It then calls `python3 run_combined_pipeline.py <input_dir> <output_dir> [OPTIONS...]`.
*   The Python script handles logic:
    *   Checks for `--is_dicom`. If present, runs `dcm2bids` first. The output (`<output_dir>/bids_converted`) becomes the input for the next stage. If not present, `<input_dir>` is assumed to be BIDS.
    *   Checks for `--skip_fmriprep`. If absent, calls `run_fmriprep_pipeline`.
        *   This function determines subjects/tasks, constructs target output paths for fmriprep, and runs `snakemake` for the `fmriprep` stage.
    *   Checks for `--skip_feature_extraction`. If absent and fMRIPrep stage succeeded (or was skipped), calls `run_feature_extraction_pipeline`.
        *   This function calls the `run_container_pipeline.sh` script, passing the derivatives directory as input and forwarding `--cores` and `--features`.

**Verbosity:**
*   The `-p` flag added to the `snakemake` call for fMRIPrep in the Python script will show the `docker run` command being executed.
*   The `-v` flag added to the `fmriprep` command *inside* the `docker run` call (in `fmriprep/Snakefile`) will increase fMRIPrep's own log detail.
*   The feature extraction container's verbosity depends on its internal Snakemake setup and the `run_container_pipeline.sh` script.

## Troubleshooting

*   **`LockException` from Snakemake:** A previous run was interrupted uncleanly. Remove the relevant `.snakemake` directory (e.g., `rm -rf fmriprep/.snakemake` or `rm -rf Feature_extraction_Container/workflows/.snakemake` if the lock is there) and try again.
*   **Docker Errors:**
    *   `docker: command not found`: Docker is not installed or not in PATH.
    *   `Cannot connect to the Docker daemon...`: Docker service isn't running, or you lack permissions. Start Docker, check `sudo systemctl status docker`, or add your user to the `docker` group (`sudo usermod -aG docker $USER` then log out/in).
    *   Image pull errors: Network issues, Docker Hub outage, or incorrect image name specified.
    *   Container execution errors: Check container logs (e.g., `docker logs <container_id>`). Often related to permissions, resource limits, or internal script errors within the container.
*   **Permission Errors:** Especially after Docker runs, output files might be owned by `root`. The `fix_permissions` rule in `fmriprep/Snakefile` attempts to address this using `sudo chown`. Ensure your user has `sudo` privileges if needed, or adjust container user mapping if possible.
*   **Freesurfer License Error:** fMRIPrep fails, complaining about the license. Ensure `fmriprep/config/license.txt` exists, is valid, and the path in `fmriprep/config/pipeline_config.yaml` (`fs_license_path`) correctly points to `/opt/freesurfer/license.txt`.
*   **Configuration Errors:** `KeyError` from Snakemake usually means a required key is missing in the relevant `.yaml` config file. Check paths and spelling. `WorkflowError: Config file must be given as JSON or YAML...` means the specified config file is empty, malformed, or not found.
*   **`dcm2bids` Errors:** Usually related to an incorrect/incomplete configuration JSON or unexpected DICOM file structure. Check the `dcm2bids` output/logs carefully.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details. 
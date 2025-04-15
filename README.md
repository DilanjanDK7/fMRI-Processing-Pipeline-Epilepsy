# Epilepsy fMRI Processing Pipeline

This repository contains a combined pipeline for processing fMRI data for epilepsy research, integrating fMRIPrep for preprocessing and a custom suite for feature extraction.

**Author:** Dilanjan DK  
**Email:** ddiyabal@uwo.ca

## Overview

This pipeline automates the following steps:
1.  Optional conversion of DICOM data to BIDS format using `dcm2bids`.
2.  Preprocessing of BIDS-formatted fMRI data using `fMRIPrep` (running inside a Docker container).
3.  Extraction of various quantitative fMRI features (e.g., ALFF, ReHo, Hurst) using a custom feature extraction workflow (running inside a Docker container).

The pipeline is orchestrated by a main Python script (`run_combined_pipeline.py`) and launched via a Bash wrapper (`run_pipeline.sh`) that checks for dependencies.

## Prerequisites

Before running the pipeline, ensure you have the following installed:

*   **Python 3:** (Python 3.8 or later recommended)
*   **Pip:** The Python package installer.
*   **Docker:** The containerization platform. Ensure the Docker daemon is running.
*   **Git:** For cloning the repository (if applicable).

The following Python packages are required and will be automatically installed by the `run_pipeline.sh` script if missing:
*   `pybids`
*   `snakemake`
*   `dcm2bids` (only strictly necessary if using the DICOM conversion feature)

## Setup

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd Epilepsy_Pipeline_Final 
    ```
2.  **Ensure scripts are executable:**
    The `run_pipeline.sh` script attempts to make the necessary scripts executable, but you can also do it manually:
    ```bash
    chmod +x run_pipeline.sh
    chmod +x Feature_extraction_Container/run_container_pipeline.sh 
    ```

## Configuration

1.  **Freesurfer License:**
    *   You **must** obtain a Freesurfer license file (`license.txt`).
    *   Place this file inside the `fmriprep/config/` directory. The pipeline expects it to be named `license.txt`.
    *   The pipeline mounts this file into the fMRIPrep container at `/opt/freesurfer/license.txt`. The configuration file `fmriprep/config/pipeline_config.yaml` already points to this internal path.

2.  **fMRIPrep Configuration (`fmriprep/config/pipeline_config.yaml`):**
    *   This file contains default parameters for fMRIPrep and the (currently skipped) denoising step.
    *   You may review and adjust settings like `tasks`, `output_space`, `mem_mb`, etc., although core paths and resources are usually managed by the main script.
    *   **Important:** The `fs_license_path` is set to the path *inside* the container where the local `fmriprep/config/license.txt` is mounted. Do not change this unless you modify the mounting logic in `fmriprep/Snakefile`.

3.  **DICOM to BIDS Configuration (Optional):**
    *   If your input data is in DICOM format, you need a `dcm2bids` configuration JSON file.
    *   By default, the script looks for `dcm2bids_config.json` in the input directory or the script's directory.
    *   You can specify a path to your config file using the `--dcm2bids_config` flag when running the pipeline.

## Usage

The pipeline is run using the main Bash script `run_pipeline.sh`.

**Basic Syntax:**

```bash
./run_pipeline.sh <input_directory> <output_directory> [OPTIONS]
```

**Required Arguments:**

*   `<input_directory>`: Path to the input data directory. This should contain either a BIDS dataset or DICOM files (if using `--is_dicom`).
*   `<output_directory>`: Path to the main directory where all outputs (converted BIDS data, derivatives, logs) will be stored.

**Common Optional Arguments (passed to `run_combined_pipeline.py`):**

*   `--is_dicom`: Flag indicating that the `<input_directory>` contains DICOM data that needs conversion to BIDS.
*   `--dcm2bids_config PATH`: Path to the `dcm2bids` JSON configuration file (required if `--is_dicom` is used and the default config isn't found).
*   `--cores N`: Number of CPU cores to allocate to pipeline stages (default: 4). fMRIPrep will use this value.
*   `--participant_label P1 [P2 ...]`: Process only specific participant labels. If omitted, all participants found in the BIDS dataset are processed by fMRIPrep.
*   `--features F1 [F2 ...]`: Specify a list of features to calculate in the feature extraction stage (e.g., `alff reho hurst`). If omitted, the feature extraction script's default (likely all features) is used.
*   `--skip_fmriprep`: Skip the fMRIPrep stage (assumes outputs exist in `<output_directory>/derivatives`).
*   `--skip_feature_extraction`: Skip the feature extraction stage.

**Examples:**

*   **Run full pipeline on BIDS data with 8 cores:**
    ```bash
    ./run_pipeline.sh /path/to/bids_data /path/to/output --cores 8
    ```
*   **Convert DICOM, run full pipeline, specify config:**
    ```bash
    ./run_pipeline.sh /path/to/dicom_data /path/to/output --is_dicom --dcm2bids_config /path/to/my_dcm2bids.json --cores 8
    ```
*   **Run only fMRIPrep for specific participants:**
    ```bash
    ./run_pipeline.sh /path/to/bids_data /path/to/output --participant_label 01 02 --skip_feature_extraction --cores 12
    ```
*   **Run only specific feature extraction steps (assuming fMRIPrep is done):**
    ```bash
    ./run_pipeline.sh /path/to/bids_data /path/to/output --skip_fmriprep --features alff falff --cores 4
    ```

## Pipeline Stages

1.  **DICOM Conversion (Optional):** If `--is_dicom` is specified, `dcm2bids` converts the input DICOMs into a BIDS structure located in `<output_directory>/bids_converted`. This path then becomes the input for fMRIPrep.
2.  **fMRIPrep:** Runs the `nipreps/fmriprep` container via Snakemake. Performs standard fMRI preprocessing steps (motion correction, susceptibility distortion correction, normalization, etc.). Outputs are saved in BIDS-Derivatives format within `<output_directory>/derivatives`. Denoising is currently skipped by default in the orchestrator script.
3.  **Feature Extraction:** Runs the custom `fmri-feature-extraction` container via the `Feature_extraction_Container/run_container_pipeline.sh` script. Takes the fMRIPrep outputs from `<output_directory>/derivatives` as input. Calculates selected quantitative features and saves them within the derivatives structure, typically under `sub-*/func/Analytical_metrics/`.

## Output Structure

All outputs are organized within the specified `<output_directory>`:

*   **`<output_directory>/bids_converted/`**: Contains the BIDS dataset generated from DICOMs (only if `--is_dicom` was used).
*   **`<output_directory>/derivatives/`**: Contains the main outputs structured according to BIDS-Derivatives standards.
    *   Contains fMRIPrep outputs (preprocessed images, confounds, reports, etc.).
    *   Contains Feature Extraction outputs, typically nested within subject folders (e.g., `sub-17017/func/Analytical_metrics/ALFF/`, `sub-17017/func/Analytical_metrics/ReHo/`, etc.).

Logs from the Python orchestrator script are printed to the console during execution. Detailed logs from Snakemake, fMRIPrep, and the feature extraction steps might also be available within the output directory or printed to the console, depending on their internal configurations.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
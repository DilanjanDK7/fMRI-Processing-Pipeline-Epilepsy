# fMRI Feature Extraction Container

A comprehensive Docker-based solution for extracting analytical features from fMRI data using a Snakemake pipeline.

## Overview

This package provides a containerized workflow for calculating various analytical metrics from resting-state fMRI data, including:

- **ALFF** (Amplitude of Low-Frequency Fluctuation)
- **fALFF** (Fractional ALFF)
- **ReHo** (Regional Homogeneity)
- **Hurst Exponent**
- **Fractal Dimension**
- **Quantum Mechanical Fourier Transform (QM-FFT)**
- **Resting State Network (RSN) Analysis**

The pipeline uses Snakemake for workflow management and Docker for containerization, ensuring reproducibility and ease of deployment across different systems.

## Documentation

Detailed documentation for using this pipeline is available in the following files:

- [**User Guide**](docs/USER_GUIDE.md): Comprehensive information about setting up and using the pipeline
- [**Quick Reference**](docs/QUICK_REFERENCE.md): Common commands and procedures for everyday use
- [**RSN Guide**](docs/RSN_GUIDE.md): Detailed information about the Resting State Network analysis
- [**Visualization Guide**](docs/VISUALIZATION_GUIDE.md): Instructions for visualizing and interpreting outputs

For a complete documentation index, see the [Documentation README](docs/README.md).

## Requirements

- Docker (latest version recommended)
- At least 8GB RAM (16GB recommended for full analysis)
- Sufficient disk space for input data and results

## Quick Start

### Using the Simplified Pipeline Script

The easiest way to run the pipeline is using the simplified script:

```bash
./run_container_pipeline.sh --input /path/to/your/data --features alff,reho,qm_fft
```

#### Key Features of the Pipeline Script

- Automatically builds the Docker container if needed
- Places outputs in an "analytical_metrics" folder inside your input directory
- Allows selection of specific features to extract
- Supports custom parameter settings
- Can target specific subjects

#### Examples

Run all analyses for all subjects:
```bash
./run_container_pipeline.sh --input /path/to/your/data
```

Run ALFF and ReHo analyses with 4 cores:
```bash
./run_container_pipeline.sh --input /path/to/your/data --features alff,reho --cores 4
```

Run QM-FFT on a specific subject with custom parameters:
```bash
./run_container_pipeline.sh --input /path/to/your/data --subject sub-17017 --features qm_fft --param qm_fft_eps=1e-5
```

For more options:
```bash
./run_container_pipeline.sh --help
```

### Manual Approach

If you need more control, you can also manually build and run the container:

#### Building the Container

```bash
./run_container.sh build
```

For a clean build that doesn't use cache:

```bash
./run_container.sh build --no-cache
```

#### Running the Pipeline Manually

The basic command structure for running the pipeline is:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v /path/to/output/dir:/data/output -v $(pwd)/workflows:/app/workflows [command]
```

To run the entire Snakemake pipeline:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v /path/to/output/dir:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores [N]
```

Replace `[N]` with the number of cores you want to use, or omit for maximum parallelization.

## Input Data Requirements

The pipeline expects input data organized according to BIDS format:

```
/path/to/input/data/
├── sub-<ID>/
│   └── func/
│       ├── sub-<ID>_task-rest_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz
│       └── sub-<ID>_task-rest_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz
```

## Output Structure

The pipeline generates output in the following structure:

```
/path/to/output/dir/
├── sub-<ID>/
│   └── func/
│       └── Analytical_metrics/
│           ├── ALFF/
│           │   ├── sub-<ID>_alff.nii.gz
│           │   └── sub-<ID>_falff.nii.gz
│           ├── ReHo/
│           │   └── sub-<ID>_reho.nii.gz
│           ├── Hurst/
│           │   └── sub-<ID>_hurst.nii.gz
│           ├── Fractal/
│           │   └── sub-<ID>_fractal.nii.gz
│           ├── QM_FFT/
│           │   └── sub-<ID>_qm_fft.h5
│           └── RSN/
│               └── sub-<ID>_rsn_activity.h5
```

## Configuration

The pipeline configuration is managed through the `workflows/config/config.yaml` file. Key parameters include:

- **Subject IDs**: Specify the subjects to process
- **I/O Paths**: Define input and output paths 
- **Processing Parameters**: Set specific parameters for each analysis
- **Core Usage**: Adjust parallel processing settings

Example configuration:

```yaml
# Input/Output settings
bids_derivatives_dir: "/data/input" 
output_dir: "/data/output"
overwrite_existing: true

# Subject settings
subjects:
  - "sub-17017"
  # - "sub-002"  # Uncomment to add more subjects

# Processing options
n_jobs: 4          # Number of parallel jobs to run
memory_limit: 8    # Memory limit in GB per job

# ALFF computation settings
compute_falff: true
alff_bandpass_low: 0.01
alff_bandpass_high: 0.08

# ReHo computation settings
reho_neighborhood: 27  # 27 for 3x3x3 cube

# ... additional settings
```

## Feature Details

### ALFF and fALFF

Measures the amplitude of BOLD signal fluctuations in the low-frequency range (typically 0.01-0.08 Hz), providing insight into regional spontaneous brain activity.

### ReHo (Regional Homogeneity)

Calculates similarity of the time series of a given voxel to those of its nearest neighbors, reflecting local synchronization of spontaneous brain activity.

### Hurst Exponent

Quantifies the long-range temporal dependence in the fMRI time series, indicating the predictability of the signal.

### Fractal Dimension

Estimates the complexity and self-similarity of the fMRI time series, providing insight into the chaotic nature of brain activity.

### QM-FFT (Quantum Mechanical Fourier Transform)

Applies quantum mechanical principles to analyze fMRI data in the frequency domain, extracting several features:
- Magnitude
- Phase
- Temporal difference magnitude
- Temporal difference phase
- Local variance (optional)

### RSN (Resting State Network) Activity

Extracts time series from established resting-state networks using the Yeo atlas:
- 7-Network parcellation
- 17-Network parcellation

## Advanced Usage

### Running Individual Analyses

To run a specific analysis only (e.g., ALFF):

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores /data/output/sub-17017/func/Analytical_metrics/ALFF/sub-17017_alff.nii.gz
```

### Debugging and Testing

For testing with smaller sample sizes:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores 1 /data/output/sub-17017/func/Analytical_metrics/QM_FFT/sub-17017_qm_fft.h5
```

Sample analysis uses reduced data sizes to speed up testing:
- QM-FFT uses spatial sampling (configurable in scripts/qm_fft_test.py)
- RSN analysis uses temporal sampling (configurable in config.yaml)

### Inspecting Outputs

To examine HDF5 outputs (QM-FFT, RSN analysis):

```bash
./run_container.sh run -v $(pwd)/pipeline_outputs:/data/output h5ls -r /data/output/sub-17017/func/Analytical_metrics/QM_FFT/sub-17017_qm_fft.h5
```

## Backing Up the Pipeline

Create a backup of the current configuration:

```bash
tar -czf feature_extraction_backup_$(date +%Y-%m-%d_%H%M%S).tar.gz workflows scripts docker run_container.sh environment.yml README.md requirements.txt
```

## Troubleshooting

If you encounter issues running the pipeline, try these solutions:

### SnakemakeLockException

If you get a `SnakemakeLockException` error:

```
Error: Directory cannot be locked. Please make sure that no other Snakemake process is trying to create the same files in parallel.
```

This can happen if a previous run was interrupted. Unlock the directory:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --unlock
```

### Memory Issues

If the container crashes due to memory limitations:

1. Reduce parallelization: Use `--cores 1` to run one job at a time
2. Increase Docker memory limit: Edit Docker settings to provide more memory
3. Modify the `n_jobs` and `memory_limit` settings in the config file

### File Permission Issues

If you encounter permissions issues accessing output files:

```bash
sudo chown -R $(id -u):$(id -g) pipeline_outputs/
```

## Copyright

© 2025 Dilanjan DK and BrainLab, University of Western Ontario. All rights reserved.

**Contact:** Dilanjan DK (ddiyabal@uwo.ca)

This software and its documentation are proprietary and confidential. Unauthorized copying, transfer, or use of this software, its documentation, and related materials, via any medium, is strictly prohibited without prior written consent from the copyright holders.

## Citation

If you use this pipeline in your research, please cite:

```
Dilanjan, DK. (2025). fMRI Feature Extraction Container: A Comprehensive Pipeline for Analytical Metrics. BrainLab, University of Western Ontario.
```

## Acknowledgments

This pipeline incorporates several open-source tools and packages:
- Snakemake for workflow management
- Nilearn and Nibabel for neuroimaging analysis
- AFNI for ReHo computation
- QM_FFT_Feature_Package for quantum mechanical analysis 

Developed at the BrainLab, University of Western Ontario by Dilanjan DK.
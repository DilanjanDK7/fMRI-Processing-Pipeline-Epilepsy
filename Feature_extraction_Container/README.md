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
./run_container_pipeline.sh --input /path/to/your/data --features alff,reho,hurst,fractal
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

Run Hurst and Fractal analyses on a specific subject with custom parameters:
```bash
./run_container_pipeline.sh --input /path/to/your/data --subject sub-17017 --features hurst,fractal --param hurst_method=dfa --param fd_method=higuchi --param kmax=64
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
│           │   ├── sub-<ID>_falff.nii.gz
│           │   ├── sub-<ID>_malff.nii.gz
│           │   └── sub-<ID>_rsfa.nii.gz
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
alff_band_low: 0.01
alff_band_high: 0.08

# ReHo computation settings
reho_neighborhood: 27  # 27 for 3x3x3 cube

# Hurst computation settings
hurst_method: "dfa"  # Options: "dfa" or "rs"
min_var: 1e-6        # Minimum variance threshold

# Fractal computation settings
fd_method: "higuchi"  # Options: "higuchi" or "psd"
kmax: 64             # Maximum lag parameter for Higuchi method

# ... additional settings
```

## Feature Details

### ALFF and fALFF

Measures the amplitude of BOLD signal fluctuations in the low-frequency range (typically 0.01-0.08 Hz), providing insight into regional spontaneous brain activity.

#### Implementation Details

The ALFF implementation has been updated to provide enhanced functionality:

- **Multiple Output Metrics**: 
  - ALFF: Standard amplitude of low-frequency fluctuations
  - fALFF: Fractional ALFF (ratio of ALFF to the total power across all frequencies)
  - mALFF: Mean ALFF (normalized ALFF values)
  - RSFA: Resting-state fluctuation amplitude

- **Preprocessing Options**:
  - Detrending methods: linear, constant, polynomial, or none
  - Window functions: hamming, hanning, blackman, or none
  - Normalization methods: z-score, percent change, or none

- **Parameter Customization**:
  - Adjustable frequency bands for low and high-frequency components
  - Control over fALFF high-band cutoff frequencies

#### Command Line Parameters

```
--alff_band_low FLOAT    Lower frequency bound (default: 0.01 Hz)
--alff_band_high FLOAT   Upper frequency bound (default: 0.08 Hz)
--compute_falff BOOL     Whether to compute fractional ALFF (default: true)
```

### ReHo (Regional Homogeneity)

Calculates similarity of the time series of a given voxel to those of its nearest neighbors, reflecting local synchronization of spontaneous brain activity.

#### Command Line Parameters

```
--reho_neighborhood INT  Cluster size (7, 19, or 27; default: 27)
```

### Hurst Exponent

Quantifies the long-range temporal dependence in the fMRI time series, indicating the predictability of the signal.

#### Implementation Details

The updated Hurst exponent implementation offers:

- **Multiple Calculation Methods**:
  - DFA (Detrended Fluctuation Analysis): More robust to non-stationarity in the time series
  - R/S (Rescaled Range): Traditional Hurst calculation method

- **Performance Optimizations**:
  - Parallelized computation for faster processing on multi-core systems
  - Variance thresholding to avoid processing flat or nearly-flat signals

- **Preprocessing Options**:
  - Optional bandpass filtering to focus on specific frequency ranges
  - Robust estimation with outlier handling

#### Command Line Parameters

```
--hurst_method STRING    Method for calculation ("dfa" or "rs"; default: "dfa")
--n_jobs INT             Number of parallel jobs (default: 8)
--min_var FLOAT          Minimum variance threshold (default: 1e-6)
```

### Fractal Dimension

Estimates the complexity and self-similarity of the fMRI time series, providing insight into the chaotic nature of brain activity.

#### Implementation Details

The updated fractal dimension implementation features:

- **Multiple Calculation Methods**:
  - Higuchi Fractal Dimension (HFD): Time-domain approach that estimates curve length across different scales
  - Power Spectral Density (PSD): Frequency-domain method that estimates fractal dimension from spectral properties

- **Performance Enhancements**:
  - Parallelized computation for efficient processing
  - Adaptive scale selection for more accurate estimations
  - Variance thresholding to focus on meaningful signals

- **Parameter Customization**:
  - Adjustable maximum lag parameter (kmax) for Higuchi method
  - Control over normalization and preprocessing steps

#### Command Line Parameters

```
--fd_method STRING       Method for fractal dimension calculation ("higuchi" or "psd"; default: "higuchi")
--kmax INT               Maximum lag parameter for Higuchi method (default: 64)
--n_jobs INT             Number of parallel jobs (default: 8)
--min_var FLOAT          Minimum variance threshold (default: 1e-6)
```

### QM-FFT (Quantum Mechanical Fourier Transform)

Applies quantum mechanical principles to frequency analysis of fMRI data, providing unique insights into brain dynamics not captured by conventional methods.

### RSN (Resting State Network) Analysis

Evaluates activity and connectivity within established resting-state networks, helping to characterize functional brain organization.

## Advanced Usage

### Combining Multiple Features

For comprehensive analysis, you can extract multiple features in a single run:

```bash
./run_container_pipeline.sh --input /path/to/your/data --features alff,reho,hurst,fractal,qm_fft,rsn --cores 8
```

### Custom Parameter Sets

You can override multiple parameters to customize your analysis:

```bash
./run_container_pipeline.sh --input /path/to/your/data --features alff,hurst,fractal \
  --param alff_band_low=0.01 \
  --param alff_band_high=0.1 \
  --param hurst_method=dfa \
  --param fd_method=higuchi \
  --param kmax=32 \
  --param n_jobs=4
```

### Using the Pipeline in Research Projects

When using this pipeline in your research, please ensure proper citation and acknowledgment. The methods implemented are based on established neuroimaging techniques with appropriate modifications for enhanced performance and reliability.

## Troubleshooting

If you encounter issues, try the following steps:

1. Ensure you have the latest version of the container
2. Check that input data is properly formatted according to BIDS
3. Increase memory allocation for more complex analyses
4. Check logs for specific error messages
5. Try running single features rather than combining multiple analyses

For persistent issues, please contact the maintainers.

## License and Citation

© 2025 Dilanjan DK and BrainLab, University of Western Ontario. All rights reserved.

If you use this pipeline in your research, please cite appropriately according to the guidelines in the [Citation Guide](docs/CITATION.md).
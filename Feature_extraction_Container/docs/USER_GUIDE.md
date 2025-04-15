# User Guide: fMRI Feature Extraction Container

This guide provides detailed information about using the fMRI Feature Extraction Container, covering each analytical feature, configuration options, and workflow management.

## Table of Contents

1. [Introduction](#introduction)
2. [Setup and Installation](#setup-and-installation)
3. [Pipeline Overview](#pipeline-overview)
4. [Detailed Feature Descriptions](#detailed-feature-descriptions)
5. [Configuration Options](#configuration-options)
6. [Usage Workflows](#usage-workflows)
7. [Output Formats and Interpretation](#output-formats-and-interpretation)
8. [Troubleshooting](#troubleshooting)
9. [Extending the Pipeline](#extending-the-pipeline)

## Introduction

The fMRI Feature Extraction Container is designed to facilitate comprehensive analysis of resting-state fMRI data by extracting various analytical metrics. The container-based approach ensures consistent environments across different systems, while the Snakemake workflow management provides reproducible analysis pipelines.

### Key Benefits

- **Reproducibility**: Docker containerization ensures identical environments
- **Scalability**: Parallelization capabilities via Snakemake
- **Modularity**: Each analysis can be run independently
- **Configurability**: Extensive parameter customization
- **Documentation**: Comprehensive guidance for interpreting results

## Setup and Installation

### Prerequisites

- Docker installed and properly configured
- Sufficient system resources (8GB+ RAM recommended)
- Input data in BIDS-compatible format

### Container Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/fmri-feature-extraction.git
   cd fmri-feature-extraction
   ```

2. Build the Docker image:
   ```bash
   ./run_container.sh build
   ```

3. Verify the container builds successfully:
   ```bash
   ./run_container.sh run echo "Container is ready"
   ```

## Pipeline Overview

The pipeline consists of several independent analytical modules, each extracting different features from fMRI data:

1. **ALFF/fALFF**: Measures low-frequency fluctuations to identify spontaneous brain activity
2. **ReHo**: Quantifies local synchronization of spontaneous brain activity
3. **Hurst Exponent**: Analyzes long-range temporal dependencies
4. **Fractal Dimension**: Estimates complexity and self-similarity of time series
5. **QM-FFT**: Applies quantum mechanical principles to extract frequency-domain features
6. **RSN**: Extracts time series from established resting-state networks

Each module can be run independently or as part of a comprehensive pipeline.

## Detailed Feature Descriptions

### ALFF and fALFF

**Amplitude of Low-Frequency Fluctuation (ALFF)** measures the total power of a specific low-frequency range in the fMRI time series.

- **Technical details**: ALFF is calculated by converting time series to frequency domain via Fast Fourier Transform, then summing amplitudes across the specified frequency band (typically 0.01-0.08 Hz).
- **fALFF**: Normalized version of ALFF, calculated as the ratio of the power within the low-frequency band to the power across the entire frequency range.
- **Applications**: Identifies regions with significant spontaneous activity, useful for detecting abnormal brain function in disorders like ADHD and depression.

**Parameters:**
- `bandpass_low`: Lower frequency bound (default: 0.01 Hz)
- `bandpass_high`: Upper frequency bound (default: 0.08 Hz)
- `detrend_method`: Signal detrending method (options: "linear", "constant", "none")
- `normalize_method`: Method for normalizing ALFF maps (options: "zscore", "percent", "none")

### ReHo (Regional Homogeneity)

**Regional Homogeneity** measures the similarity of the time series of a given voxel to those of its nearest neighbors.

- **Technical details**: Calculated using Kendall's coefficient of concordance (KCC) across a neighborhood of voxels.
- **Applications**: Reflects functional connectivity at a local level, useful for identifying local synchronization abnormalities in neurological disorders.

**Parameters:**
- `neighborhood`: Size of the voxel neighborhood for ReHo calculation
  - `7`: Face-adjacent neighboring voxels only
  - `19`: Face- and edge-adjacent neighbors
  - `27`: Face-, edge-, and corner-adjacent neighbors (cubic neighborhood, default)

### Hurst Exponent

The **Hurst Exponent** quantifies the long-range temporal dependence and self-similarity in time series.

- **Technical details**: Calculated using Detrended Fluctuation Analysis (DFA) or Rescaled Range (RS) analysis.
- **Interpretation**: 
  - H = 0.5: Random walk (no temporal dependence)
  - 0.5 < H < 1: Persistent behavior (trends tend to continue)
  - 0 < H < 0.5: Anti-persistent behavior (trends tend to reverse)
- **Applications**: Identifies regions with notable long-term memory in neural activity, useful for characterizing complex temporal dynamics in brain function.

**Parameters:**
- `hurst_method`: Method for Hurst exponent calculation (options: "dfa", "rs")

### Fractal Dimension

**Fractal Dimension** quantifies the complexity and self-similarity of the fMRI time series.

- **Technical details**: Calculated using Higuchi's method or Power Spectral Density (PSD) analysis.
- **Interpretation**: Higher values indicate more complex temporal dynamics.
- **Applications**: Characterizes the complexity of neural activity, which may be altered in disorders like Alzheimer's disease and schizophrenia.

**Parameters:**
- `fractal_method`: Method for calculating fractal dimension (options: "higuchi", "psd")

### QM-FFT (Quantum Mechanical Fourier Transform)

**QM-FFT** applies quantum mechanical principles to analyze fMRI data in the frequency domain.

- **Technical details**: Transforms fMRI data into the frequency domain and extracts features based on quantum mechanical operators.
- **Extracted features**:
  - `magnitude`: Strength of frequency components
  - `phase`: Angular information of frequency components
  - `temporal_diff_magnitude`: Changes in magnitude over time
  - `temporal_diff_phase`: Changes in phase over time
  - `local_variance`: Local variability of frequency components
- **Applications**: Provides unique insights into the frequency structure of neural activity, potentially revealing patterns not detectable with traditional methods.

**Parameters:**
- `eps`: Epsilon value for numerical stability (default: 1e-6)
- `radius`: Radius parameter for local calculations (default: 0.6)
- `local_k`: k parameter for local variance calculation (default: 5)

### RSN (Resting State Network) Analysis

**RSN Analysis** extracts time series from established resting-state networks using the Yeo atlas.

- **Technical details**: Uses predefined network masks to extract average time series from each network.
- **Networks included**:
  - Yeo 7-network parcellation: Visual, Somatomotor, Dorsal Attention, Ventral Attention, Limbic, Frontoparietal, Default
  - Yeo 17-network parcellation: More fine-grained subdivision of the 7 networks
- **Applications**: Allows analysis of network-level activity and connectivity, useful for studying network dynamics in rest and task conditions.

**Parameters:**
- `rsn_sample_tp`: Number of time points to use when sampling (for testing, default: 100)

## Configuration Options

The pipeline's behavior is controlled through the `workflows/config/config.yaml` file. Key sections include:

### Input/Output Settings

```yaml
# Input/Output settings
bids_derivatives_dir: "/data/input"  # Path to input data
output_dir: "/data/output"           # Path for output results
overwrite_existing: true             # Whether to overwrite existing output
```

### Subject Selection

```yaml
# Subject settings
subjects:
  - "sub-17017"  # Active subject
  # - "sub-002"  # Commented subjects are ignored
  # - "sub-003"
```

### Resource Management

```yaml
# Processing options
n_jobs: 4         # Number of parallel jobs within each analytical module
memory_limit: 8   # Memory limit in GB per job
```

### Analysis-Specific Parameters

Each analysis type has its own configurable parameters:

```yaml
# ALFF computation settings
compute_falff: true
alff_bandpass_low: 0.01
alff_bandpass_high: 0.08
detrend_method: "linear"
normalize_method: "zscore"

# ReHo computation settings
reho_neighborhood: 27

# ... additional analysis parameters
```

## Usage Workflows

### Basic Workflow: Running All Analyses

To run all analyses for the subjects specified in the config file:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores
```

### Individual Feature Analysis

To run only a specific analysis (e.g., ALFF):

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores /data/output/sub-17017/func/Analytical_metrics/ALFF/sub-17017_alff.nii.gz
```

### Multiple Features for Multiple Subjects

To run selected analyses for multiple subjects:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores /data/output/sub-{001,002,003}/func/Analytical_metrics/{ALFF,ReHo}/sub-{001,002,003}_{alff,reho}.nii.gz
```

### Testing Mode

For faster testing with reduced data:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores 1 /data/output/sub-17017/func/Analytical_metrics/QM_FFT/sub-17017_qm_fft.h5
```

### Dry Run

To check what would be executed without actually running the analyses:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows -n
```

## Output Formats and Interpretation

### NIfTI Format (.nii.gz)

ALFF, fALFF, ReHo, Hurst, and Fractal outputs are stored as 3D NIfTI files containing voxel-wise metrics.

**Interpretation tips:**
- Values are typically standardized (e.g., z-scored) for comparison
- Higher values generally indicate stronger metric presence
- Visualization: Use tools like FSLeyes, AFNI viewer, or NiiVue to display on brain templates

### HDF5 Format (.h5)

QM-FFT and RSN analyses produce HDF5 files containing multiple datasets.

**QM-FFT HDF5 structure:**
```
/analysis/
    /map_0_magnitude
    /map_0_phase
    /map_0_temporal_diff_magnitude
    /map_0_temporal_diff_phase
    /map_0_local_variance (if enabled)
/data/
    /forward_fft
    /gradient_map_0
    ...
```

**RSN HDF5 structure:**
```
/networks_7/
    /Visual
    /Somatomotor
    /Dorsal Attention
    ...
/networks_17/
    /Network 1
    /Network 2
    ...
```

**Interpreting HDF5 files:**
- Use tools like `h5ls -r` to view the structure
- For detailed analysis, use Python with h5py, pandas, and matplotlib:
  ```python
  import h5py
  import matplotlib.pyplot as plt
  
  # Load QM-FFT data
  with h5py.File('sub-17017_qm_fft.h5', 'r') as f:
      magnitude = f['/analysis/map_0_magnitude'][:]
      phase = f['/analysis/map_0_phase'][:]
      
      # Plot or analyze...
  ```

## Troubleshooting

### Common Issues and Solutions

#### Docker-Related Issues

- **Error**: "docker: Error response from daemon: OCI runtime create failed"
  **Solution**: Check Docker's memory allocation in Docker Desktop settings

- **Error**: "no space left on device"
  **Solution**: Clean up Docker cache: `docker system prune -a`

#### Snakemake Issues

- **Error**: "Error: Directory cannot be locked"
  **Solution**: Run with `--unlock` flag to release previous locks

- **Error**: "IncompleteFilesException"
  **Solution**: Delete incomplete outputs or add `--rerun-incomplete` flag

#### Permission Issues

- **Error**: "Permission denied" when accessing output files
  **Solution**: Adjust file ownership: `sudo chown -R $(id -u):$(id -g) /path/to/output/dir`

#### Input Data Issues

- **Error**: "FileNotFoundError: File does not exist"
  **Solution**: Verify BIDS formatting of input data and paths in config.yaml

## Extending the Pipeline

### Adding New Features

To add a new analytical feature to the pipeline:

1. Create a new Python script in the `scripts/` directory:
   ```bash
   touch scripts/new_feature.py
   chmod +x scripts/new_feature.py
   ```

2. Implement the feature extraction logic with proper argument parsing

3. Add a corresponding test script with sampling capabilities

4. Update the Snakefile with a new rule:
   ```python
   rule compute_new_feature:
       input:
           fmri = get_fmri_file,
           mask = get_mask_file
       output:
           new_feat = os.path.join(
               config["output_dir"],
               "{subject}",
               "func",
               "Analytical_metrics",
               "NewFeature",
               "{subject}_new_feature.nii.gz"
           )
       params:
           # Custom parameters
       shell:
           """
           mkdir -p $(dirname {output.new_feat})
           python /app/scripts/new_feature_test.py \
               --fmri {input.fmri} \
               --output {output.new_feat} \
               --mask {input.mask} \
               [additional parameters]
           """
   ```

5. Update `rule all` in the Snakefile to include the new outputs

6. Add configuration parameters to `config.yaml`

### Customizing Existing Features

To modify an existing feature:

1. Identify the relevant script in `scripts/`
2. Update the script with new functionality
3. Modify the corresponding test script if necessary
4. Update configuration parameters in `config.yaml`
5. Rebuild the container with `./run_container.sh build --no-cache`

### Integrating with Existing Workflows

To integrate this pipeline with existing workflows:

1. Export results from this pipeline
2. Use custom scripts to convert outputs to formats required by other tools
3. Consider creating a wrapper script that calls both workflows in sequence 
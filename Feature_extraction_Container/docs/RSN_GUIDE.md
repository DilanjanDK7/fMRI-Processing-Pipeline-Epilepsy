# Resting State Network (RSN) Analysis Guide

This guide provides detailed information about the Resting State Network (RSN) analysis implemented in the fMRI Feature Extraction Container.

## Overview

The RSN analysis extracts time series data from established resting-state networks using the Yeo atlas parcellations. This enables researchers to analyze functional connectivity and network dynamics without the need for seed-based or independent component analyses.

## Features

- Automated download of Yeo atlas parcellations (7 and 17 networks)
- Extraction of network-specific time series
- Standardization and denoising options
- Outputs in both CSV and HDF5 formats for flexibility in downstream analyses

## Technical Details

### Yeo Atlas Networks

The pipeline uses the Yeo et al. 2011 atlas, which defines functional networks based on resting-state fMRI data from 1,000 subjects. Two parcellation schemes are implemented:

#### 7-Network Parcellation

1. **Visual Network**: Processing of visual information
2. **Somatomotor Network**: Motor and sensory processing
3. **Dorsal Attention Network**: Top-down attention control
4. **Ventral Attention Network**: Bottom-up attention control
5. **Limbic Network**: Emotion and motivation
6. **Frontoparietal Network**: Executive control and decision-making
7. **Default Mode Network**: Self-referential thinking and internal mentation

#### 17-Network Parcellation

A more fine-grained subdivision of the 7 networks, providing higher resolution for network analysis.

### Implementation Details

The RSN extraction involves the following steps:

1. **Atlas Download**: The `download_rsn_masks.py` script automatically downloads the Yeo atlas parcellations using nilearn.

2. **Time Series Extraction**: For each network in the parcellations, the mean time series is extracted using NiftiLabelsMasker from nilearn.

3. **Processing Options**:
   - **Standardization**: Time series can be standardized (z-scored)
   - **Sample Mode**: For testing, a subset of time points can be used

4. **Output Generation**: Results are saved in both CSV format (for easy inspection) and HDF5 format (for efficient storage and access).

## Usage

### Standalone Usage

The RSN extraction can be run directly via:

```bash
python scripts/rsn_extraction.py --fmri /path/to/fmri.nii.gz --output-dir /path/to/output --mask /path/to/mask.nii.gz [--subject-id SUB-ID] [--sample] [--sample-tp 100]
```

### Pipeline Integration

Within the Snakemake pipeline, RSN extraction is controlled via the `config.yaml` file:

```yaml
# RSN extraction settings
compute_rsn: true          # Enable/disable RSN extraction
rsn_sample_tp: 100         # Number of time points to sample in testing mode
```

To run only the RSN analysis for a subject:

```bash
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores /data/output/sub-17017/func/Analytical_metrics/RSN/sub-17017_rsn_activity.h5
```

## Outputs

### File Structure

The RSN analysis produces the following outputs:

1. **CSV files**:
   - `sub-<ID>_rsn_7networks.csv`: Time series for each of the 7 networks
   - `sub-<ID>_rsn_17networks.csv`: Time series for each of the 17 networks

2. **HDF5 file** (`sub-<ID>_rsn_activity.h5`):
   - `/networks_7/`: Time series for 7-network parcellation
     - `/Visual`: Time series for the Visual network
     - `/Somatomotor`: Time series for the Somatomotor network
     - ... (additional networks)
   - `/networks_17/`: Time series for 17-network parcellation
     - `/Network 1`: Time series for network 1
     - `/Network 2`: Time series for network 2
     - ... (additional networks)
   - Metadata attributes:
     - `subject_id`: Subject identifier
     - `fmri_file`: Input fMRI filename
     - `mask_file`: Mask filename
     - `sample_applied`: Whether sampling was applied
     - `sample_timepoints`: Number of time points if sampled

### Inspecting Outputs

To examine the HDF5 file structure:

```bash
./run_container.sh run -v $(pwd)/pipeline_outputs:/data/output h5ls -r /data/output/sub-17017/func/Analytical_metrics/RSN/sub-17017_rsn_activity.h5
```

To view CSV files:

```bash
./run_container.sh run -v $(pwd)/pipeline_outputs:/data/output head -n 5 /data/output/sub-17017/func/Analytical_metrics/RSN/sub-17017_rsn_7networks.csv
```

## Data Analysis Examples

### Python Example: Network Time Series Analysis

```python
import h5py
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr

# Load RSN data
with h5py.File('sub-17017_rsn_activity.h5', 'r') as f:
    # Get time series for DMN and FPN networks
    dmn_ts = f['/networks_7/Default'][:]
    fpn_ts = f['/networks_7/Frontoparietal'][:]
    
    # Calculate correlation between networks
    corr, p_value = pearsonr(dmn_ts, fpn_ts)
    print(f"Correlation between DMN and FPN: {corr:.3f} (p={p_value:.3f})")
    
    # Plot time series
    plt.figure(figsize=(12, 6))
    plt.plot(dmn_ts, label='Default Mode Network')
    plt.plot(fpn_ts, label='Frontoparietal Network')
    plt.legend()
    plt.xlabel('Time Point')
    plt.ylabel('BOLD Signal (standardized)')
    plt.title('DMN and FPN Time Series')
    plt.savefig('dmn_fpn_timeseries.png')
```

### Network Connectivity Analysis Example

```python
import h5py
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load RSN data for 7-network parcellation
with h5py.File('sub-17017_rsn_activity.h5', 'r') as f:
    # Extract all network time series
    networks = []
    network_names = ['Visual', 'Somatomotor', 'Dorsal Attention', 
                    'Ventral Attention', 'Limbic', 'Frontoparietal', 'Default']
    
    for name in network_names:
        networks.append(f[f'/networks_7/{name}'][:])
    
    # Convert to numpy array
    networks = np.array(networks)
    
    # Calculate correlation matrix
    corr_matrix = np.corrcoef(networks)
    
    # Plot correlation matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1,
                xticklabels=network_names, yticklabels=network_names)
    plt.title('Network Correlation Matrix')
    plt.tight_layout()
    plt.savefig('network_correlation_matrix.png')
```

## Advanced Usage

### Custom Network Masks

While the pipeline uses the Yeo atlas by default, it can be extended to use custom network masks:

1. Prepare your custom network masks in NIfTI format, with integer labels for each network
2. Modify the `download_rsn_masks.py` script to load your custom masks
3. Update the network labels in `rsn_extraction.py` to match your custom network names

### Integration with QM-FFT

The RSN analysis can be combined with QM-FFT to analyze frequency-domain properties of network time series:

1. Extract network time series using RSN analysis
2. Apply QM-FFT analysis to each network time series
3. Compare frequency domain features across networks

## Troubleshooting

### Common Issues

- **Missing Yeo Atlas**: If the atlas download fails, check your internet connection or manually download the Yeo atlas from the nilearn website.

- **Misaligned Masks**: Ensure your input fMRI data and the Yeo atlas are in the same space (MNI152).

- **No Variance in Network Time Series**: This can occur if the mask doesn't overlap with the brain or if there are signal quality issues in the fMRI data.

### Solutions

- **Verify Mask Alignment**: Use a visualization tool like FSLeyes to check that the Yeo atlas masks align with your input fMRI data.

- **Check Time Series**: Examine the CSV output files to verify that the time series have reasonable variance and aren't all zeros or constants.

- **Custom Masks**: If the atlas doesn't align well with your data, consider using custom network masks derived from your specific dataset.

## References

1. Yeo, B. T., et al. (2011). The organization of the human cerebral cortex estimated by intrinsic functional connectivity. Journal of Neurophysiology, 106(3), 1125-1165. DOI: 10.1152/jn.00338.2011

2. Thomas Yeo, B. T., et al. (2011). The organization of the human cerebral cortex estimated by intrinsic functional connectivity. Journal of Neurophysiology, 106(3), 1125-1165. DOI: 10.1152/jn.00338.2011

3. Nilearn Documentation: https://nilearn.github.io/stable/modules/generated/nilearn.datasets.fetch_atlas_yeo_2011.html 
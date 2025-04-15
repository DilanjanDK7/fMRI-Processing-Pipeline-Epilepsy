# Visualization Guide for fMRI Feature Extraction Outputs

This guide provides instructions for visualizing the different types of outputs produced by the fMRI Feature Extraction Container.

## Table of Contents

1. [Introduction](#introduction)
2. [Visualizing NIfTI Outputs](#visualizing-nifti-outputs)
3. [Working with HDF5 Files](#working-with-hdf5-files)
4. [Creating Publication-Ready Figures](#creating-publication-ready-figures)
5. [Batch Processing and Visualization](#batch-processing-and-visualization)

## Introduction

The fMRI Feature Extraction Container produces outputs in several formats:

- **NIfTI files (.nii.gz)**: 3D brain volumes containing voxel-wise metrics (ALFF, fALFF, ReHo, Hurst, Fractal)
- **HDF5 files (.h5)**: Hierarchical datasets containing multiple analysis results (QM-FFT, RSN)
- **CSV files (.csv)**: Tabular data for network time series (RSN)

This guide will help you visualize and interpret these different outputs.

## Visualizing NIfTI Outputs

### Recommended Software

Several software packages can be used to visualize NIfTI files:

- **FSLeyes**: Part of the FSL package, offers comprehensive visualization
- **AFNI**: Powerful viewer with extensive functionality
- **MRIcroGL**: User-friendly visualization with advanced rendering
- **NiiVue**: Web-based viewer for quick visualization

### Basic Visualization Steps

#### Using FSLeyes

1. **Launch FSLeyes**:
   ```bash
   fsleyes
   ```

2. **Load a standard brain template**:
   File → Add Standard → MNI152_T1_2mm

3. **Add your metric map**:
   File → Add → Select your `.nii.gz` file (e.g., `sub-17017_alff.nii.gz`)

4. **Configure the overlay**:
   - Set color map (e.g., "red-yellow")
   - Adjust min/max values (e.g., display values between 2-8 for z-scored maps)
   - Set transparency to see the underlying anatomy

#### Using the Container

You can also use the container to visualize outputs:

```bash
./run_container.sh run -v $(pwd)/pipeline_outputs:/data/output fsleyes /data/output/sub-17017/func/Analytical_metrics/ALFF/sub-17017_alff.nii.gz -cm hot -dr 2 8
```

### Comparing Multiple Maps

To compare different metrics for the same subject:

1. Load a standard template
2. Add multiple metric maps (ALFF, ReHo, etc.)
3. Use different color maps for each metric
4. Toggle visibility to compare patterns

Example FSLeyes command:

```bash
fsleyes MNI152_T1_2mm.nii.gz \
  sub-17017_alff.nii.gz -cm red-yellow -dr 2 8 \
  sub-17017_reho.nii.gz -cm blue-lightblue -dr 2 8 \
  sub-17017_hurst.nii.gz -cm green -dr 0.4 0.8
```

## Working with HDF5 Files

HDF5 files contain hierarchical data that can't be directly visualized in brain visualization software. Instead, you'll need to extract data and create custom visualizations.

### Examining HDF5 Structure

First, examine the file structure:

```bash
./run_container.sh run -v $(pwd)/pipeline_outputs:/data/output h5ls -r /data/output/sub-17017/func/Analytical_metrics/QM_FFT/sub-17017_qm_fft.h5
```

### Python Visualization Examples

#### QM-FFT Visualization

```python
import h5py
import numpy as np
import matplotlib.pyplot as plt
import nibabel as nib

# Load QM-FFT data
with h5py.File('sub-17017_qm_fft.h5', 'r') as f:
    # Get magnitude data
    magnitude = f['/analysis/map_0_magnitude'][:]
    phase = f['/analysis/map_0_phase'][:]
    
    # Load a brain mask to reshape data to 3D
    mask = nib.load('sub-17017_brain_mask.nii.gz')
    mask_data = mask.get_fdata() > 0
    
    # Create empty 3D volumes
    mag_vol = np.zeros(mask_data.shape)
    phase_vol = np.zeros(mask_data.shape)
    
    # Fill masked locations with data
    mag_vol[mask_data] = magnitude
    phase_vol[mask_data] = phase
    
    # Create NIfTI images
    mag_nii = nib.Nifti1Image(mag_vol, mask.affine)
    phase_nii = nib.Nifti1Image(phase_vol, mask.affine)
    
    # Save as NIfTI for visualization in FSLeyes or other viewers
    nib.save(mag_nii, 'qm_fft_magnitude.nii.gz')
    nib.save(phase_nii, 'qm_fft_phase.nii.gz')
    
    # Plot slices
    plt.figure(figsize=(12, 5))
    
    # Plot magnitude
    plt.subplot(121)
    plt.imshow(mag_vol[:, :, 50], cmap='hot')
    plt.colorbar()
    plt.title('QM-FFT Magnitude (Axial Slice)')
    
    # Plot phase
    plt.subplot(122)
    plt.imshow(phase_vol[:, :, 50], cmap='hsv')
    plt.colorbar()
    plt.title('QM-FFT Phase (Axial Slice)')
    
    plt.tight_layout()
    plt.savefig('qm_fft_visualization.png', dpi=300)
```

#### RSN Time Series Visualization

```python
import h5py
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec

# Load RSN data
with h5py.File('sub-17017_rsn_activity.h5', 'r') as f:
    # Extract 7-network time series
    networks = []
    network_names = ['Visual', 'Somatomotor', 'Dorsal Attention', 
                     'Ventral Attention', 'Limbic', 'Frontoparietal', 'Default']
    
    for name in network_names:
        networks.append(f[f'/networks_7/{name}'][:])
    
    networks = np.array(networks)
    
    # Create a comprehensive visualization
    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(2, 2, figure=fig)
    
    # 1. Plot time series
    ax1 = fig.add_subplot(gs[0, :])
    for i, name in enumerate(network_names):
        ax1.plot(networks[i], label=name)
    ax1.set_xlabel('Time Points')
    ax1.set_ylabel('BOLD Signal (standardized)')
    ax1.set_title('RSN Time Series for 7 Networks')
    ax1.legend(loc='upper right')
    
    # 2. Plot correlation matrix
    ax2 = fig.add_subplot(gs[1, 0])
    corr_matrix = np.corrcoef(networks)
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1,
                xticklabels=network_names, yticklabels=network_names, ax=ax2)
    ax2.set_title('Network Correlation Matrix')
    
    # 3. Plot power spectrum (frequency domain)
    ax3 = fig.add_subplot(gs[1, 1])
    for i, name in enumerate(network_names):
        # Calculate frequency spectrum
        signal = networks[i]
        fft_vals = np.abs(np.fft.rfft(signal))
        fft_freq = np.fft.rfftfreq(len(signal), d=2.0)  # Assuming TR=2s
        
        # Plot only frequencies below 0.1 Hz
        mask = fft_freq < 0.1
        ax3.plot(fft_freq[mask], fft_vals[mask], label=name)
    
    ax3.set_xlabel('Frequency (Hz)')
    ax3.set_ylabel('Power')
    ax3.set_title('RSN Power Spectrum (< 0.1 Hz)')
    ax3.legend()
    
    plt.tight_layout()
    plt.savefig('rsn_comprehensive_viz.png', dpi=300)
```

## Creating Publication-Ready Figures

### Multi-Subject Comparison

The following Python script creates a publication-ready figure comparing ALFF maps across multiple subjects:

```python
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
from nilearn import plotting
import glob

# Get all ALFF files
alff_files = glob.glob('/path/to/output/sub-*/func/Analytical_metrics/ALFF/sub-*_alff.nii.gz')
subject_ids = [f.split('/')[-1].split('_')[0] for f in alff_files]

# Create a figure
fig, axes = plt.subplots(len(subject_ids), 3, figsize=(15, 5*len(subject_ids)))

# Selected slices to display
slices = {'sagittal': 91, 'coronal': 91, 'axial': 91}

# For each subject
for i, (subject, file) in enumerate(zip(subject_ids, alff_files)):
    # Load the data
    img = nib.load(file)
    
    # Display slices
    if len(subject_ids) > 1:
        # Sagittal view
        plotting.plot_img(img, cut_coords=[slices['sagittal']], display_mode='x',
                         colorbar=True, cmap='hot', vmin=2, vmax=8,
                         axes=axes[i, 0], title=f"{subject} - Sagittal")
        
        # Coronal view
        plotting.plot_img(img, cut_coords=[slices['coronal']], display_mode='y',
                         colorbar=True, cmap='hot', vmin=2, vmax=8,
                         axes=axes[i, 1], title=f"{subject} - Coronal")
        
        # Axial view
        plotting.plot_img(img, cut_coords=[slices['axial']], display_mode='z',
                         colorbar=True, cmap='hot', vmin=2, vmax=8,
                         axes=axes[i, 2], title=f"{subject} - Axial")
    else:
        # Handle single subject case
        plotting.plot_img(img, cut_coords=[slices['sagittal']], display_mode='x',
                         colorbar=True, cmap='hot', vmin=2, vmax=8,
                         axes=axes[0], title=f"{subject} - Sagittal")
        
        plotting.plot_img(img, cut_coords=[slices['coronal']], display_mode='y',
                         colorbar=True, cmap='hot', vmin=2, vmax=8,
                         axes=axes[1], title=f"{subject} - Coronal")
        
        plotting.plot_img(img, cut_coords=[slices['axial']], display_mode='z',
                         colorbar=True, cmap='hot', vmin=2, vmax=8,
                         axes=axes[2], title=f"{subject} - Axial")

plt.tight_layout()
plt.savefig('alff_multi_subject_comparison.png', dpi=300)
```

### Comparison Across Features

To compare different features on the same brain:

```python
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
from nilearn import plotting

# Define metrics to compare
metrics = {
    'ALFF': '/path/to/output/sub-17017/func/Analytical_metrics/ALFF/sub-17017_alff.nii.gz',
    'ReHo': '/path/to/output/sub-17017/func/Analytical_metrics/ReHo/sub-17017_reho.nii.gz',
    'Hurst': '/path/to/output/sub-17017/func/Analytical_metrics/Hurst/sub-17017_hurst.nii.gz',
    'Fractal': '/path/to/output/sub-17017/func/Analytical_metrics/Fractal/sub-17017_fractal.nii.gz'
}

# Create a figure
fig, axes = plt.subplots(len(metrics), 1, figsize=(12, 4*len(metrics)))

# Display glass brain view for each metric
for i, (name, file) in enumerate(metrics.items()):
    img = nib.load(file)
    
    # Choose appropriate threshold and colormap for each metric
    if name == 'ALFF' or name == 'ReHo':
        vmin, vmax = 2, 8
        cmap = 'hot'
    elif name == 'Hurst':
        vmin, vmax = 0.4, 0.8
        cmap = 'RdBu_r'
    else:  # Fractal
        vmin, vmax = 1.0, 2.0
        cmap = 'viridis'
    
    plotting.plot_glass_brain(
        img, colorbar=True, display_mode='lyrz',
        title=f"{name} - Subject 17017",
        threshold=vmin, vmax=vmax, cmap=cmap,
        axes=axes[i] if len(metrics) > 1 else axes
    )

plt.tight_layout()
plt.savefig('feature_comparison_glass_brain.png', dpi=300)
```

## Batch Processing and Visualization

### Creating a Group Average Map

This script produces a group average ALFF map:

```python
import nibabel as nib
import numpy as np
import os
import glob
from nilearn import image, plotting

# Find all ALFF files
alff_files = glob.glob('/path/to/output/sub-*/func/Analytical_metrics/ALFF/sub-*_alff.nii.gz')

# Load all images
images = [nib.load(f) for f in alff_files]

# Create mean image
mean_img = image.mean_img(images)

# Save the mean image
output_dir = '/path/to/group_results'
os.makedirs(output_dir, exist_ok=True)
nib.save(mean_img, os.path.join(output_dir, 'group_mean_alff.nii.gz'))

# Create a visualization
plotting.plot_stat_map(
    mean_img, 
    display_mode='ortho', 
    cut_coords=(0, 0, 0),
    colorbar=True,
    title='Group Average ALFF'
)
plt.savefig(os.path.join(output_dir, 'group_mean_alff.png'), dpi=300)
```

### Automated Report Generation

This script generates an HTML report with all key visualizations:

```python
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from nilearn import plotting
import h5py
import pandas as pd
import seaborn as sns
from IPython.display import HTML
from jinja2 import Template

# Define paths
output_base = '/path/to/output'
subject_id = 'sub-17017'
report_dir = '/path/to/reports'
os.makedirs(report_dir, exist_ok=True)

# Define paths to each output
alff_file = f"{output_base}/{subject_id}/func/Analytical_metrics/ALFF/{subject_id}_alff.nii.gz"
falff_file = f"{output_base}/{subject_id}/func/Analytical_metrics/ALFF/{subject_id}_falff.nii.gz"
reho_file = f"{output_base}/{subject_id}/func/Analytical_metrics/ReHo/{subject_id}_reho.nii.gz"
hurst_file = f"{output_base}/{subject_id}/func/Analytical_metrics/Hurst/{subject_id}_hurst.nii.gz"
fractal_file = f"{output_base}/{subject_id}/func/Analytical_metrics/Fractal/{subject_id}_fractal.nii.gz"
qm_fft_file = f"{output_base}/{subject_id}/func/Analytical_metrics/QM_FFT/{subject_id}_qm_fft.h5"
rsn_file = f"{output_base}/{subject_id}/func/Analytical_metrics/RSN/{subject_id}_rsn_activity.h5"

# Create figures for each output
figure_paths = {}

# ALFF and fALFF
for name, file in [('ALFF', alff_file), ('fALFF', falff_file)]:
    fig_path = f"{report_dir}/{subject_id}_{name.lower()}.png"
    plotting.plot_stat_map(
        file, 
        display_mode='ortho', 
        colorbar=True,
        title=f"{name} - {subject_id}"
    )
    plt.savefig(fig_path, dpi=150)
    plt.close()
    figure_paths[name] = os.path.basename(fig_path)

# ReHo
fig_path = f"{report_dir}/{subject_id}_reho.png"
plotting.plot_stat_map(
    reho_file, 
    display_mode='ortho', 
    colorbar=True,
    title=f"ReHo - {subject_id}"
)
plt.savefig(fig_path, dpi=150)
plt.close()
figure_paths['ReHo'] = os.path.basename(fig_path)

# Hurst Exponent
fig_path = f"{report_dir}/{subject_id}_hurst.png"
plotting.plot_stat_map(
    hurst_file, 
    display_mode='ortho', 
    colorbar=True,
    cmap='RdBu_r',
    title=f"Hurst Exponent - {subject_id}"
)
plt.savefig(fig_path, dpi=150)
plt.close()
figure_paths['Hurst'] = os.path.basename(fig_path)

# Fractal Dimension
fig_path = f"{report_dir}/{subject_id}_fractal.png"
plotting.plot_stat_map(
    fractal_file, 
    display_mode='ortho', 
    colorbar=True,
    cmap='viridis',
    title=f"Fractal Dimension - {subject_id}"
)
plt.savefig(fig_path, dpi=150)
plt.close()
figure_paths['Fractal'] = os.path.basename(fig_path)

# RSN Time Series
with h5py.File(rsn_file, 'r') as f:
    # Extract 7-network time series
    networks = []
    network_names = ['Visual', 'Somatomotor', 'Dorsal Attention', 
                    'Ventral Attention', 'Limbic', 'Frontoparietal', 'Default']
    
    for name in network_names:
        networks.append(f[f'/networks_7/{name}'][:])
    
    networks = np.array(networks)
    
    fig_path = f"{report_dir}/{subject_id}_rsn_timeseries.png"
    plt.figure(figsize=(10, 6))
    for i, name in enumerate(network_names):
        plt.plot(networks[i], label=name)
    plt.xlabel('Time Points')
    plt.ylabel('BOLD Signal (standardized)')
    plt.title('RSN Time Series')
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
    figure_paths['RSN_TimeSeries'] = os.path.basename(fig_path)
    
    # Network Correlation Matrix
    fig_path = f"{report_dir}/{subject_id}_rsn_correlation.png"
    plt.figure(figsize=(8, 7))
    corr_matrix = np.corrcoef(networks)
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1,
                xticklabels=network_names, yticklabels=network_names)
    plt.title('Network Correlation Matrix')
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
    figure_paths['RSN_Correlation'] = os.path.basename(fig_path)

# Create HTML report using Jinja2 template
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ subject_id }} - Feature Extraction Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #2c3e50; }
        .section { margin-bottom: 30px; }
        .figure { margin: 10px 0; text-align: center; }
        img { max-width: 100%; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>fMRI Feature Extraction Report: {{ subject_id }}</h1>
    
    <div class="section">
        <h2>ALFF and fALFF</h2>
        <div class="figure">
            <img src="{{ alff_img }}" alt="ALFF Map">
            <p>ALFF Map - Amplitude of Low-Frequency Fluctuations</p>
        </div>
        <div class="figure">
            <img src="{{ falff_img }}" alt="fALFF Map">
            <p>fALFF Map - Fractional Amplitude of Low-Frequency Fluctuations</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Regional Homogeneity (ReHo)</h2>
        <div class="figure">
            <img src="{{ reho_img }}" alt="ReHo Map">
            <p>ReHo Map - Regional Homogeneity</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Hurst Exponent</h2>
        <div class="figure">
            <img src="{{ hurst_img }}" alt="Hurst Map">
            <p>Hurst Exponent Map</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Fractal Dimension</h2>
        <div class="figure">
            <img src="{{ fractal_img }}" alt="Fractal Map">
            <p>Fractal Dimension Map</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Resting State Networks</h2>
        <div class="figure">
            <img src="{{ rsn_ts_img }}" alt="RSN Time Series">
            <p>RSN Time Series for 7 Networks</p>
        </div>
        <div class="figure">
            <img src="{{ rsn_corr_img }}" alt="RSN Correlation Matrix">
            <p>RSN Network Correlation Matrix</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <p>Report generated on {{ date }}.</p>
        <p>Full data available in: {{ output_path }}</p>
    </div>
</body>
</html>
"""

# Fill the template
import datetime
template = Template(html_template)
html_content = template.render(
    subject_id=subject_id,
    alff_img=figure_paths['ALFF'],
    falff_img=figure_paths['fALFF'],
    reho_img=figure_paths['ReHo'],
    hurst_img=figure_paths['Hurst'],
    fractal_img=figure_paths['Fractal'],
    rsn_ts_img=figure_paths['RSN_TimeSeries'],
    rsn_corr_img=figure_paths['RSN_Correlation'],
    date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    output_path=output_base
)

# Save the HTML report
with open(f"{report_dir}/{subject_id}_report.html", 'w') as f:
    f.write(html_content)

print(f"Report generated: {report_dir}/{subject_id}_report.html")
```

This automated report provides a comprehensive overview of all features extracted for a subject, making it easy to review results at a glance.

## Conclusion

Proper visualization is crucial for interpreting the complex outputs of fMRI feature extraction. By combining 3D brain visualization tools with custom Python scripts, you can create detailed visualizations that highlight the unique insights provided by each analytical metric.

For further assistance with visualization, consider exploring dedicated neuroimaging visualization packages such as:

- **nilearn**: Python library for neuroimaging data analysis and visualization
- **pysurfer**: Surface visualization of neuroimaging data
- **brainspace**: Toolbox for macroscale gradient mapping and visualization 
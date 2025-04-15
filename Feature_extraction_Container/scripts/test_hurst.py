#!/usr/bin/env python3
import nibabel as nib
import numpy as np
import nolds
import os
import matplotlib.pyplot as plt
from scipy import signal

# File paths
fmri_file = '/media/brainlab-uwo/Data1/Results/pipeline_test_3/sub-17017/func/sub-17017_task-rest_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz'
hurst_file = 'outputs/sub-17017/metrics/hurst.nii.gz'
output_dir = 'outputs/hurst_analysis'

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Load the fMRI data and computed Hurst map
print(f"Loading fMRI data from {fmri_file}")
fmri_img = nib.load(fmri_file)
fmri_data = fmri_img.get_fdata()
nx, ny, nz, nt = fmri_data.shape
print(f"fMRI dimensions: {nx} x {ny} x {nz} x {nt}")

print(f"Loading Hurst map from {hurst_file}")
hurst_img = nib.load(hurst_file)
hurst_data = hurst_img.get_fdata()
print(f"Hurst map dimensions: {hurst_data.shape}")

# Check affine transformation matrices
print("fMRI affine:")
print(fmri_img.affine)
print("Hurst affine:")
print(hurst_img.affine)

# Basic statistics of Hurst map
non_zero_hurst = hurst_data[hurst_data > 0]
print(f"Min non-zero Hurst: {np.min(non_zero_hurst)}")
print(f"Max Hurst: {np.max(hurst_data)}")
print(f"Mean Hurst (non-zero): {np.mean(non_zero_hurst)}")
print(f"Median Hurst (non-zero): {np.median(non_zero_hurst)}")
print(f"Non-zero voxel count: {len(non_zero_hurst)}")
print(f"Total brain voxels: {np.prod(hurst_data.shape)}")

# Select a few voxels for validation
print("\nValidating specific voxels:")
test_coords = [
    (nx//2, ny//2, nz//2),  # Center
    (nx//2+5, ny//2, nz//2),  # Offset
    (nx//2, ny//2+5, nz//2),  # Offset
    (nx//2, ny//2, nz//2+5)   # Offset
]

for coords in test_coords:
    x, y, z = coords
    ts = fmri_data[x, y, z, :]
    stored_hurst = hurst_data[x, y, z]
    
    # Skip if time series has no variance
    if np.std(ts) <= 1e-6:
        print(f"Voxel at {coords} has no variance, skipping")
        continue
    
    print(f"\nVoxel at {coords}:")
    print(f"  Stored Hurst: {stored_hurst}")
    
    try:
        # Recompute Hurst exponent
        recomputed_hurst = nolds.hurst_rs(ts)
        print(f"  Recomputed Hurst: {recomputed_hurst}")
        
        # Check if values match within tolerance
        tol = 1e-6
        if abs(stored_hurst - recomputed_hurst) < tol:
            print(f"  MATCH: Values match within tolerance of {tol}")
        else:
            print(f"  MISMATCH: Values differ by {abs(stored_hurst - recomputed_hurst)}")
            
        # Plot the time series
        plt.figure(figsize=(10, 6))
        plt.plot(ts)
        plt.title(f"Time Series at {coords}, Hurst={recomputed_hurst:.4f}")
        plt.xlabel("Time Point")
        plt.ylabel("BOLD Signal")
        plt.grid(True)
        plt.savefig(f"{output_dir}/timeseries_{x}_{y}_{z}.png")
        plt.close()
        
        # Save time series to CSV
        np.savetxt(f"{output_dir}/timeseries_{x}_{y}_{z}.csv", ts, delimiter=',')
        
    except Exception as e:
        print(f"  ERROR: {e}")

# Create a histogram of Hurst values
plt.figure(figsize=(10, 6))
plt.hist(non_zero_hurst, bins=50)
plt.title("Distribution of Hurst Exponent Values")
plt.xlabel("Hurst Exponent")
plt.ylabel("Count")
plt.grid(True)
plt.savefig(f"{output_dir}/hurst_histogram.png")
plt.close()

# Create a 2D slice showing Hurst values
slice_z = nz // 2
plt.figure(figsize=(10, 8))
plt.imshow(hurst_data[:, :, slice_z], cmap='viridis')
plt.colorbar(label='Hurst Exponent')
plt.title(f"Hurst Exponent Map (z={slice_z})")
plt.savefig(f"{output_dir}/hurst_slice_z{slice_z}.png")
plt.close()

print("\nAnalysis complete. Results saved to:", output_dir) 
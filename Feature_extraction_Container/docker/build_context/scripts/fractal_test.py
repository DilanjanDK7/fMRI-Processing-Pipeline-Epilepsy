#!/usr/bin/env python3
import argparse
import nibabel as nib
import numpy as np
import os

def extract_fractal_dimension(signal: np.ndarray) -> float:
    """Extract fractal dimension using Higuchi's method."""
    # Normalize the signal
    signal = (signal - np.mean(signal)) / np.std(signal)
    
    # Parameters for Higuchi's method
    k_max = 10
    k_values = np.arange(1, k_max + 1)
    length_values = []
    
    # Calculate length for different k values
    for k in k_values:
        length = compute_curve_length(signal, k)
        length_values.append(length)
    
    # Compute fractal dimension from the slope
    if len(length_values) > 1:
        log_length = np.log(length_values)
        log_k = np.log(1.0 / k_values)
        fd = -np.polyfit(log_k, log_length, 1)[0]
        return max(1.0, fd)  # Ensure value is at least 1
    else:
        return 1.0  # Return 1.0 if calculation fails

def compute_curve_length(signal: np.ndarray, k: int) -> float:
    """Compute curve length for Higuchi's method."""
    n = len(signal)
    length = 0.0
    
    # Calculate length for each m
    for m in range(k):
        # Extract subsequence
        indices = np.arange(0, (n-m-1)//k*k + 1, k)
        subsequence = signal[indices + m]
        
        # Calculate normalized length
        diff = np.abs(np.diff(subsequence))
        norm = ((n-1) / (((n-m-1)//k)*k)) * (k/1.0)
        length += np.sum(diff) * norm
    
    return length / k

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmri", required=True, help="Path to input fMRI file")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--sample", action="store_true", help="Process only a sample region for testing")
    args = parser.parse_args()
    
    print(f"Loading fMRI data from {args.fmri}")
    img = nib.load(args.fmri)
    data = img.get_fdata()
    affine = img.affine
    
    # Get dimensions
    nx, ny, nz, nt = data.shape
    print(f"Data dimensions: {nx} x {ny} x {nz} x {nt}")
    
    # Create mask (simplified for testing)
    print("Creating mask based on signal variance")
    variance = np.var(data, axis=3)
    mask = variance > np.percentile(variance, 10)
    
    # Initialize output
    fractal_map = np.zeros((nx, ny, nz))
    
    # Process only a central region if sample mode is on
    if args.sample:
        print("Processing sample region only (for testing)")
        x_range = slice(nx//2-5, nx//2+5)
        y_range = slice(ny//2-5, ny//2+5)
        z_range = slice(nz//2-2, nz//2+2)
        
        masked_indices = []
        for x in range(nx//2-5, nx//2+5):
            for y in range(ny//2-5, ny//2+5):
                for z in range(nz//2-2, nz//2+2):
                    if mask[x, y, z]:
                        masked_indices.append((x, y, z))
    else:
        # Get all masked voxels
        masked_indices = np.argwhere(mask)
    
    total_voxels = len(masked_indices)
    print(f"Processing {total_voxels} voxels")
    
    # Loop through voxels (with progress updates)
    for i, index in enumerate(masked_indices):
        if isinstance(index, tuple):
            x, y, z = index
        else:
            x, y, z = index[0], index[1], index[2]
            
        if i % max(1, total_voxels // 10) == 0:
            print(f"Progress: {100.0 * i / total_voxels:.1f}% ({i}/{total_voxels} voxels)")
        
        # Get time series
        ts = data[x, y, z, :]
        
        # Skip if time series has no variance
        if np.std(ts) <= 1e-6:
            continue
        
        # Compute fractal dimension
        try:
            fd = extract_fractal_dimension(ts)
            fractal_map[x, y, z] = fd
        except Exception as e:
            print(f"Error computing fractal dimension at ({x},{y},{z}): {e}")
    
    # Save output
    print(f"Saving fractal dimension map to {args.output}")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    out_img = nib.Nifti1Image(fractal_map, affine)
    nib.save(out_img, args.output)
    print("Fractal dimension computation completed successfully")

if __name__ == "__main__":
    main() 
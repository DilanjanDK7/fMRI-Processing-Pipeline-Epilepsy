#!/usr/bin/env python3
"""
Script to compute Hurst exponent from fMRI data.
"""

import os
import argparse
import time
import numpy as np
import nibabel as nib
import nolds  # For Hurst exponent calculation


def compute_hurst(fmri_file, output_file, method='dfa', mask_file=None):
    """
    Compute Hurst exponent from fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    output_file : str
        Path to save the Hurst exponent output
    method : str, optional
        Method for Hurst exponent calculation ('dfa' or 'rs'). Default is 'dfa'.
    mask_file : str, optional
        Path to a brain mask. If not provided, a mask will be created based on signal variance.
    """
    print("Starting Hurst exponent calculation...")
    start_time = time.time()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load fMRI data
    print(f"Loading fMRI data from {fmri_file}...")
    img = nib.load(fmri_file)
    data = img.get_fdata()
    affine = img.affine
    header = img.header
    
    # Get dimensions
    nx, ny, nz, nt = data.shape
    print(f"Data dimensions: {nx} x {ny} x {nz} x {nt}")
    
    # Create or load mask
    if mask_file:
        print(f"Loading mask from {mask_file}...")
        mask_img = nib.load(mask_file)
        mask = mask_img.get_fdata() > 0
    else:
        print("Creating mask from fMRI data...")
        # Simple mask: voxels with non-zero variance
        mask = np.std(data, axis=3) > 0
    
    # Ensure mask dimensions match
    if mask.shape[:3] != data.shape[:3]:
        raise ValueError("Mask dimensions do not match fMRI data dimensions")
    
    # Create Hurst exponent map
    print(f"Calculating Hurst exponent using {method} method...")
    hurst_map = np.zeros((nx, ny, nz))
    
    # Loop through masked voxels
    total_voxels = np.sum(mask)
    processed_voxels = 0
    last_update = 0
    
    # Set Hurst calculation method
    if method == 'dfa':
        hurst_func = nolds.dfa
    elif method == 'rs':
        hurst_func = nolds.hurst_rs
    else:
        print(f"Unknown method {method}. Using DFA (detrended fluctuation analysis).")
        hurst_func = nolds.dfa
    
    for x in range(nx):
        for y in range(ny):
            for z in range(nz):
                if mask[x, y, z]:
                    # Get time series for this voxel
                    ts = data[x, y, z, :]
                    
                    # Skip if time series has no variance
                    if np.std(ts) <= 1e-6:
                        continue
                    
                    try:
                        # Calculate Hurst exponent
                        hurst_map[x, y, z] = hurst_func(ts)
                    except Exception as e:
                        # If calculation fails, set to NaN
                        hurst_map[x, y, z] = np.nan
                        print(f"Error calculating Hurst at ({x},{y},{z}): {e}")
                    
                    processed_voxels += 1
                    
                    # Update progress every 5%
                    progress = processed_voxels / total_voxels
                    if progress - last_update >= 0.05:
                        print(f"Progress: {progress * 100:.1f}% ({processed_voxels}/{total_voxels} voxels)")
                        last_update = progress
    
    # Replace NaNs with 0
    hurst_map = np.nan_to_num(hurst_map)
    
    # Normalize Hurst map for visualization (z-score)
    brain_mask = (hurst_map > 0) & (hurst_map < 2)  # Valid Hurst range
    if np.sum(brain_mask) > 0:
        mean_hurst = np.mean(hurst_map[brain_mask])
        std_hurst = np.std(hurst_map[brain_mask])
        if std_hurst > 0:
            hurst_map_norm = np.zeros_like(hurst_map)
            hurst_map_norm[brain_mask] = (hurst_map[brain_mask] - mean_hurst) / std_hurst
            
            # Save both raw and normalized maps
            print(f"Saving Hurst exponent map to {output_file}...")
            hurst_img = nib.Nifti1Image(hurst_map, affine, header)
            nib.save(hurst_img, output_file)
            
            norm_output = output_file.replace('.nii.gz', '_norm.nii.gz')
            print(f"Saving normalized Hurst exponent map to {norm_output}...")
            hurst_norm_img = nib.Nifti1Image(hurst_map_norm, affine, header)
            nib.save(hurst_norm_img, norm_output)
        else:
            print("Warning: Standard deviation is zero, cannot normalize.")
            hurst_img = nib.Nifti1Image(hurst_map, affine, header)
            nib.save(hurst_img, output_file)
    else:
        print("Warning: No valid Hurst exponents calculated.")
        hurst_img = nib.Nifti1Image(hurst_map, affine, header)
        nib.save(hurst_img, output_file)
    
    elapsed_time = time.time() - start_time
    print(f"Hurst exponent calculation completed in {elapsed_time:.2f} seconds")
    
    return output_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute Hurst exponent from fMRI data')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output', required=True, help='Output Hurst exponent file')
    parser.add_argument('--method', choices=['dfa', 'rs'], default='dfa',
                      help='Method for Hurst calculation (dfa or rs). Default is dfa.')
    parser.add_argument('--mask', help='Brain mask (optional, will be created if not provided)')
    
    args = parser.parse_args()
    
    compute_hurst(args.fmri, args.output, args.method, args.mask) 
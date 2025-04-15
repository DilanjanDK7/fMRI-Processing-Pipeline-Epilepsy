#!/usr/bin/env python3
"""
Script to compute Fractal Dimension from fMRI data.
"""

import os
import argparse
import time
import numpy as np
import nibabel as nib
from scipy import signal


def compute_higuchi_fd(ts, kmax=10):
    """
    Compute Higuchi Fractal Dimension of a time series.
    
    Parameters:
    -----------
    ts : numpy.ndarray
        Input time series
    kmax : int
        Maximum delay/lag. Default is 10.
        
    Returns:
    --------
    float
        Higuchi Fractal Dimension
    """
    n = len(ts)
    lk = np.zeros(kmax)
    x_reg = np.array(range(kmax))
    y_reg = np.zeros(kmax)
    
    for k in range(1, kmax + 1):
        lm = np.zeros(k)
        
        for m in range(k):
            # Construct subsequence
            ll = 0
            
            # Number of subsequences
            n_m = int((n - m) / k)
            
            for i in range(1, n_m):
                ll += abs(ts[m + i * k] - ts[m + (i - 1) * k])
            
            ll /= k  # Normalize with factor k
            # Length for subsequence starting at m
            lm[m] = ll * (n - 1) / (n_m * k)
        
        # Mean length for step k
        lk[k - 1] = np.mean(lm)
        y_reg[k - 1] = np.log(lk[k - 1])
    
    x_reg = np.log(1.0 / np.array(range(1, kmax + 1)))
    
    # Perform linear regression
    slopes = np.polyfit(x_reg, y_reg, 1)
    
    # Return the slope (fractal dimension)
    return slopes[0]


def compute_psd_fd(ts):
    """
    Compute Fractal Dimension using Power Spectral Density (PSD) method.
    
    Parameters:
    -----------
    ts : numpy.ndarray
        Input time series
        
    Returns:
    --------
    float
        Fractal Dimension from PSD slope
    """
    # Remove mean
    ts = ts - np.mean(ts)
    
    # Compute PSD using Welch's method
    freqs, psd = signal.welch(ts, nperseg=min(256, len(ts)//4))
    
    # Avoid zero frequency and use only positive frequencies
    mask = (freqs > 0)
    freqs = freqs[mask]
    psd = psd[mask]
    
    # Perform linear regression in log-log space
    if len(freqs) > 5:  # Ensure enough points for regression
        slopes = np.polyfit(np.log10(freqs), np.log10(psd), 1)
        
        # Calculate fractal dimension from PSD slope
        # FD = (5 - beta) / 2, where beta is the negative of the slope
        beta = -slopes[0]
        fd = (5 - beta) / 2
        return fd
    else:
        return np.nan


def compute_fractal(fmri_file, output_file, method='higuchi', kmax=10, mask_file=None):
    """
    Compute Fractal Dimension from fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    output_file : str
        Path to save the Fractal Dimension output
    method : str, optional
        Method for fractal dimension calculation ('higuchi' or 'psd'). Default is 'higuchi'.
    kmax : int, optional
        Maximum lag parameter for Higuchi method. Default is 10.
    mask_file : str, optional
        Path to a brain mask. If not provided, a mask will be created based on signal variance.
    """
    print("Starting Fractal Dimension calculation...")
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
    
    # Create Fractal Dimension map
    print(f"Calculating Fractal Dimension using {method} method...")
    fd_map = np.zeros((nx, ny, nz))
    
    # Set fractal dimension calculation method
    if method == 'higuchi':
        fd_func = lambda ts: compute_higuchi_fd(ts, kmax)
    elif method == 'psd':
        fd_func = compute_psd_fd
    else:
        print(f"Unknown method {method}. Using Higuchi method.")
        fd_func = lambda ts: compute_higuchi_fd(ts, kmax)
    
    # Loop through masked voxels
    total_voxels = np.sum(mask)
    processed_voxels = 0
    last_update = 0
    
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
                        # Calculate fractal dimension
                        fd_map[x, y, z] = fd_func(ts)
                    except Exception as e:
                        # If calculation fails, set to NaN
                        fd_map[x, y, z] = np.nan
                        print(f"Error calculating fractal dimension at ({x},{y},{z}): {e}")
                    
                    processed_voxels += 1
                    
                    # Update progress every 5%
                    progress = processed_voxels / total_voxels
                    if progress - last_update >= 0.05:
                        print(f"Progress: {progress * 100:.1f}% ({processed_voxels}/{total_voxels} voxels)")
                        last_update = progress
    
    # Replace NaNs with 0
    fd_map = np.nan_to_num(fd_map)
    
    # Normalize fractal dimension map for visualization (z-score)
    # Valid fractal dimension range for most physiological signals
    brain_mask = (fd_map > 1.0) & (fd_map < 2.0)
    if np.sum(brain_mask) > 0:
        mean_fd = np.mean(fd_map[brain_mask])
        std_fd = np.std(fd_map[brain_mask])
        if std_fd > 0:
            fd_map_norm = np.zeros_like(fd_map)
            fd_map_norm[brain_mask] = (fd_map[brain_mask] - mean_fd) / std_fd
            
            # Save both raw and normalized maps
            print(f"Saving Fractal Dimension map to {output_file}...")
            fd_img = nib.Nifti1Image(fd_map, affine, header)
            nib.save(fd_img, output_file)
            
            norm_output = output_file.replace('.nii.gz', '_norm.nii.gz')
            print(f"Saving normalized Fractal Dimension map to {norm_output}...")
            fd_norm_img = nib.Nifti1Image(fd_map_norm, affine, header)
            nib.save(fd_norm_img, norm_output)
        else:
            print("Warning: Standard deviation is zero, cannot normalize.")
            fd_img = nib.Nifti1Image(fd_map, affine, header)
            nib.save(fd_img, output_file)
    else:
        print("Warning: No valid fractal dimensions calculated.")
        fd_img = nib.Nifti1Image(fd_map, affine, header)
        nib.save(fd_img, output_file)
    
    elapsed_time = time.time() - start_time
    print(f"Fractal Dimension calculation completed in {elapsed_time:.2f} seconds")
    
    return output_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute Fractal Dimension from fMRI data')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output', required=True, help='Output Fractal Dimension file')
    parser.add_argument('--method', choices=['higuchi', 'psd'], default='higuchi',
                      help='Method for fractal dimension calculation (higuchi or psd). Default is higuchi.')
    parser.add_argument('--kmax', type=int, default=10, help='Maximum lag for Higuchi method. Default is 10.')
    parser.add_argument('--mask', help='Brain mask (optional, will be created if not provided)')
    
    args = parser.parse_args()
    
    compute_fractal(args.fmri, args.output, args.method, args.kmax, args.mask) 
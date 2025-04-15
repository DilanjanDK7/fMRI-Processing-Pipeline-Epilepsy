#!/usr/bin/env python3
import argparse
import os
import time
import numpy as np
import nibabel as nib
from scipy import fft
from scipy.signal import butter, filtfilt


def compute_alff(fmri_file, output_file, tr, bandpass_low=0.01, bandpass_high=0.08, mask_file=None):
    """
    Compute ALFF from fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the fMRI file.
    output_file : str
        Path to save the ALFF map.
    tr : float
        Repetition time of the fMRI data in seconds.
    bandpass_low : float, optional
        Lower frequency bound for bandpass filter in Hz. Default is 0.01 Hz.
    bandpass_high : float, optional
        Upper frequency bound for bandpass filter in Hz. Default is 0.08 Hz.
    mask_file : str, optional
        Path to a binary mask file. If None, a mask will be created from the fMRI data.
    """
    print("Starting ALFF calculation...")
    start_time = time.time()
    
    # Load fMRI data
    print(f"Loading fMRI data from {fmri_file}...")
    fmri_img = nib.load(fmri_file)
    fmri_data = fmri_img.get_fdata()
    
    # Get dimensions
    nx, ny, nz, nt = fmri_data.shape
    
    # Create or load mask
    if mask_file:
        print(f"Loading mask from {mask_file}...")
        mask_img = nib.load(mask_file)
        mask = mask_img.get_fdata() > 0
    else:
        print("Creating mask from fMRI data...")
        # Simple mask: voxels with non-zero variance
        mask = np.std(fmri_data, axis=3) > 0
    
    # Ensure mask dimensions match
    if mask.shape[:3] != fmri_data.shape[:3]:
        raise ValueError("Mask dimensions do not match fMRI data dimensions")
    
    # Create ALFF map
    print("Calculating ALFF...")
    alff_map = np.zeros((nx, ny, nz))
    
    # Frequency information
    sample_freq = 1. / tr
    freq_bins = fft.rfftfreq(nt, d=tr)
    
    # Find frequency band indices
    freq_idx = np.where((freq_bins >= bandpass_low) & (freq_bins <= bandpass_high))[0]
    
    # Process voxels
    total_voxels = np.sum(mask)
    processed_voxels = 0
    last_update = 0
    
    for x in range(nx):
        for y in range(ny):
            for z in range(nz):
                if mask[x, y, z]:
                    # Get time series for this voxel
                    ts = fmri_data[x, y, z, :]
                    
                    # Remove linear trend
                    ts = detrend(ts)
                    
                    # Compute FFT
                    fft_vals = np.abs(fft.rfft(ts))
                    
                    # Calculate ALFF (sum of amplitudes in frequency band)
                    alff_map[x, y, z] = np.sum(fft_vals[freq_idx]) / len(freq_idx)
                    
                    processed_voxels += 1
                    
                    # Update progress every 5%
                    progress = processed_voxels / total_voxels
                    if progress - last_update >= 0.05:
                        print(f"Progress: {progress * 100:.1f}% ({processed_voxels}/{total_voxels} voxels)")
                        last_update = progress
    
    # Normalize ALFF for visualization (z-score)
    mask_alff = alff_map[mask]
    mean_alff = np.mean(mask_alff)
    std_alff = np.std(mask_alff)
    alff_map_norm = np.zeros_like(alff_map)
    alff_map_norm[mask] = (mask_alff - mean_alff) / std_alff
    
    # Save ALFF map
    print(f"Saving ALFF map to {output_file}...")
    alff_img = nib.Nifti1Image(alff_map_norm, fmri_img.affine, fmri_img.header)
    nib.save(alff_img, output_file)
    
    elapsed_time = time.time() - start_time
    print(f"ALFF calculation completed in {elapsed_time:.2f} seconds")
    
    return output_file


def detrend(x):
    """
    Remove linear trend from a 1D array.
    """
    n = len(x)
    t = np.arange(n)
    p = np.polyfit(t, x, 1)
    return x - np.polyval(p, t)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute ALFF from fMRI data')
    parser.add_argument('--fmri', required=True, help='Path to fMRI file')
    parser.add_argument('--output', required=True, help='Path to save ALFF map')
    parser.add_argument('--tr', type=float, required=True, help='Repetition time in seconds')
    parser.add_argument('--low', type=float, default=0.01, help='Lower frequency bound in Hz (default: 0.01)')
    parser.add_argument('--high', type=float, default=0.08, help='Upper frequency bound in Hz (default: 0.08)')
    parser.add_argument('--mask', help='Path to mask file (optional)')
    
    args = parser.parse_args()
    
    compute_alff(
        args.fmri,
        args.output,
        args.tr,
        args.low,
        args.high,
        args.mask
    ) 
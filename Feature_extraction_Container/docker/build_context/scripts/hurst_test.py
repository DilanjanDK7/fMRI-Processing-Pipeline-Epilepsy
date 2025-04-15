#!/usr/bin/env python3
import argparse
import nibabel as nib
import numpy as np
import nolds
import os
from scipy import signal

def compute_hurst(ts, fit_method='RANSAC', nvals=None, bandpass=None, tr=None):
    """
    Compute Hurst exponent for a time series.
    
    Parameters:
    -----------
    ts : numpy.ndarray
        Input time series
    fit_method : str, optional
        Method for fitting the power law ('RANSAC' or 'poly'). Default is 'RANSAC'.
    nvals : list, optional
        List of subsequence lengths to use for R/S analysis. If None, uses logmid_n.
    bandpass : tuple, optional
        Bandpass filter frequencies (low, high) in Hz. If None, no filtering is applied.
    tr : float, optional
        Repetition time in seconds, required if bandpass is specified.
        
    Returns:
    --------
    float
        Hurst exponent value
    """
    # Apply bandpass filtering if specified
    if bandpass is not None and tr is not None:
        low_freq, high_freq = bandpass
        fs = 1/tr  # Sampling frequency in Hz
        nyquist = fs/2
        
        # Check if frequencies are valid
        if high_freq > nyquist:
            print(f"Warning: High cutoff frequency {high_freq} exceeds Nyquist frequency {nyquist}. Setting to Nyquist.")
            high_freq = nyquist
            
        # Normalize frequencies to Nyquist
        low = low_freq / nyquist
        high = high_freq / nyquist
        
        # Apply bandpass filter
        b, a = signal.butter(3, [low, high], btype='band')
        ts = signal.filtfilt(b, a, ts)
    
    try:
        return nolds.hurst_rs(ts, nvals=nvals, fit=fit_method, corrected=True, unbiased=True)
    except Exception:
        return 0.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fmri", required=True, help="Path to preprocessed or denoised fMRI file")
    parser.add_argument("--output", required=True, help="Output NIfTI file for Hurst exponent map")
    parser.add_argument("--sample", action="store_true", help="Process only a sample region for testing")
    parser.add_argument("--mask", help="Path to brain mask file (optional)")
    parser.add_argument("--fit", choices=["RANSAC", "poly"], default="RANSAC", 
                        help="Method for fitting the power law ('RANSAC' or 'poly'). Default is 'RANSAC'.")
    parser.add_argument("--subsequence", choices=["logmid", "binary", "logarithmic"], default="logmid",
                        help="Method for selecting subsequence lengths ('logmid', 'binary', or 'logarithmic'). Default is 'logmid'.")
    parser.add_argument("--bandpass", nargs=2, type=float, metavar=('LOW_FREQ', 'HIGH_FREQ'),
                        help="Bandpass filter frequencies in Hz (e.g., 0.01 0.1 for 0.01-0.1 Hz)")
    parser.add_argument("--tr", type=float, help="Repetition time in seconds, required if --bandpass is used")
    args = parser.parse_args()

    # Validate arguments
    if args.bandpass is not None and args.tr is None:
        parser.error("--tr is required when --bandpass is specified")

    print(f"Loading fMRI data from {args.fmri}")
    img = nib.load(args.fmri)
    data = img.get_fdata()
    hurst_map = np.zeros(data.shape[:-1])
    
    # Get dimensions
    nx, ny, nz, nt = data.shape
    print(f"Data dimensions: {nx} x {ny} x {nz} x {nt}")
    
    # Load mask if provided, otherwise create based on variance
    if args.mask:
        print(f"Loading brain mask from {args.mask}")
        mask_img = nib.load(args.mask)
        mask = mask_img.get_fdata() > 0
    else:
        print("Creating mask based on signal variance")
        variance = np.var(data, axis=3)
        mask = variance > np.percentile(variance, 10)
    
    # Setup subsequence selection method
    nvals = None
    if args.subsequence == "binary":
        nvals = nolds.binary_n(nt, min_n=10)
    elif args.subsequence == "logarithmic":
        nvals = nolds.logarithmic_n(10, nt//2, 1.5)
    # For "logmid", we'll use the default (None) which will use nolds.logmid_n
    
    # Process only a sample region if requested
    if args.sample:
        print("Processing sample region only (for testing)")
        # Create a central test region
        x_range = slice(nx//2-5, nx//2+5)
        y_range = slice(ny//2-5, ny//2+5)
        z_range = slice(nz//2-2, nz//2+2)
        
        # Get masked indices only in the sample region
        masked_indices = []
        for x in range(nx//2-5, nx//2+5):
            for y in range(ny//2-5, ny//2+5):
                for z in range(nz//2-2, nz//2+2):
                    if mask[x, y, z]:
                        masked_indices.append((x, y, z))
    else:
        # Get all masked voxels
        masked_indices = np.argwhere(mask)
    
    # Add progress tracking
    total_voxels = len(masked_indices)
    step = max(1, total_voxels // 20)  # Show 20 steps
    
    print("Computing Hurst exponent...")
    print(f"Processing {total_voxels} voxels")
    print(f"Using fitting method: {args.fit}")
    print(f"Using subsequence selection: {args.subsequence}")
    
    if args.bandpass:
        print(f"Applying bandpass filter: {args.bandpass[0]}-{args.bandpass[1]} Hz (TR={args.tr}s)")
        bandpass = (args.bandpass[0], args.bandpass[1])
    else:
        bandpass = None
    
    for i, index in enumerate(masked_indices):
        if isinstance(index, tuple):
            x, y, z = index
        else:
            x, y, z = index[0], index[1], index[2]
        
        if i % step == 0:
            print(f"Progress: {100*i/total_voxels:.1f}% ({i}/{total_voxels} voxels)")
        
        ts = data[x, y, z, :]
        if np.std(ts) > 0:
            hurst_map[x, y, z] = compute_hurst(ts, 
                                              fit_method=args.fit, 
                                              nvals=nvals, 
                                              bandpass=bandpass, 
                                              tr=args.tr)

    print(f"Saving Hurst map to {args.output}")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    out_img = nib.Nifti1Image(hurst_map, affine=img.affine)
    nib.save(out_img, args.output)
    print("Hurst computation completed successfully")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
import argparse
import nibabel as nib
import numpy as np
from scipy import signal
from scipy.signal import windows
import os
import sys

def compute_alff(fmri_file, output_file, tr, bandpass_low, bandpass_high, mask_file=None, 
                detrend_method='linear', window='none', normalize_method='none', 
                compute_falff=False, falff_highband=(0.08, 0.25), sample=False):
    """
    Compute ALFF (Amplitude of Low Frequency Fluctuations) from fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to input fMRI file
    output_file : str
        Path to output ALFF file
    tr : float
        Repetition time in seconds
    bandpass_low : float
        Lower frequency bound for bandpass filter in Hz
    bandpass_high : float
        Upper frequency bound for bandpass filter in Hz
    mask_file : str, optional
        Path to brain mask file
    detrend_method : str, optional
        Method for detrending ('linear', 'constant', 'polynomial', or 'none'). Default is 'linear'.
    window : str, optional
        Window function to apply ('hamming', 'hanning', 'blackman', or 'none'). Default is 'none'.
    normalize_method : str, optional
        Method for normalizing ALFF ('zscore', 'percent', or 'none'). Default is 'none'.
    compute_falff : bool, optional
        Whether to compute fractional ALFF (fALFF). Default is False.
    falff_highband : tuple, optional
        Higher frequency band for fALFF computation (default is (0.08, 0.25) Hz).
    sample : bool, optional
        Whether to process only a sample region for testing. Default is False.
    """
    # Load the fMRI data
    print(f"Loading fMRI data from {fmri_file}")
    img = nib.load(fmri_file)
    data = img.get_fdata()
    affine = img.affine
    header = img.header

    # Load the mask if provided
    mask = None
    if mask_file:
        print(f"Loading mask from {mask_file}")
        mask_img = nib.load(mask_file)
        mask = mask_img.get_fdata().astype(bool)
    else:
        # Create a simple mask based on variance
        print("No mask provided, creating mask based on signal variance")
        variance = np.var(data, axis=3)
        mask = variance > np.percentile(variance, 10)

    # Get dimensions
    nx, ny, nz, nt = data.shape
    print(f"Data dimensions: {nx} x {ny} x {nz} x {nt}")

    # Create empty ALFF map and optional fALFF map
    alff_map = np.zeros((nx, ny, nz))
    falff_map = np.zeros((nx, ny, nz)) if compute_falff else None

    # Calculate sample frequency and design bandpass filter
    fs = 1.0 / tr  # Sample frequency in Hz
    nyquist = fs / 2  # Nyquist frequency
    normalized_low = bandpass_low / nyquist
    normalized_high = bandpass_high / nyquist
    
    # Validate frequency bounds
    if normalized_high > 1.0:
        print(f"Warning: Upper frequency bound {bandpass_high} Hz exceeds Nyquist frequency {nyquist} Hz")
        normalized_high = 1.0
        bandpass_high = nyquist
    
    # Design bandpass filter for ALFF
    b, a = signal.butter(3, [normalized_low, normalized_high], btype='band')
    
    # Handle fALFF computation - fix for potential frequency overlap
    if compute_falff:
        falff_low, falff_high = falff_highband
        
        # Ensure falff_low is greater than bandpass_high to avoid overlap
        if falff_low <= bandpass_high:
            falff_low = bandpass_high + 0.001
            print(f"Warning: Adjusting lower fALFF bound to {falff_low} Hz to avoid overlap with ALFF band")
            
        # Check if adjusted falff_low is still valid
        if falff_low >= nyquist:
            print("Warning: Cannot compute fALFF - frequency range is invalid")
            compute_falff = False
        else:
            # Proceed with the filter design
            norm_falff_low = falff_low / nyquist
            norm_falff_high = min(falff_high / nyquist, 0.99)  # Ensure it's below 1.0
            
            # Validate frequency range
            if norm_falff_low >= norm_falff_high:
                print("Warning: Invalid fALFF frequency range - disabling fALFF computation")
                compute_falff = False
            else:
                b_high, a_high = signal.butter(3, [norm_falff_low, norm_falff_high], btype='band')
                print(f"Computing fALFF with additional high frequency band {falff_low}-{falff_high} Hz")

    print(f"Computing ALFF with bandpass filter {bandpass_low}-{bandpass_high} Hz")
    print(f"Using detrend method: {detrend_method}")
    print(f"Using window function: {window}")
    print(f"Using normalization method: {normalize_method}")

    # Add progress tracking
    masked_indices = np.argwhere(mask)
    total_voxels = len(masked_indices)
    step = max(1, total_voxels // 20)  # Show 20 steps
    
    # Process only a central region if sample mode is on
    if sample:
        print("Processing sample region only (for testing)")
        x_range = slice(nx//2-5, nx//2+5)
        y_range = slice(ny//2-5, ny//2+5)
        z_range = slice(nz//2-2, nz//2+2)
        
        # Filter masked_indices to only include those in the sample region
        sample_indices = []
        for idx in masked_indices:
            if (x_range.start <= idx[0] < x_range.stop and
                y_range.start <= idx[1] < y_range.stop and
                z_range.start <= idx[2] < z_range.stop):
                sample_indices.append(idx)
        masked_indices = np.array(sample_indices)
        total_voxels = len(masked_indices)
        step = max(1, total_voxels // 20) # Recalculate step for sample
        print(f"Processing {total_voxels} voxels in sample region.")
        if total_voxels == 0:
             print("Warning: No voxels found in the sample region within the mask.")
             # Optionally handle this case, e.g., save empty maps or exit
             
    # Loop through masked voxels
    for i, index in enumerate(masked_indices):
        if i % step == 0:
            print(f"Progress: {100*i/total_voxels:.1f}% ({i}/{total_voxels} voxels)")
            
        x, y, z = tuple(index)
        # Get time series for this voxel
        ts = data[x, y, z, :]
        
        # Skip if time series has no variance
        if np.std(ts) <= 1e-6:
            continue
        
        # Apply detrending
        if detrend_method == 'linear':
            ts_detrended = signal.detrend(ts)
        elif detrend_method == 'constant':
            ts_detrended = signal.detrend(ts, type='constant')
        elif detrend_method == 'polynomial':
            # Fit and remove 2nd order polynomial trend
            t = np.arange(len(ts))
            coeffs = np.polyfit(t, ts, 2)
            poly_trend = np.polyval(coeffs, t)
            ts_detrended = ts - poly_trend
        elif detrend_method == 'none':
            ts_detrended = ts
        else:
            raise ValueError(f"Unknown detrend method: {detrend_method}")
        
        # Apply window function if specified
        if window == 'hamming':
            ts_detrended = ts_detrended * windows.hamming(len(ts_detrended))
        elif window == 'hanning':
            ts_detrended = ts_detrended * windows.hann(len(ts_detrended))
        elif window == 'blackman':
            ts_detrended = ts_detrended * windows.blackman(len(ts_detrended))
        # 'none' or any other value means no window is applied
        
        # Apply bandpass filter
        ts_filtered = signal.filtfilt(b, a, ts_detrended)
        
        # Compute FFT and get amplitudes for ALFF band
        fft_vals = np.abs(np.fft.rfft(ts_filtered))
        
        # Compute ALFF as the sum of amplitudes in the frequency band
        alff_map[x, y, z] = np.sum(fft_vals[1:])  # Skip DC component (0 frequency)
        
        # Compute fALFF if requested and valid
        if compute_falff:
            # For fALFF we need to calculate both ALFF and total power across all frequencies
            
            # Option 1: Apply high-frequency bandpass and compute power
            ts_high = signal.filtfilt(b_high, a_high, ts_detrended)
            fft_high = np.abs(np.fft.rfft(ts_high))
            high_power = np.sum(fft_high[1:])
            
            # Option 2: More accurately, compute FFT of the original detrended signal
            # This provides total power across all frequencies
            fft_total = np.abs(np.fft.rfft(ts_detrended))
            total_power = np.sum(fft_total[1:])
            
            # fALFF is ratio of ALFF to the total power
            if total_power > 0:
                falff_map[x, y, z] = alff_map[x, y, z] / total_power

    # Normalize ALFF map based on selected method
    brain_mask = alff_map > 0
    if np.sum(brain_mask) > 0:  # Make sure we have non-zero values
        if normalize_method == 'zscore':
            # Z-score normalization
            alff_mean = np.mean(alff_map[brain_mask])
            alff_std = np.std(alff_map[brain_mask])
            if alff_std > 0:
                alff_map[brain_mask] = (alff_map[brain_mask] - alff_mean) / alff_std
                
                # Also normalize fALFF if computed
                if compute_falff:
                    falff_mean = np.mean(falff_map[brain_mask])
                    falff_std = np.std(falff_map[brain_mask])
                    if falff_std > 0:
                        falff_map[brain_mask] = (falff_map[brain_mask] - falff_mean) / falff_std
                        
        elif normalize_method == 'percent':
            # Percent change relative to mean
            alff_mean = np.mean(alff_map[brain_mask])
            if alff_mean > 0:
                alff_map[brain_mask] = (alff_map[brain_mask] / alff_mean) * 100
                
                # Also normalize fALFF if computed
                if compute_falff:
                    falff_mean = np.mean(falff_map[brain_mask])
                    if falff_mean > 0:
                        falff_map[brain_mask] = (falff_map[brain_mask] / falff_mean) * 100

    # Save the ALFF map
    print(f"Saving ALFF map to {output_file}")
    alff_img = nib.Nifti1Image(alff_map, affine, header)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    nib.save(alff_img, output_file)
    print("ALFF computation completed successfully")
    
    # Save fALFF map if computed
    if compute_falff:
        # Construct the expected fALFF output path based on the ALFF path
        alff_dir = os.path.dirname(output_file)
        alff_basename = os.path.basename(output_file)
        subject_id = alff_basename.split('_alff.nii.gz')[0]
        falff_expected_name = f"{subject_id}_falff.nii.gz"
        falff_output = os.path.join(alff_dir, falff_expected_name)
        
        # falff_output = output_file.replace('.nii.gz', '_falff.nii.gz') # Original incorrect naming
        print(f"Saving fALFF map to {falff_output}")
        falff_img = nib.Nifti1Image(falff_map, affine, header)
        nib.save(falff_img, falff_output)
        print("fALFF computation completed successfully")
        
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compute ALFF from fMRI data')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output', required=True, help='Output ALFF file')
    parser.add_argument('--mask', help='Brain mask file (optional)')
    parser.add_argument('--tr', type=float, required=True, help='Repetition time in seconds')
    parser.add_argument('--bandpass_low', type=float, required=True, help='Lower frequency bound for bandpass filter in Hz')
    parser.add_argument('--bandpass_high', type=float, required=True, help='Upper frequency bound for bandpass filter in Hz')
    parser.add_argument('--sample', action='store_true', help='Process only a sample region for testing')
    
    # Additional options
    parser.add_argument('--detrend', choices=['linear', 'constant', 'polynomial', 'none'], default='linear',
                      help='Detrending method (default: linear)')
    parser.add_argument('--window', choices=['hamming', 'hanning', 'blackman', 'none'], default='none',
                      help='Window function to apply to time series (default: none)')
    parser.add_argument('--normalize', choices=['zscore', 'percent', 'none'], default='none',
                      help='Normalization method for output maps (default: none)')
    parser.add_argument('--falff', action='store_true', 
                      help='Also compute fractional ALFF (fALFF)')
    parser.add_argument('--falff_highband', nargs=2, type=float, default=[0.08, 0.25], metavar=('LOW', 'HIGH'),
                      help='Higher frequency band for fALFF computation in Hz (default: 0.08 0.25)')
    
    args = parser.parse_args()
    print(f"Arguments parsed: {args}")
    
    compute_alff(
        args.fmri, 
        args.output, 
        args.tr, 
        args.bandpass_low, 
        args.bandpass_high, 
        args.mask,
        detrend_method=args.detrend,
        window=args.window,
        normalize_method=args.normalize,
        compute_falff=args.falff,
        falff_highband=tuple(args.falff_highband),
        sample=args.sample
    ) 
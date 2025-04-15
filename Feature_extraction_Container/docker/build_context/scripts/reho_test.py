#!/usr/bin/env python3
"""
Script to compute Regional Homogeneity (ReHo) from fMRI data using AFNI's 3dReHo.
"""

import os
import sys
import subprocess
import argparse
import nibabel as nib
import numpy as np
from pathlib import Path

def compute_reho(fmri_file, output_file, mask_file=None, neighborhood_size=27):
    """
    Compute Regional Homogeneity (ReHo) from fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    output_file : str
        Path to save the ReHo output
    mask_file : str, optional
        Path to a brain mask. If not provided, a mask will be created based on signal variance.
    neighborhood_size : int, optional
        Size of the neighborhood for ReHo calculation (27, 19, or 7). Default is 27.
    """
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Check if AFNI is installed and 3dReHo is available
    try:
        subprocess.run(['which', '3dReHo'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: AFNI's 3dReHo command not found. Please ensure AFNI is installed.")
        sys.exit(1)
    
    # Create a temporary mask if not provided
    temp_mask = None
    if not mask_file:
        print("No mask provided, creating a mask based on signal variance")
        # Create a directory for the mask if it doesn't exist
        mask_dir = os.path.dirname(output_file)
        if not os.path.exists(mask_dir):
            os.makedirs(mask_dir)
            
        temp_mask = os.path.join(mask_dir, "temp_mask.nii.gz")
        create_mask_from_variance(fmri_file, temp_mask)
        mask_file = temp_mask
        print(f"Created temporary mask file: {mask_file}")
    
    # Compute ReHo
    print("Computing Regional Homogeneity (ReHo)")
    print(f"Input fMRI: {fmri_file}")
    print(f"Brain mask: {mask_file}")
    print(f"Output: {output_file}")
    print(f"Neighborhood size: {neighborhood_size}")
    
    # Ensure neighborhood size is valid
    if neighborhood_size not in [7, 19, 27]:
        print(f"Warning: Invalid neighborhood size {neighborhood_size}. Using default (27).")
        neighborhood_size = 27
    
    # Construct and run the 3dReHo command
    cmd = [
        '3dReHo',
        '-prefix', output_file,
        '-inset', fmri_file,
        '-mask', mask_file,
        '-nneigh', str(neighborhood_size)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"ReHo computation complete. Output saved to: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error computing ReHo: {e}")
        print(f"Command stdout: {e.stdout.decode() if e.stdout else ''}")
        print(f"Command stderr: {e.stderr.decode() if e.stderr else ''}")
        if temp_mask and os.path.exists(temp_mask):
            os.remove(temp_mask)
        sys.exit(1)
    
    # Clean up temporary files
    if temp_mask and os.path.exists(temp_mask):
        os.remove(temp_mask)
        print(f"Removed temporary mask file: {temp_mask}")

def create_mask_from_variance(fmri_file, mask_file, threshold=0.05):
    """
    Create a brain mask based on signal variance.
    Voxels with variance above the threshold are considered brain voxels.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    mask_file : str
        Path to save the mask
    threshold : float, optional
        Variance threshold. Default is 0.05.
    """
    try:
        # Load the fMRI data
        img = nib.load(fmri_file)
        data = img.get_fdata()
        
        # Calculate variance over time
        variance = np.var(data, axis=3)
        
        # Create mask by thresholding variance
        # We normalize the variance first to make the threshold more robust
        normalized_variance = variance / np.max(variance)
        mask = (normalized_variance > threshold).astype(np.int16)
        
        # Save the mask
        mask_img = nib.Nifti1Image(mask, img.affine, img.header)
        nib.save(mask_img, mask_file)
        
    except Exception as e:
        print(f"Error creating mask from variance: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Compute Regional Homogeneity (ReHo) from fMRI data')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output', required=True, help='Output ReHo file')
    parser.add_argument('--mask', help='Brain mask (optional, will be created if not provided)')
    parser.add_argument('--neighborhood', type=int, default=27, choices=[7, 19, 27],
                        help='Neighborhood size (7, 19, or 27). Default is 27.')
    
    args = parser.parse_args()
    
    compute_reho(args.fmri, args.output, args.mask, args.neighborhood)

if __name__ == "__main__":
    main() 
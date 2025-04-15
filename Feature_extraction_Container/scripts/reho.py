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
import time
from pathlib import Path

def compute_reho(fmri_file, output_file, cluster_size=27, mask_file=None):
    """
    Compute Regional Homogeneity (ReHo) from fMRI data using AFNI's 3dReHo.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    output_file : str
        Path to save the ReHo output
    cluster_size : int, optional
        Size of the neighborhood for ReHo calculation (27, 19, or 7). Default is 27.
    mask_file : str, optional
        Path to a brain mask. If not provided, a mask will be created based on signal variance.
    """
    start_time = time.time()
    
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
    print(f"Neighborhood size: {cluster_size}")
    
    # Ensure neighborhood size is valid
    if cluster_size not in [7, 19, 27]:
        print(f"Warning: Invalid neighborhood size {cluster_size}. Using default (27).")
        cluster_size = 27
    
    # Construct and run the 3dReHo command
    cmd = [
        '3dReHo',
        '-prefix', output_file,
        '-inset', fmri_file,
        '-mask', mask_file,
        '-nneigh', str(cluster_size)
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
    
    elapsed_time = time.time() - start_time
    print(f"ReHo calculation completed in {elapsed_time:.2f} seconds")
    
    return output_file


def create_mask_from_variance(fmri_file, mask_file):
    """
    Create a brain mask based on variance in fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    mask_file : str
        Path to save the output mask
    """
    print(f"Creating mask from fMRI data variance: {fmri_file}")
    
    # Load the fMRI data
    img = nib.load(fmri_file)
    data = img.get_fdata()
    
    # Calculate variance along time axis
    variance = np.var(data, axis=3)
    
    # Create mask based on variance threshold (10th percentile)
    threshold = np.percentile(variance[variance > 0], 10)
    mask = variance > threshold
    
    # Save the mask
    mask_img = nib.Nifti1Image(mask.astype(np.int8), img.affine, img.header)
    nib.save(mask_img, mask_file)
    
    print(f"Created mask with {np.sum(mask)} voxels")
    return mask_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute Regional Homogeneity (ReHo) from fMRI data')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output', required=True, help='Output ReHo file')
    parser.add_argument('--cluster-size', type=int, default=27, choices=[7, 19, 27],
                        help='Cluster size (7, 19, or 27). Default is 27.')
    parser.add_argument('--mask', help='Brain mask (optional, will be created if not provided)')
    
    args = parser.parse_args()
    
    compute_reho(args.fmri, args.output, args.cluster_size, args.mask) 
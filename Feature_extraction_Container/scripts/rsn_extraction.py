#!/usr/bin/env python3
"""
Script to extract resting state network (RSN) activity from fMRI data.
Uses Yeo et al. 7-network and 17-network masks for network parcellation.
"""

import os
import sys
import logging
import argparse
import numpy as np
import nibabel as nib
import pandas as pd
from pathlib import Path
from nilearn import input_data
from nilearn import image
from nilearn.maskers import NiftiLabelsMasker, NiftiMapsMasker
import h5py

# Import RSN mask download function
from download_rsn_masks import download_rsn_masks

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_rsn_activity(fmri_file, output_dir, mask_file=None, subject_id=None, sample=False, sample_tp=100):
    """
    Extract resting state network (RSN) activity from fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    output_dir : str
        Path to save the RSN activity results
    mask_file : str, optional
        Path to a brain mask. If not provided, all non-zero voxels are used.
    subject_id : str, optional
        Subject ID for the analysis. If None, extracted from fmri_file.
    sample : bool, optional
        If True, only a sample of time points will be used for testing purposes.
    sample_tp : int, optional
        Number of time points to use when sample is True.
    """
    logger.info(f"Starting RSN activity extraction for: {fmri_file}")
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Extract subject ID if not provided
    if subject_id is None:
        subject_id = os.path.basename(fmri_file).split('_')[0]
        logger.info(f"Extracted subject ID: {subject_id}")
    
    # Get RSN masks
    rsn_masks_dir = "/app/rsn_masks"
    yeo_7_path, yeo_17_path = download_rsn_masks(rsn_masks_dir)
    
    # Load fMRI data
    logger.info(f"Loading fMRI data from {fmri_file}")
    fmri_img = nib.load(fmri_file)
    
    # Apply sample if requested
    if sample:
        logger.warning(f"Applying temporal sampling for testing: using first {sample_tp} time points.")
        # Extract data and limit time points
        fmri_data = fmri_img.get_fdata()
        original_shape = fmri_data.shape
        
        if original_shape[3] > sample_tp:
            fmri_data = fmri_data[..., :sample_tp]
            # Create new NIfTI with sampled data, preserving header info
            fmri_img = nib.Nifti1Image(fmri_data, fmri_img.affine, fmri_img.header)
            logger.info(f"Sampled fMRI data to shape: {fmri_data.shape}")
    
    # Load mask if provided
    mask_img = None
    if mask_file:
        logger.info(f"Loading mask from {mask_file}")
        mask_img = nib.load(mask_file)
    
    # Define output paths
    yeo_7_output_csv = os.path.join(output_dir, f"{subject_id}_rsn_7networks.csv")
    yeo_17_output_csv = os.path.join(output_dir, f"{subject_id}_rsn_17networks.csv")
    output_h5 = os.path.join(output_dir, f"{subject_id}_rsn_activity.h5")
    
    logger.info("Processing 7-network parcellation...")
    # Extract time series for each of the 7 networks
    yeo_7_masker = NiftiLabelsMasker(
        labels_img=yeo_7_path,
        mask_img=mask_img,
        standardize=True,
        memory='nilearn_cache',
        verbose=1
    )
    
    # Extract time series
    yeo_7_time_series = yeo_7_masker.fit_transform(fmri_img)
    
    # Create DataFrame with network labels
    network_7_labels = [
        'Visual', 'Somatomotor', 'Dorsal Attention',
        'Ventral Attention', 'Limbic', 'Frontoparietal', 'Default'
    ]
    yeo_7_df = pd.DataFrame(yeo_7_time_series, columns=network_7_labels)
    
    # Save to CSV
    logger.info(f"Saving 7-network time series to {yeo_7_output_csv}")
    yeo_7_df.to_csv(yeo_7_output_csv, index=False)
    
    logger.info("Processing 17-network parcellation...")
    # Extract time series for each of the 17 networks
    yeo_17_masker = NiftiLabelsMasker(
        labels_img=yeo_17_path,
        mask_img=mask_img,
        standardize=True,
        memory='nilearn_cache',
        verbose=1
    )
    
    # Extract time series
    yeo_17_time_series = yeo_17_masker.fit_transform(fmri_img)
    
    # Create DataFrame with network labels
    network_17_labels = [f'Network {i+1}' for i in range(17)]
    yeo_17_df = pd.DataFrame(yeo_17_time_series, columns=network_17_labels)
    
    # Save to CSV
    logger.info(f"Saving 17-network time series to {yeo_17_output_csv}")
    yeo_17_df.to_csv(yeo_17_output_csv, index=False)
    
    # Save both sets of time series to a single HDF5 file
    logger.info(f"Saving all time series to HDF5: {output_h5}")
    with h5py.File(output_h5, 'w') as f:
        # Create groups
        networks_7 = f.create_group('networks_7')
        networks_17 = f.create_group('networks_17')
        
        # Save 7-network time series
        for i, label in enumerate(network_7_labels):
            networks_7.create_dataset(label, data=yeo_7_time_series[:, i])
        
        # Save 17-network time series
        for i, label in enumerate(network_17_labels):
            networks_17.create_dataset(label, data=yeo_17_time_series[:, i])
        
        # Add metadata
        f.attrs['subject_id'] = subject_id
        f.attrs['fmri_file'] = os.path.basename(fmri_file)
        f.attrs['mask_file'] = os.path.basename(mask_file) if mask_file else 'None'
        f.attrs['sample_applied'] = sample
        if sample:
            f.attrs['sample_timepoints'] = sample_tp
    
    logger.info("RSN activity extraction completed successfully.")
    
    return yeo_7_output_csv, yeo_17_output_csv, output_h5

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract resting state network (RSN) activity from fMRI data.')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output-dir', required=True, help='Output directory for RSN activity results')
    parser.add_argument('--mask', help='Brain mask (optional)')
    parser.add_argument('--subject-id', help='Subject ID (optional, extracted from filename if not provided)')
    parser.add_argument('--sample', action='store_true', help='Use only a sample of time points for testing')
    parser.add_argument('--sample-tp', type=int, default=100, help='Number of time points to use when sampling')
    
    args = parser.parse_args()
    
    extract_rsn_activity(
        args.fmri,
        args.output_dir,
        args.mask,
        args.subject_id,
        args.sample,
        args.sample_tp
    )

if __name__ == '__main__':
    main() 
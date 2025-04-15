#!/usr/bin/env python3
"""
Script to download resting state network (RSN) masks.
Downloads Yeo et al. 7-network and 17-network masks for RSN analysis.
"""

import os
import logging
import nibabel as nib
import numpy as np
from nilearn.datasets import fetch_atlas_yeo_2011
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_rsn_masks(output_dir="/app/rsn_masks"):
    """
    Download the Yeo et al. 7-network and 17-network masks.
    
    Parameters:
    -----------
    output_dir : str
        Directory where to save the masks
    
    Returns:
    --------
    tuple
        Paths to the 7-network and 17-network masks
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Download the Yeo 2011 atlas with both 7 and 17 networks
    logger.info(f"Downloading Yeo et al. RSN masks to {output_dir}")
    yeo_7_path = os.path.join(output_dir, "yeo_7_networks.nii.gz")
    yeo_17_path = os.path.join(output_dir, "yeo_17_networks.nii.gz")
    
    # Check if masks have already been downloaded
    if os.path.exists(yeo_7_path) and os.path.exists(yeo_17_path):
        logger.info("RSN masks already downloaded.")
        return yeo_7_path, yeo_17_path
    
    try:
        # Fetch the atlases
        logger.info("Fetching Yeo 2011 atlases...")
        yeo_atlas = fetch_atlas_yeo_2011()
        
        # Save 7-network mask (MNI152 space)
        logger.info(f"Saving 7-network mask to {yeo_7_path}")
        # Copy the atlas to preserve the original
        mask_7 = nib.load(yeo_atlas['thin_7'])
        nib.save(mask_7, yeo_7_path)
        
        # Save 17-network mask (MNI152 space)
        logger.info(f"Saving 17-network mask to {yeo_17_path}")
        mask_17 = nib.load(yeo_atlas['thin_17'])
        nib.save(mask_17, yeo_17_path)
        
        logger.info("RSN masks downloaded successfully.")
        return yeo_7_path, yeo_17_path
    
    except Exception as e:
        logger.error(f"Error downloading RSN masks: {e}")
        raise

if __name__ == "__main__":
    download_rsn_masks() 
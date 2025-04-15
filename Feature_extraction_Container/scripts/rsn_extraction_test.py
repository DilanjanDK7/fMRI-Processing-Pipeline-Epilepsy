#!/usr/bin/env python3
"""
Test script for RSN extraction, with sampling functionality for testing.
"""

import os
import sys
import logging
import argparse
import numpy as np
import nibabel as nib
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the scripts directory to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from rsn_extraction import extract_rsn_activity
from download_rsn_masks import download_rsn_masks

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Extract resting state network (RSN) activity from fMRI data.')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output_dir', required=True, help='Output directory for RSN activity results')
    parser.add_argument('--mask', help='Brain mask (optional)')
    parser.add_argument('--subject_id', help='Subject ID (optional, extracted from filename if not provided)')
    parser.add_argument('--sample', action='store_true', help='Use only a sample of time points for testing')
    parser.add_argument('--sample_tp', type=int, default=100, help='Number of time points to use when sampling')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Extract subject ID if not provided
    subject_id = args.subject_id
    if subject_id is None:
        subject_id = os.path.basename(args.fmri).split('_')[0]
        logging.info(f"Extracted subject ID: {subject_id}")
    
    # Download RSN masks if needed
    logging.info("Downloading RSN masks if needed...")
    rsn_masks_dir = "/app/rsn_masks"
    try:
        yeo_7_path, yeo_17_path = download_rsn_masks(rsn_masks_dir)
        logging.info(f"Using RSN masks: {yeo_7_path} and {yeo_17_path}")
    except Exception as e:
        logging.error(f"Failed to download RSN masks: {e}")
        sys.exit(1)
    
    # Extract RSN activity
    try:
        logging.info(f"Extracting RSN activity from {args.fmri}")
        yeo_7_csv, yeo_17_csv, h5_file = extract_rsn_activity(
            args.fmri,
            args.output_dir,
            args.mask,
            subject_id,
            args.sample,
            args.sample_tp
        )
        logging.info(f"RSN extraction completed. Results saved to:")
        logging.info(f"  - 7-Network CSV: {yeo_7_csv}")
        logging.info(f"  - 17-Network CSV: {yeo_17_csv}")
        logging.info(f"  - HDF5 file: {h5_file}")
    except Exception as e:
        logging.error(f"RSN extraction failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 
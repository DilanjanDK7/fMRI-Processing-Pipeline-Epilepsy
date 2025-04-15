#!/usr/bin/env python3
"""
Script to organize BIDS data and find appropriate fMRI and mask inputs for feature extraction.
"""

import os
import argparse
import sys
import logging
from pathlib import Path
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from bids import BIDSLayout
except ImportError:
    logging.error("Failed to import pybids. Please install with 'pip install pybids'.")
    sys.exit(1)


def find_inputs(bids_dir, derivatives_dir=None, subject=None, session=None, 
                task=None, space="MNI152NLin2009cAsym", desc="preproc"):
    """
    Find fMRI and mask files in a BIDS dataset.
    
    Parameters:
    -----------
    bids_dir : str
        Path to the BIDS dataset root directory.
    derivatives_dir : str, optional
        Path to the derivatives directory. If None, will look in bids_dir/derivatives.
    subject : str, optional
        Subject ID to filter by (e.g., '001'). If None, all subjects will be included.
    session : str, optional
        Session ID to filter by (e.g., '01'). If None, all sessions will be included.
    task : str, optional
        Task name to filter by (e.g., 'rest'). If None, all tasks will be included.
    space : str, optional
        Image space to filter by. Default is 'MNI152NLin2009cAsym'.
    desc : str, optional
        Image description to filter by for fMRI data. Default is 'preproc'.
        
    Returns:
    --------
    dict
        Dictionary mapping subject IDs to dictionaries containing fMRI and mask file paths.
    """
    bids_dir = Path(bids_dir)
    
    # Set up derivatives directory
    if derivatives_dir is None:
        derivatives_dir = bids_dir / "derivatives"
    else:
        derivatives_dir = Path(derivatives_dir)
    
    logging.info(f"Looking for inputs in BIDS directory: {bids_dir}")
    logging.info(f"Derivatives directory: {derivatives_dir}")
    
    # Try different derivatives directories commonly used
    derivatives_options = [
        derivatives_dir,
        derivatives_dir / "fmriprep",
        derivatives_dir / "preprocessing"
    ]
    
    layout = None
    for deriv_dir in derivatives_options:
        if deriv_dir.exists():
            try:
                logging.info(f"Attempting to load BIDS layout from: {deriv_dir}")
                layout = BIDSLayout(deriv_dir, derivatives=True)
                logging.info(f"Successfully loaded BIDS layout from: {deriv_dir}")
                break
            except Exception as e:
                logging.warning(f"Failed to load BIDS layout from {deriv_dir}: {e}")
    
    if layout is None:
        logging.error(f"Could not find a valid derivatives directory with BIDS structure.")
        sys.exit(1)
    
    # Set up filters
    filters = {"space": space}
    if subject:
        filters["subject"] = subject
    if session:
        filters["session"] = session
    if task:
        filters["task"] = task
    
    logging.info(f"Using filters: {filters}")
    
    # Find all subjects if not specified
    if not subject:
        subjects = layout.get_subjects()
    else:
        subjects = [subject]
    
    # Find all sessions if not specified
    if not session:
        sessions = layout.get_sessions() or [None]
    else:
        sessions = [session]
    
    # Find all tasks if not specified
    if not task:
        tasks = layout.get_tasks() or ["rest"]
    else:
        tasks = [task]
    
    # Store results
    results = {}
    
    for subj in subjects:
        logging.info(f"Processing subject: {subj}")
        for ses in sessions:
            for tsk in tasks:
                # Set up subject-specific filters
                subj_filters = filters.copy()
                subj_filters["subject"] = subj
                if ses:
                    subj_filters["session"] = ses
                subj_filters["task"] = tsk
                
                # Find preprocessed fMRI files
                fmri_filters = subj_filters.copy()
                fmri_filters["desc"] = desc
                fmri_filters["suffix"] = "bold"
                
                fmri_files = layout.get(return_type="file", **fmri_filters)
                
                # Find corresponding mask files
                mask_filters = subj_filters.copy()
                mask_filters["desc"] = "brain"
                mask_filters["suffix"] = "mask"
                
                mask_files = layout.get(return_type="file", **mask_filters)
                
                if fmri_files and mask_files:
                    # Use first file if multiple matches
                    fmri_file = fmri_files[0]
                    mask_file = mask_files[0]
                    
                    # Create subject key (including session if present)
                    subj_key = f"sub-{subj}"
                    if ses:
                        subj_key += f"_ses-{ses}"
                    
                    # Add to results
                    results[subj_key] = {
                        "fmri": str(fmri_file),
                        "mask": str(mask_file),
                        "task": tsk
                    }
                    
                    logging.info(f"Found fMRI file: {fmri_file}")
                    logging.info(f"Found mask file: {mask_file}")
                else:
                    logging.warning(f"Could not find matching fMRI and mask files for subject {subj}, task {tsk}")
    
    if not results:
        logging.error("No matching fMRI and mask files found with the specified filters.")
        return None
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Find fMRI and mask inputs from a BIDS dataset")
    parser.add_argument("--bids-dir", required=True, help="Path to the BIDS dataset root directory")
    parser.add_argument("--derivatives-dir", help="Path to the derivatives directory (default: bids-dir/derivatives)")
    parser.add_argument("--subject", help="Subject ID to filter by (e.g., '001')")
    parser.add_argument("--session", help="Session ID to filter by (e.g., '01')")
    parser.add_argument("--task", default="rest", help="Task name to filter by (default: 'rest')")
    parser.add_argument("--space", default="MNI152NLin2009cAsym", help="Image space to filter by (default: 'MNI152NLin2009cAsym')")
    parser.add_argument("--desc", default="preproc", help="Image description for fMRI data (default: 'preproc')")
    parser.add_argument("--output", default="inputs.json", help="Output JSON file to save inputs (default: 'inputs.json')")
    
    args = parser.parse_args()
    
    inputs = find_inputs(
        args.bids_dir,
        args.derivatives_dir,
        args.subject,
        args.session,
        args.task,
        args.space,
        args.desc
    )
    
    if inputs:
        logging.info(f"Found {len(inputs)} subjects with matching fMRI and mask files.")
        
        # Save inputs to JSON file
        with open(args.output, "w") as f:
            json.dump(inputs, f, indent=2)
        
        logging.info(f"Saved inputs to {args.output}")
        
        # Print example command
        subject_key = next(iter(inputs))
        subject_inputs = inputs[subject_key]
        print("\nExample command to run feature extraction:")
        print(f"python scripts/run_features.py --input \"{subject_inputs['fmri']}\" --mask \"{subject_inputs['mask']}\" --output-dir \"outputs/{subject_key}\"")
    

if __name__ == "__main__":
    main() 
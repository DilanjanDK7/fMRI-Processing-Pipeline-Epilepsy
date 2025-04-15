#!/usr/bin/env python3
"""
Script to compute Quantum Mechanics-inspired FFT (QM-FFT) features from fMRI data.
"""

import os
import argparse
import time
import logging
import sys
import h5py
import glob
import numpy as np
import nibabel as nib
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    # Try to import the QM_FFT_Analysis package
    from QM_FFT_Analysis.utils.map_builder import MapBuilder
except ImportError as e:
    logging.error(f"Failed to import QM_FFT_Analysis: {e}")
    logging.error("Ensure the package is installed and accessible (check PYTHONPATH).")
    sys.exit(1)


def consolidate_mapbuilder_to_hdf5(mapbuilder_subject_dir, output_h5_path):
    """
    Finds all .npy files in the MapBuilder output directory (data, analysis subdirs)
    and saves them into a single HDF5 file, preserving relative structure.
    """
    logging.info(f"Consolidating results from {mapbuilder_subject_dir} into {output_h5_path}")
    os.makedirs(os.path.dirname(output_h5_path), exist_ok=True)
    
    with h5py.File(output_h5_path, 'w') as hf:
        search_dirs = [mapbuilder_subject_dir / 'data', mapbuilder_subject_dir / 'analysis']
        npy_files = []
        for d in search_dirs:
            if d.exists():
                # Recursively find all .npy files
                npy_files.extend(glob.glob(str(d / '**/*.npy'), recursive=True)) 
        
        if not npy_files:
            logging.warning(f"No .npy files found in {mapbuilder_subject_dir} subdirectories.")
            return
            
        for npy_file in npy_files:
            try:
                data = np.load(npy_file)
                relative_path = os.path.relpath(npy_file, mapbuilder_subject_dir)
                dataset_path = Path(relative_path).with_suffix('').as_posix() 
                
                logging.debug(f"Saving {npy_file} to HDF5 dataset: {dataset_path}")
                hf.create_dataset(dataset_path, data=data)
            except Exception as e:
                logging.error(f"Failed to load or save {npy_file} to HDF5: {e}")

    logging.info("HDF5 consolidation complete.")


def compute_qm_fft(fmri_file, output_file, mask_file=None, subject_id=None, 
                  eps=1e-6, radius=0.6, local_k=5):
    """
    Compute QM-FFT (Quantum Mechanics-inspired Fast Fourier Transform) features from fMRI data.
    
    Parameters:
    -----------
    fmri_file : str
        Path to the input fMRI data
    output_file : str
        Path to save the QM-FFT features (HDF5 format)
    mask_file : str, optional
        Path to a brain mask. If not provided, a mask will be created based on signal variance.
    subject_id : str, optional
        Subject ID for the analysis. If None, extracted from fmri_file.
    eps : float, optional
        FINUFFT precision. Default is 1e-6.
    radius : float, optional
        K-space mask radius. Default is 0.6.
    local_k : int, optional
        Number of neighbors for local variance. Default is 5.
    """
    print("Starting QM-FFT calculation...")
    start_time = time.time()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Extract subject ID if not provided
    if subject_id is None:
        subject_id = os.path.basename(fmri_file).split('_')[0]
        print(f"Extracted subject ID: {subject_id}")
    
    # Create temporary directory for MapBuilder intermediate files
    temp_mapbuilder_base = Path(os.path.dirname(output_file)) / f"{os.path.splitext(os.path.basename(output_file))[0]}_temp_mapbuilder_work"
    temp_mapbuilder_base.mkdir(parents=True, exist_ok=True)
    
    print(f"Using temporary directory: {temp_mapbuilder_base}")
    
    try:
        # Load fMRI data and mask
        print(f"Loading fMRI data from {fmri_file}...")
        fmri_img = nib.load(fmri_file)
        fmri_data = fmri_img.get_fdata(dtype=np.float32)
        affine = fmri_img.affine
        
        # Load or create mask
        if mask_file:
            print(f"Loading mask from {mask_file}...")
            mask_img = nib.load(mask_file)
            mask_data = mask_img.get_fdata().astype(bool)
        else:
            print("Creating mask from fMRI data...")
            # Simple mask: voxels with non-zero variance
            mask_data = np.std(fmri_data, axis=3) > 0
        
        # Ensure mask dimensions match
        if fmri_data.shape[:3] != mask_data.shape:
            raise ValueError("Mask dimensions do not match fMRI data dimensions")
        
        # Extract voxel coordinates and time series
        print("Extracting voxel coordinates and time series...")
        mask_indices = np.array(np.where(mask_data)).T
        voxel_coords_ijk1 = np.hstack((mask_indices, np.ones((mask_indices.shape[0], 1))))
        voxel_coords_xyz = nib.affines.apply_affine(affine, voxel_coords_ijk1[:, :3])
        
        # Extract time series for each voxel in the mask
        voxel_time_series = fmri_data[mask_indices[:, 0], mask_indices[:, 1], mask_indices[:, 2], :]
        n_voxels, n_timepoints = voxel_time_series.shape
        print(f"Extracted {n_voxels} voxels, {n_timepoints} time points.")
        
        # Transpose to get time as first dimension (required by MapBuilder)
        strengths_real = np.ascontiguousarray(voxel_time_series.T)
        
        # Create complex array (real values with zero imaginary part)
        strengths_imag = np.zeros_like(strengths_real)
        strengths_complex = np.ascontiguousarray(strengths_real + 1j * strengths_imag)
        
        # Get spatial coordinates for each voxel
        x_coords = np.ascontiguousarray(voxel_coords_xyz[:, 0])
        y_coords = np.ascontiguousarray(voxel_coords_xyz[:, 1])
        z_coords = np.ascontiguousarray(voxel_coords_xyz[:, 2])
        
        # Run MapBuilder
        print("Initializing MapBuilder...")
        map_builder = MapBuilder(
            subject_id=subject_id,
            output_dir=temp_mapbuilder_base,
            x=x_coords,
            y=y_coords,
            z=z_coords,
            strengths=strengths_complex,
            eps=eps,
            dtype='complex128'
        )
        
        mapbuilder_subject_dir = temp_mapbuilder_base / subject_id
        print(f"Using MapBuilder output directory: {mapbuilder_subject_dir}")
        
        print("Running MapBuilder processing...")
        analyses_to_run = [
            'magnitude'
            # , 
            # 'phase',
            # 'temporal_diff_magnitude',
            #   'temporal_diff_phase'
        ]
        
        print(f"Running MapBuilder with analyses: {analyses_to_run}")
        map_builder.process_map(
            n_centers=1,
            radius=radius,
            analyses_to_run=analyses_to_run,
            k_neighbors_local_var=local_k
        )
        print(f"MapBuilder processing complete. Consolidating results...")
        
        # Consolidate results to HDF5
        if mapbuilder_subject_dir.exists():
            consolidate_mapbuilder_to_hdf5(mapbuilder_subject_dir, output_file)
        else:
            raise Exception(f"MapBuilder output directory not found after processing: {mapbuilder_subject_dir}")
        
        # Optional: Clean up temporary directory
        # import shutil
        # print(f"Cleaning up temporary directory: {temp_mapbuilder_base}")
        # shutil.rmtree(temp_mapbuilder_base)
        
    except Exception as e:
        print(f"Error during QM-FFT analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    elapsed_time = time.time() - start_time
    print(f"QM-FFT calculation completed in {elapsed_time:.2f} seconds")
    
    return output_file


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compute QM-FFT (Quantum Mechanics-inspired FFT) features from fMRI data')
    parser.add_argument('--fmri', required=True, help='Input fMRI file')
    parser.add_argument('--output', required=True, help='Output HDF5 file for QM-FFT features')
    parser.add_argument('--mask', help='Brain mask (optional, will be created if not provided)')
    parser.add_argument('--subject-id', help='Subject ID (optional, extracted from filename if not provided)')
    parser.add_argument('--eps', type=float, default=1e-6, help='FINUFFT precision (default: 1e-6)')
    parser.add_argument('--radius', type=float, default=0.6, help='K-space mask radius (default: 0.6)')
    parser.add_argument('--local-k', type=int, default=5, help='Number of neighbors for local variance (default: 5)')
    
    args = parser.parse_args()
    
    compute_qm_fft(
        args.fmri,
        args.output,
        args.mask,
        args.subject_id,
        args.eps,
        args.radius,
        args.local_k
    ) 
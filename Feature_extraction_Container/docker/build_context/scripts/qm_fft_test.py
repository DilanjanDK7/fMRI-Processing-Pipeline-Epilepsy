import numpy as np
import nibabel as nib
from pathlib import Path
import logging
import sys
import h5py 
import glob 
import os 
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Define paths and parameters ---
# Use argparse for flexibility, but provide defaults for direct running
parser = argparse.ArgumentParser(description="Run standalone QM FFT Analysis test.")
parser.add_argument('--fmri', type=str, 
                    default="/media/brainlab-uwo/Data1/Results/pipeline_test_3/sub-17017/func/sub-17017_task-rest_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz",
                    help="Path to the input preprocessed fMRI NIfTI file.")
parser.add_argument('--mask', type=str, 
                    default="/media/brainlab-uwo/Data1/Results/pipeline_test_3/sub-17017/func/sub-17017_task-rest_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz",
                    help="Path to the input brain mask NIfTI file.")
parser.add_argument('--output_h5', type=str, 
                    default="./feature_extraction/qm_fft_test_result.h5",
                    help="Path for the output HDF5 features file.")
parser.add_argument('--subject_id', type=str, default="sub-17017_test",
                    help="Subject ID for the analysis.")
parser.add_argument('--eps', type=float, default=1e-6,
                    help="FINUFFT precision.")
parser.add_argument('--radius', type=float, default=0.6,
                    help="K-space mask radius.")
parser.add_argument('--local_k', type=int, default=5,
                    help="Number of neighbors for local variance.")

args = parser.parse_args()

input_fmri_path = Path(args.fmri)
input_mask_path = Path(args.mask)
output_hdf5_path = Path(args.output_h5)
subject_id = args.subject_id
finufft_precision = args.eps
kspace_masks_radius = args.radius
local_var_k = args.local_k

# Ensure output directory exists
output_hdf5_path.parent.mkdir(parents=True, exist_ok=True)
# Temporary directory for MapBuilder intermediate files
temp_mapbuilder_base = output_hdf5_path.parent / f"{output_hdf5_path.stem}_temp_mapbuilder_work"


# --- Import the QM FFT Analysis package --- 
try:
    # Ensure the package is accessible in your Python environment
    # You might need to adjust PYTHONPATH or install the package
    from QM_FFT_Analysis.utils.map_builder import MapBuilder
except ImportError as e:
    logging.error(f"Failed to import QM_FFT_Analysis: {e}")
    logging.error("Ensure the package is installed and accessible (check PYTHONPATH).")
    sys.exit(1)

# --- Function to consolidate MapBuilder results into HDF5 --- 
def consolidate_mapbuilder_to_hdf5(mapbuilder_subject_dir, output_h5_path):
    """
    Finds all .npy files in the MapBuilder output directory (data, analysis subdirs)
    and saves them into a single HDF5 file, preserving relative structure.
    """
    logging.info(f"Consolidating results from {mapbuilder_subject_dir} into {output_h5_path}")
    output_h5_path.parent.mkdir(parents=True, exist_ok=True)
    
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

# --- Main Analysis Logic ---
def main():
    logging.info(f"Starting Standalone QM FFT Analysis for subject: {subject_id}")
    logging.info(f"Input fMRI: {input_fmri_path}")
    logging.info(f"Input Mask: {input_mask_path}")
    logging.info(f"Temporary MapBuilder base dir: {temp_mapbuilder_base}")
    logging.info(f"Final HDF5 output: {output_hdf5_path}")

    if not input_fmri_path.exists():
        logging.error(f"Input fMRI file not found: {input_fmri_path}")
        sys.exit(1)
    if not input_mask_path.exists():
        logging.error(f"Input mask file not found: {input_mask_path}")
        sys.exit(1)

    mapbuilder_subject_dir = None # Define outside try block

    try:
        # --- Prepare Data --- 
        logging.info("Loading NIfTI data...")
        fmri_img = nib.load(input_fmri_path)
        mask_img = nib.load(input_mask_path)
        
        # Get the header information for verification
        logging.info(f"fMRI image dimensions: {fmri_img.shape}")
        logging.info(f"fMRI image header: TR={fmri_img.header.get_zooms()[-1] if len(fmri_img.header.get_zooms()) > 3 else 'Not defined'}")
        
        fmri_data = fmri_img.get_fdata(dtype=np.float32) 
        mask_data = mask_img.get_fdata().astype(bool)
        
        if fmri_data.shape[:3] != mask_data.shape:
            raise ValueError(f"Spatial dimensions mismatch: fMRI {fmri_data.shape[:3]} vs Mask {mask_data.shape}")
            
        affine = fmri_img.affine
        logging.info("Extracting voxel coordinates and time series...")
        mask_indices = np.array(np.where(mask_data)).T
        voxel_coords_ijk1 = np.hstack((mask_indices, np.ones((mask_indices.shape[0], 1))))
        voxel_coords_xyz = nib.affines.apply_affine(affine, voxel_coords_ijk1[:, :3])
        
        # Extract time series for each voxel in the mask
        voxel_time_series = fmri_data[mask_indices[:, 0], mask_indices[:, 1], mask_indices[:, 2], :]
        n_voxels, n_timepoints = voxel_time_series.shape
        logging.info(f"Extracted {n_voxels} voxels, {n_timepoints} time points.")
        logging.info(f"Time series shape (before transpose): {voxel_time_series.shape} [voxels, time]")
        
        # Transpose to get time as first dimension (required by MapBuilder)
        # MapBuilder expects strengths of shape [n_timepoints, n_voxels]
        strengths_real = np.ascontiguousarray(voxel_time_series.T)  # Explicitly make contiguous
        logging.info(f"Time series shape (after transpose): {strengths_real.shape} [time, voxels]")
        
        # Verify contiguity
        logging.info(f"Is strengths array C-contiguous: {strengths_real.flags['C_CONTIGUOUS']}")
        
        # Create complex array (real values with zero imaginary part)
        strengths_imag = np.zeros_like(strengths_real)
        strengths_complex = np.ascontiguousarray(strengths_real + 1j * strengths_imag)
        logging.info(f"Complex strengths shape: {strengths_complex.shape}, dtype: {strengths_complex.dtype}")
        logging.info(f"Is complex strengths array C-contiguous: {strengths_complex.flags['C_CONTIGUOUS']}")

        # Get spatial coordinates for each voxel
        x_coords = np.ascontiguousarray(voxel_coords_xyz[:, 0])
        y_coords = np.ascontiguousarray(voxel_coords_xyz[:, 1])
        z_coords = np.ascontiguousarray(voxel_coords_xyz[:, 2])
        
        logging.info(f"Coordinate arrays shapes - x: {x_coords.shape}, y: {y_coords.shape}, z: {z_coords.shape}")
        logging.info(f"Are coordinate arrays contiguous - x: {x_coords.flags['C_CONTIGUOUS']}, " +
                     f"y: {y_coords.flags['C_CONTIGUOUS']}, z: {z_coords.flags['C_CONTIGUOUS']}")

        # --- Run MapBuilder --- 
        logging.info("Initializing MapBuilder...")
        temp_mapbuilder_base.mkdir(parents=True, exist_ok=True) 

        map_builder = MapBuilder(
            subject_id=subject_id,
            output_dir=temp_mapbuilder_base, # Use temporary base directory
            x=x_coords,
            y=y_coords,
            z=z_coords,
            strengths=strengths_complex, 
            eps=finufft_precision,      
            dtype='complex128' # Ensure complex type is explicitly set
        )
        
        mapbuilder_subject_dir = temp_mapbuilder_base / subject_id # Construct the expected output path
        logging.info(f"Using MapBuilder intermediate output directory: {mapbuilder_subject_dir}")
        
        logging.info("Running MapBuilder processing (n_centers=1)...")
        analyses_to_run = [
            'magnitude', 'phase', 'local_variance', 
            'temporal_diff_magnitude', 'temporal_diff_phase'      
        ]
        map_builder.process_map(
            n_centers=1, # Force n=1 as per the original script's logic
            radius=kspace_masks_radius,       
            analyses_to_run=analyses_to_run,
            k_neighbors_local_var=local_var_k
        )
        logging.info(f"MapBuilder intermediate processing complete. Results in: {mapbuilder_subject_dir}")

        # --- Consolidate Results to HDF5 --- 
        if mapbuilder_subject_dir.exists():
             consolidate_mapbuilder_to_hdf5(mapbuilder_subject_dir, output_hdf5_path)
        else:
             logging.error(f"MapBuilder output directory not found after processing: {mapbuilder_subject_dir}")
             sys.exit(1)
        
        # --- Optional: Clean up temporary directory ---
        # import shutil
        # logging.info(f"Cleaning up temporary directory: {temp_mapbuilder_base}")
        # shutil.rmtree(temp_mapbuilder_base)

    except Exception as e:
        logging.exception(f"Error during Standalone QM FFT Analysis for subject {subject_id}: {e}")
        sys.exit(1) 
    finally:
        # Optional cleanup, similar to original script
        pass 

if __name__ == "__main__":
    main()
    logging.info(f"Standalone QM FFT test script finished. Output: {output_hdf5_path}") 
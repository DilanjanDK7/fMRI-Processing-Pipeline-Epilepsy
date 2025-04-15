import numpy as np
import nibabel as nib
from pathlib import Path
import logging
import sys
import h5py 
import glob 
import os 
import argparse
import shutil

# Add QM_FFT_Feature_Package path to sys.path
qm_fft_package_path = '/app/QM_FFT_Feature_Package'
sys.path.insert(0, qm_fft_package_path)

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
parser.add_argument('--sample', action='store_true',
                    help="Process only a sample number of time points for testing.")
parser.add_argument('--sample_tp', type=int, default=20,
                    help="Number of time points to use when --sample is active.")

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
    logging.info(f"--> Entering consolidate_mapbuilder_to_hdf5")
    logging.info(f"Consolidating results from {mapbuilder_subject_dir} into {output_h5_path}")
    output_h5_path.parent.mkdir(parents=True, exist_ok=True)
    
    files_processed_count = 0
    with h5py.File(output_h5_path, 'w') as hf:
        search_dirs = [mapbuilder_subject_dir / 'data', mapbuilder_subject_dir / 'analysis']
        npy_files = []
        logging.info(f"--> Searching for .npy files in: {search_dirs}")
        for d in search_dirs:
            if d.exists():
                # Recursively find all .npy files
                found = glob.glob(str(d / '**/*.npy'), recursive=True)
                logging.info(f"--> Found {len(found)} .npy files in {d}")
                npy_files.extend(found) 
        
        logging.info(f"--> Total .npy files found: {len(npy_files)}")
        if not npy_files:
            logging.warning(f"No .npy files found in {mapbuilder_subject_dir} subdirectories.")
            logging.info("--> Exiting consolidate_mapbuilder_to_hdf5 (no files)")
            return
            
        for npy_file in npy_files:
            try:
                logging.debug(f"--> Processing file: {npy_file}")
                data = np.load(npy_file)
                relative_path = os.path.relpath(npy_file, mapbuilder_subject_dir)
                dataset_path = Path(relative_path).with_suffix('').as_posix() 
                
                logging.debug(f"Saving {npy_file} to HDF5 dataset: {dataset_path}")
                hf.create_dataset(dataset_path, data=data)
                files_processed_count += 1
            except Exception as e:
                logging.error(f"Failed to load or save {npy_file} to HDF5: {e}")

    logging.info(f"--> HDF5 consolidation complete. Processed {files_processed_count} files.")
    logging.info("--> Exiting consolidate_mapbuilder_to_hdf5 (success)")

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
        
        # --- Sample Time Points if requested ---
        if args.sample:
            # Reduce spatial extent for sampling as well
            logging.warning("Applying SPATIAL sampling for testing (--sample active).")
            nx, ny, nz, _ = fmri_data.shape # Get dimensions
            x_center, y_center, z_center = nx // 2, ny // 2, nz // 2
            x_half, y_half, z_half = 1, 1, 1 # Reduced to smallest region (3x3x3 voxels)
            x_range = slice(x_center - x_half, x_center + x_half + 1)
            y_range = slice(y_center - y_half, y_center + y_half + 1)
            z_range = slice(z_center - z_half, z_center + z_half + 1)
            
            logging.warning(f"Spatial sample region: X={x_range}, Y={y_range}, Z={z_range}")
            
            # Create a spatial mask for the sample region
            spatial_sample_mask = np.zeros(fmri_data.shape[:3], dtype=bool)
            spatial_sample_mask[x_range, y_range, z_range] = True
            
            # Combine with original mask
            original_mask = mask_data # Assuming mask_data holds the loaded/calculated mask
            combined_mask = original_mask & spatial_sample_mask
            
            # Re-extract coordinates and time series based on combined mask
            logging.info("Re-extracting data for spatial sample...")
            mask_indices = np.array(np.where(combined_mask)).T
            if mask_indices.shape[0] == 0:
                logging.error("No voxels found in the combined spatial sample mask! Halting.")
                sys.exit(1)
            
            voxel_coords_ijk1 = np.hstack((mask_indices, np.ones((mask_indices.shape[0], 1))))
            voxel_coords_xyz = nib.affines.apply_affine(affine, voxel_coords_ijk1[:, :3])
            voxel_time_series = fmri_data[mask_indices[:, 0], mask_indices[:, 1], mask_indices[:, 2], :]
            n_voxels, n_timepoints = voxel_time_series.shape # Update n_voxels, n_timepoints
            logging.info(f"Extracted {n_voxels} voxels (spatially sampled), {n_timepoints} time points.")
            
            # Original time point sampling logic (applied AFTER spatial sampling)
            if args.sample_tp < n_timepoints:
                logging.warning(f"--sample active: Using only the first {args.sample_tp} time points out of {n_timepoints}.")
                voxel_time_series = voxel_time_series[:, :args.sample_tp] # Sample time points
                n_timepoints = args.sample_tp # Update n_timepoints
                logging.info(f"Time points sampled down to {n_timepoints}.")
            else:
                logging.warning(f"--sample active, but requested sample_tp ({args.sample_tp}) >= total timepoints ({n_timepoints}). Using all {n_timepoints} time points.")
            
            # Transpose for MapBuilder
            strengths_real = np.ascontiguousarray(voxel_time_series.T)
            logging.info(f"Sampled time series shape (after transpose): {strengths_real.shape} [time, voxels]")
            strengths_imag = np.zeros_like(strengths_real)
            strengths_complex = np.ascontiguousarray(strengths_real + 1j * strengths_imag)
            logging.info(f"Sampled complex strengths shape: {strengths_complex.shape}")

            # Update coordinate arrays for the spatially sampled voxels
            x_coords = np.ascontiguousarray(voxel_coords_xyz[:, 0])
            y_coords = np.ascontiguousarray(voxel_coords_xyz[:, 1])
            z_coords = np.ascontiguousarray(voxel_coords_xyz[:, 2])
            
            # Normalize coordinates to avoid FINUFFT out-of-range errors
            logging.info("Original coordinate ranges: X=[{:.2f}, {:.2f}], Y=[{:.2f}, {:.2f}], Z=[{:.2f}, {:.2f}]".format(
                x_coords.min(), x_coords.max(), y_coords.min(), y_coords.max(), z_coords.min(), z_coords.max()))
            
            # Scale coordinates to fit within the expected range for FINUFFT
            # FINUFFT expects coords in range [-3π, 3π]
            max_allowed = 3.0  # We'll scale to [-max_allowed, max_allowed] which is within FINUFFT's range
            max_coord = max(abs(x_coords).max(), abs(y_coords).max(), abs(z_coords).max())
            scale_factor = max_allowed / max_coord if max_coord > 0 else 1.0
            
            x_coords = x_coords * scale_factor
            y_coords = y_coords * scale_factor
            z_coords = z_coords * scale_factor
            
            logging.info("Normalized coordinate ranges (scale={:.4f}): X=[{:.2f}, {:.2f}], Y=[{:.2f}, {:.2f}], Z=[{:.2f}, {:.2f}]".format(
                scale_factor, x_coords.min(), x_coords.max(), y_coords.min(), y_coords.max(), z_coords.min(), z_coords.max()))
            
            logging.info(f"Sampled coordinate arrays shapes - x: {x_coords.shape}, y: {y_coords.shape}, z: {z_coords.shape}")

        else: # If not args.sample, run original data prep
            # Original data prep logic remains here...
            # Extract time series for each voxel in the mask (original full mask)
            voxel_time_series = fmri_data[mask_indices[:, 0], mask_indices[:, 1], mask_indices[:, 2], :]
            n_voxels, n_timepoints = voxel_time_series.shape
            # Transpose to get time as first dimension (required by MapBuilder)
            strengths_real = np.ascontiguousarray(voxel_time_series.T)
            strengths_imag = np.zeros_like(strengths_real)
            strengths_complex = np.ascontiguousarray(strengths_real + 1j * strengths_imag)
            # Get spatial coordinates for each voxel (original full mask)
            x_coords = np.ascontiguousarray(voxel_coords_xyz[:, 0])
            y_coords = np.ascontiguousarray(voxel_coords_xyz[:, 1])
            z_coords = np.ascontiguousarray(voxel_coords_xyz[:, 2])
            
            # Normalize coordinates to avoid FINUFFT out-of-range errors (same as in sampling branch)
            logging.info("Original coordinate ranges: X=[{:.2f}, {:.2f}], Y=[{:.2f}, {:.2f}], Z=[{:.2f}, {:.2f}]".format(
                x_coords.min(), x_coords.max(), y_coords.min(), y_coords.max(), z_coords.min(), z_coords.max()))
            
            # Scale coordinates to fit within the expected range for FINUFFT
            # FINUFFT expects coords in range [-3π, 3π]
            max_allowed = 3.0  # We'll scale to [-max_allowed, max_allowed] which is within FINUFFT's range
            max_coord = max(abs(x_coords).max(), abs(y_coords).max(), abs(z_coords).max())
            scale_factor = max_allowed / max_coord if max_coord > 0 else 1.0
            
            x_coords = x_coords * scale_factor
            y_coords = y_coords * scale_factor
            z_coords = z_coords * scale_factor
            
            logging.info("Normalized coordinate ranges (scale={:.4f}): X=[{:.2f}, {:.2f}], Y=[{:.2f}, {:.2f}], Z=[{:.2f}, {:.2f}]".format(
                scale_factor, x_coords.min(), x_coords.max(), y_coords.min(), y_coords.max(), z_coords.min(), z_coords.max()))
            # -------- End of original data prep ---------

        # --- Run MapBuilder --- 
        logging.info("Initializing MapBuilder...")
        temp_mapbuilder_base.mkdir(parents=True, exist_ok=True) 

        map_builder = MapBuilder(
            subject_id=subject_id,
            output_dir=temp_mapbuilder_base, # Use temporary base directory
            x=x_coords, # Use potentially sampled coords
            y=y_coords,
            z=z_coords,
            strengths=strengths_complex, # Use potentially sampled strengths
            eps=finufft_precision,      
            dtype='complex128' # Ensure complex type is explicitly set
        )
        
        mapbuilder_subject_dir = temp_mapbuilder_base / subject_id # Construct the expected output path
        logging.info(f"Using MapBuilder intermediate output directory: {mapbuilder_subject_dir}")
        
        logging.info("Running MapBuilder processing (n_centers=1)...")
        analyses_to_run = [
            'magnitude', 'phase', # 'local_variance', # Commented out as requested
            'temporal_diff_magnitude', 'temporal_diff_phase' # Re-enabled these
        ]
        map_builder.process_map(
            n_centers=1, # Force n=1 as per the original script's logic
            radius=kspace_masks_radius,       
            analyses_to_run=analyses_to_run,
            k_neighbors_local_var=local_var_k
        )
        logging.info(f"MapBuilder intermediate processing complete. Results in: {mapbuilder_subject_dir}")

        # --- Consolidate Results to HDF5 --- 
        logging.info("--> Checking if MapBuilder output directory exists...")
        if mapbuilder_subject_dir.exists():
             logging.info(f"--> Directory found. Calling consolidate_mapbuilder_to_hdf5.")
             consolidate_mapbuilder_to_hdf5(mapbuilder_subject_dir, output_hdf5_path)
             logging.info("--> Returned from consolidate_mapbuilder_to_hdf5.")
        else:
             logging.error(f"MapBuilder output directory not found after processing: {mapbuilder_subject_dir}")
             sys.exit(1)
        
        # --- Optional: Clean up temporary directory ---
        if mapbuilder_subject_dir and mapbuilder_subject_dir.exists():
             logging.info(f"Cleaning up temporary directory: {mapbuilder_subject_dir.parent}")
             shutil.rmtree(mapbuilder_subject_dir.parent)

    except Exception as e:
        logging.exception(f"Error during Standalone QM FFT Analysis for subject {subject_id}: {e}")
        sys.exit(1) 
    finally:
        # Optional cleanup, similar to original script
        pass 

if __name__ == "__main__":
    # Parse arguments first
    args = parser.parse_args() 
    # Then call main, which now uses the parsed args
    main()
    logging.info(f"Standalone QM FFT test script finished. Output: {output_hdf5_path}") 
# run_combined_pipeline.py

import argparse
import subprocess
import sys
import logging
from pathlib import Path
from bids import BIDSLayout

# --- Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Paths relative to this script's location (project root)
FMRIREP_SNAKEFILE = Path("fmriprep/Snakefile")
FEATURE_EXTRACTION_WRAPPER = Path("Feature_extraction_Container/run_container_pipeline.sh")
# Default location for dcm2bids config if not provided
DEFAULT_DCM2BIDS_CONFIG_NAME = "dcm2bids_config.json"

# --- Helper Functions ---

def run_command(command, cwd=None):
    """Executes a shell command and logs output."""
    logging.info(f"Running command: {' '.join(map(str, command))}")
    try:
        process = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd # Run command in the specified directory (often project root)
        )
        logging.info(f"Command stdout:\n{process.stdout}")
        if process.stderr:
            logging.warning(f"Command stderr:\n{process.stderr}")
        logging.info(f"Command completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}")
        logging.error(f"Command: {' '.join(map(str, command))}")
        logging.error(f"stdout:\n{e.stdout}")
        logging.error(f"stderr:\n{e.stderr}")
        return False
    except FileNotFoundError:
        logging.error(f"Error: Command not found: {command[0]}. Is it installed and in PATH?")
        return False

def convert_dicom_to_bids(dicom_dir: Path, bids_output_dir: Path, dcm2bids_config: Path, participant_id: str | None = None, session_id: str | None = None):
    """
    Uses dcm2bids to convert DICOM data to BIDS format.

    Args:
        dicom_dir: Path to the directory containing DICOM files.
        bids_output_dir: Path to the directory where BIDS output should be saved.
        dcm2bids_config: Path to the dcm2bids JSON configuration file.
        participant_id: Optional participant label (e.g., "01").
        session_id: Optional session label (e.g., "Session1").

    Returns:
        True if conversion was successful, False otherwise.
    """
    if not dcm2bids_config.is_file():
         logging.error(f"dcm2bids config file not found: {dcm2bids_config}")
         return False

    logging.info(f"Starting DICOM to BIDS conversion for {dicom_dir}")
    bids_output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "dcm2bids",
        "-d", str(dicom_dir),
        "-o", str(bids_output_dir),
        "-c", str(dcm2bids_config),
    ]
    if participant_id:
        cmd.extend(["-p", participant_id])
    if session_id:
         cmd.extend(["-s", session_id])

    # dcm2bids often benefits from running in the output dir context
    if not run_command(cmd, cwd=bids_output_dir):
        logging.error("DICOM to BIDS conversion failed.")
        return False

    logging.info(f"DICOM to BIDS conversion completed. Output in: {bids_output_dir}")
    return True

def fix_permissions(directory: Path):
    """
    Fix permissions on a directory and its contents to ensure they are readable and writable.
    
    Args:
        directory: Path to the directory to fix permissions for.
    """
    logging.info(f"Fixing permissions for {directory}...")
    try:
        # Use subprocess to run chmod recursively
        subprocess.run(
            ["sudo", "chmod", "-R", "775", str(directory)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logging.info(f"Fixed permissions for {directory}")
        return True
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to fix permissions: {e.stderr}")
        return False

# --- Pipeline Stages ---

def run_fmriprep_pipeline(bids_input_dir: Path, fmriprep_output_dir: Path, cores: int, participant_label: list[str] | None = None, memory_mb_override: int | None = None):
    """
    Runs the fmriprep Snakemake pipeline.

    Args:
        bids_input_dir: Path to the BIDS input dataset.
        fmriprep_output_dir: Path where fmriprep derivatives should be saved.
        cores: Number of cores to use for Snakemake.
        participant_label: Optional list of specific participant labels to process.
        memory_mb_override: Optional memory limit in MB to pass directly to fmriprep.

    Returns:
        True if successful, False otherwise.
    """
    logging.info("--- Starting fMRIPrep Pipeline Stage (Skipping Denoising) ---")
    fmriprep_output_dir.mkdir(parents=True, exist_ok=True)

    # Use pybids to find subjects and tasks to potentially build specific targets
    try:
        layout = BIDSLayout(str(bids_input_dir), validate=True)
        # Use participant_label if provided, otherwise get all subjects
        subjects_to_process = participant_label if participant_label else layout.get_subjects()
        tasks = layout.get_tasks()
        if not subjects_to_process:
            logging.error(f"No subjects found or specified in BIDS directory: {bids_input_dir}")
            return False
        logging.info(f"Processing subjects: {subjects_to_process}")
        logging.info(f"Found tasks: {tasks}")
    except Exception as e:
        logging.error(f"PyBIDS error reading {bids_input_dir}: {e}")
        return False

    # --- Generate target file paths for the run_fmriprep rule --- 
    # This ensures snakemake only runs fmriprep and its dependencies
    fmriprep_targets = []
    for subject in subjects_to_process:
        for task in tasks:
            # Construct expected output paths based on the run_fmriprep rule
            # Add 'sub-' prefix to match the Docker container's output format
            bold_out = fmriprep_output_dir / f"sub-{subject}/func/sub-{subject}_task-{task}_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz"
            confounds_out = fmriprep_output_dir / f"sub-{subject}/func/sub-{subject}_task-{task}_desc-confounds_timeseries.tsv"
            mask_out = fmriprep_output_dir / f"sub-{subject}/func/sub-{subject}_task-{task}_space-MNI152NLin2009cAsym_desc-brain_mask.nii.gz"
            # Add report target as well, if the check_fmriprep_reports rule is desired
            report_out = fmriprep_output_dir / f"sub-{subject}.html"
            
            fmriprep_targets.extend([str(bold_out), str(confounds_out), str(mask_out), str(report_out)])

    if not fmriprep_targets:
        logging.error("Could not generate any target files for Snakemake.")
        return False

    # Define Snakemake command
    cmd = [
        "snakemake",
        "--snakefile", str(FMRIREP_SNAKEFILE.resolve()),
        "--directory", str(FMRIREP_SNAKEFILE.parent.resolve()),
    ]
    # Add config overrides
    config_opts = [
        f"bids_input_dir={str(bids_input_dir.resolve())}",
        f"derivatives_output_dir={str(fmriprep_output_dir.resolve())}",
    ]
    if memory_mb_override is not None:
        # Use a simple key for command-line config
        config_opts.append(f"cmd_mem_mb={memory_mb_override}") 
        logging.info(f"Passing memory override to Snakemake: cmd_mem_mb={memory_mb_override} MB")
    
    cmd.extend(["--config"] + config_opts)
    
    # Add other flags
    cmd.extend([
        "--cores", str(cores),
        "--use-conda",
        "--rerun-incomplete",
        "--keep-going",
        "--latency-wait", "60",  # Wait up to 60 seconds for output files to appear
        "-p" # Print shell commands
    ])

    # Add the specific target files to the command
    cmd.extend(fmriprep_targets)

    logging.info(f"Targeting specific outputs: {fmriprep_targets}")

    # Run the command from the project root
    if not run_command(cmd, cwd=None):
        logging.error("fMRIPrep pipeline stage failed.")
        return False

    # Fix permissions for the output directory
    fix_permissions(fmriprep_output_dir)

    logging.info("--- fMRIPrep Pipeline Stage Completed ---")
    return True


def run_feature_extraction_pipeline(feature_input_dir: Path, cores: int, features: list[str] | None = None):
    """
    Runs the feature extraction pipeline using its wrapper script.

    Args:
        feature_input_dir: Path to the directory containing fmriprep outputs
                           (this will be passed as --input to the wrapper script).
        cores: Number of cores to use.
        features: Optional list of specific features to calculate (e.g., ['alff', 'reho']).
                  If None, the wrapper script's default behavior is used.

    Returns:
        True if successful, False otherwise.
    """
    logging.info("--- Starting Feature Extraction Pipeline Stage ---")

    if not FEATURE_EXTRACTION_WRAPPER.exists():
         logging.error(f"Feature extraction wrapper script not found: {FEATURE_EXTRACTION_WRAPPER}")
         return False
    if not feature_input_dir.exists():
        logging.error(f"Input directory for feature extraction not found: {feature_input_dir}")
        logging.error("This directory should contain the outputs from the fMRIPrep stage.")
        return False

    # Ensure the wrapper script is executable
    try:
        FEATURE_EXTRACTION_WRAPPER.chmod(FEATURE_EXTRACTION_WRAPPER.stat().st_mode | 0o111) # Add execute permission u+x, g+x, o+x
    except OSError as e:
        logging.warning(f"Could not set execute permission on {FEATURE_EXTRACTION_WRAPPER}: {e}")


    cmd = [
        str(FEATURE_EXTRACTION_WRAPPER.resolve()),
        "--input", str(feature_input_dir.resolve()),
        "--cores", str(cores),
        # Add --force flag if needed: "--force"
    ]

    if features:
        cmd.extend(["--features", ",".join(features)])

    # The wrapper script should handle running inside its own directory context if necessary
    # We run it from the project root.
    if not run_command(cmd, cwd=None):
        logging.error("Feature extraction pipeline stage failed.")
        return False

    # Fix permissions for feature extraction outputs
    fix_permissions(feature_input_dir)
    
    # Also fix workflow directory permissions
    workflow_dir = FEATURE_EXTRACTION_WRAPPER.parent / "workflows"
    if workflow_dir.exists():
        fix_permissions(workflow_dir)

    logging.info("--- Feature Extraction Pipeline Stage Completed ---")
    logging.info(f"Feature extraction outputs should be located within: {feature_input_dir}")
    logging.info("(Typically in subdirectories like 'sub-*/func/Analytical_metrics')")
    return True


# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Run the combined fMRIPrep and Feature Extraction pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("input_dir", type=Path,
                        help="Path to the input data directory. Can be BIDS or DICOM (if --is_dicom is set).")
    parser.add_argument("output_dir", type=Path,
                        help="Path to the main output directory where all results (BIDS, derivatives) will be stored.")
    parser.add_argument("--is_dicom", action="store_true",
                        help="Flag indicating the input_dir contains DICOM files needing conversion to BIDS.")
    parser.add_argument("--dcm2bids_config", type=Path, default=None,
                        help="Path to the dcm2bids JSON configuration file (required if --is_dicom is set). "
                             f"Defaults to '{DEFAULT_DCM2BIDS_CONFIG_NAME}' in the input directory if not provided.")
    parser.add_argument("--participant_label", nargs="+", default=None,
                        help="Optional list of participant labels (e.g., 01 02 03) to process. "
                             "If not specified, all participants found in the BIDS dataset will be processed by fmriprep. "
                             "Note: Feature extraction script might process all subjects found in its input regardless of this.")
    parser.add_argument("--session_label", default=None,
                        help="Optional session label for DICOM conversion.")
    parser.add_argument("--features", nargs="+", default=None,
                        help="Optional list of specific features to extract (e.g., alff reho). "
                             "If not specified, the feature extraction script defaults will be used.")
    parser.add_argument("--cores", type=int, default=4,
                        help="Number of CPU cores to use for pipeline stages.")
    parser.add_argument("--memory_mb", type=int, default=None,
                        help="Memory limit in MB for fMRIPrep stage (overrides config).")
    parser.add_argument("--skip_fmriprep", action="store_true",
                        help="Skip the fMRIPrep stage (assumes outputs already exist).")
    parser.add_argument("--skip_feature_extraction", action="store_true",
                        help="Skip the Feature Extraction stage.")


    args = parser.parse_args()

    # --- Input Handling ---
    input_dir = args.input_dir.resolve()
    main_output_dir = args.output_dir.resolve()
    main_output_dir.mkdir(parents=True, exist_ok=True)

    bids_dir = input_dir
    if args.is_dicom:
        logging.info("Input identified as DICOM, attempting conversion...")
        converted_bids_path = main_output_dir / "bids_converted"
        config_path = args.dcm2bids_config

        if not config_path:
             # Try finding default config in input or script dir
             potential_config = input_dir / DEFAULT_DCM2BIDS_CONFIG_NAME
             if potential_config.is_file():
                  config_path = potential_config
             else:
                  script_dir_config = Path(__file__).parent / DEFAULT_DCM2BIDS_CONFIG_NAME
                  if script_dir_config.is_file():
                       config_path = script_dir_config
                  else:
                       logging.error(f"dcm2bids config file not specified with --dcm2bids_config and default '{DEFAULT_DCM2BIDS_CONFIG_NAME}' not found.")
                       sys.exit(1)
        elif not args.dcm2bids_config.is_file():
            logging.error(f"Specified dcm2bids config file not found: {args.dcm2bids_config}")
            sys.exit(1)

        logging.info(f"Using dcm2bids config: {config_path}")

        # For simplicity, converting all participants found in DICOM dir
        # dcm2bids participant/session flags might need adjustment based on actual tool usage
        if not convert_dicom_to_bids(input_dir, converted_bids_path, config_path.resolve(), session_id=args.session_label):
            sys.exit(1)
        bids_dir = converted_bids_path
    else:
        logging.info(f"Input identified as BIDS: {bids_dir}")
        # Basic check if it looks like a BIDS directory
        if not (bids_dir / "dataset_description.json").exists():
             logging.warning(f"Warning: {bids_dir / 'dataset_description.json'} not found. Input might not be a valid BIDS dataset.")


    # Define the primary output directory for fmriprep derivatives
    fmriprep_output_base = main_output_dir / "derivatives"

    # --- Run Pipeline Stages ---
    fmriprep_success = True
    if not args.skip_fmriprep:
        fmriprep_success = run_fmriprep_pipeline(bids_dir, fmriprep_output_base, args.cores, args.participant_label, args.memory_mb)
        if not fmriprep_success:
            logging.error("fMRIPrep stage failed. Aborting.")
            sys.exit(1)
    else:
        logging.info("Skipping fMRIPrep stage as requested.")
        if not fmriprep_output_base.exists():
             logging.warning(f"fMRIPrep skipped, but output directory {fmriprep_output_base} does not exist. Feature extraction might fail.")


    feature_extraction_success = True
    if not args.skip_feature_extraction:
        if fmriprep_success or args.skip_fmriprep: # Only run if fmriprep succeeded or was skipped
             feature_extraction_success = run_feature_extraction_pipeline(fmriprep_output_base, args.cores, args.features)
             if not feature_extraction_success:
                  logging.error("Feature Extraction stage failed.")
                  # Decide if this is a critical failure
                  # sys.exit(1)
        else:
             logging.warning("Skipping Feature Extraction because fMRIPrep stage failed.")
             feature_extraction_success = False
    else:
         logging.info("Skipping Feature Extraction stage as requested.")


    # --- Completion ---
    logging.info("--- Combined Pipeline Execution Finished ---")
    if not fmriprep_success or not feature_extraction_success:
         logging.warning("One or more pipeline stages reported errors.")
    else:
         logging.info("All requested pipeline stages completed successfully.")
         logging.info(f"Final outputs located in: {main_output_dir}")


if __name__ == "__main__":
    main()




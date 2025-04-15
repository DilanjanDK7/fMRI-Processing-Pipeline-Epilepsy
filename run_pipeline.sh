#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PYTHON_CMD="python3"
PIPELINE_SCRIPT="run_combined_pipeline.py"
REQUIRED_PACKAGES=("bids" "snakemake" "dcm2bids") # Package names for pip/import check

# Flag for force unlocking Snakemake
FORCE_UNLOCK=false

# --- Helper Functions ---
usage() {
    echo "Usage: $0 <input_directory> <output_directory> [python_script_options...]" 
    echo ""
    echo "Arguments:"
    echo "  <input_directory>    Path to the input data (BIDS or DICOM)."
    echo "  <output_directory>   Path to the desired output directory."
    echo "  [python_script_options...]  Optional arguments to pass directly to $PIPELINE_SCRIPT"
    echo "                              (e.g., --is_dicom, --cores N, --features F1 F2, --skip_fmriprep)."
    echo ""
    echo "Additional options:"
    echo "  --force_unlock       Force unlock any Snakemake locks before running"
    echo "  --fix_permissions    Fix permissions of output directory after running"
    echo ""
    echo "Example:"
    echo "  $0 /data/my_bids /results/pipeline_run --cores 8"
    echo "  $0 /data/my_dicoms /results/dicom_run --is_dicom --dcm2bids_config /path/to/config.json"
    exit 1
}

check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: Required command '$1' not found in PATH."
        exit 1
    fi
}

check_docker_running() {
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker daemon does not appear to be running."
        echo "Please start Docker and try again."
        exit 1
    fi
}

unlock_snakemake() {
    echo "Unlocking Snakemake locks in fmriprep directory..."
    if [ -d "fmriprep/.snakemake" ]; then
        rm -f fmriprep/.snakemake/*.lock
        rm -rf fmriprep/.snakemake/locks
        echo "Locks removed."
    else
        echo "No .snakemake directory found, nothing to unlock."
    fi
}

fix_permissions() {
    echo "Fixing permissions for output directory: $1"
    sudo chmod -R 775 "$1"
    echo "Permissions fixed."
}

# --- Process custom flags and extract them from arguments ---
# These variables will hold arguments that should be passed to the Python script
PYTHON_ARGS=()
FIX_PERMISSIONS=false

# Save the first two positional arguments (input and output directories)
if [ "$#" -lt 2 ]; then
    echo "Error: Missing required arguments."
    usage
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
shift 2 # Remove the first two arguments, leaving any extras for processing

# Process remaining arguments
while [ "$#" -gt 0 ]; do
    case "$1" in
        --force_unlock)
            FORCE_UNLOCK=true
            shift
            ;;
        --fix_permissions)
            FIX_PERMISSIONS=true
            shift
            ;;
        *)
            # For any other arguments, pass them through to the Python script
            PYTHON_ARGS+=("$1")
            shift
            ;;
    esac
done

# --- Dependency Checks ---
echo "--- Checking Dependencies ---"

# 1. Check Python
echo "Checking for Python 3..."
check_command "$PYTHON_CMD"
echo "Found Python 3."

# 2. Check Pip
echo "Checking for Pip..."
if command -v pip >/dev/null 2>&1; then
    PIP_CMD="pip"
elif $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
    PIP_CMD="$PYTHON_CMD -m pip"
else
    echo "Error: Could not find 'pip' or '$PYTHON_CMD -m pip'. Please install pip for Python 3."
    exit 1
fi
echo "Found Pip ($PIP_CMD)."

# 3. Check Python Packages
echo "Checking required Python packages..."
missing_packages=()
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    # Use import check as package name might differ slightly from import name (though not for these)
    if ! $PYTHON_CMD -c "import $pkg" >/dev/null 2>&1; then
        # Fallback check using pip show for the common case where import name = package name
        if ! $PIP_CMD show "$pkg" >/dev/null 2>&1; then
             echo "Package '$pkg' seems to be missing."
             missing_packages+=("$pkg")
        else
             echo "Package '$pkg' found via pip, but failed import check (potential environment issue?)."
        fi
    fi
done

if [ ${#missing_packages[@]} -ne 0 ]; then
    echo "Attempting to install missing packages using '$PIP_CMD install --user'..."
    if ! $PIP_CMD install --user "${missing_packages[@]}"; then
        echo "Error: Failed to install missing Python packages."
        echo "Please install them manually: $PIP_CMD install --user ${missing_packages[*]}"
        exit 1
    fi
    echo "Successfully installed missing packages."
    # Recommend re-sourcing profile or restarting terminal if PATH needs update for user installs
    echo "Note: You might need to restart your terminal session for the installed packages to be found."
else
    echo "All required Python packages are present."
fi

# 4. Check Docker
echo "Checking for Docker..."
check_command "docker"
echo "Found Docker command."
echo "Checking if Docker daemon is running..."
check_docker_running
echo "Docker daemon is running."

# 5. Check Pipeline Script
echo "Checking for pipeline script ($PIPELINE_SCRIPT)..."
if [ ! -f "$PIPELINE_SCRIPT" ]; then
    echo "Error: Pipeline script '$PIPELINE_SCRIPT' not found in the current directory ($(pwd))."
    exit 1
fi
echo "Found $PIPELINE_SCRIPT."

echo "--- Dependency Checks Complete ---"

# --- Handle Force Unlock if Requested ---
if [ "$FORCE_UNLOCK" = true ]; then
    unlock_snakemake
fi

# --- Execute Pipeline ---
echo ""
echo "--- Starting Combined Pipeline using $PIPELINE_SCRIPT ---"

# Construct the command
pipeline_command=("$PYTHON_CMD" "$PIPELINE_SCRIPT" "$INPUT_DIR" "$OUTPUT_DIR" "${PYTHON_ARGS[@]}")

echo "Executing: ${pipeline_command[*]}"
echo ""

# Run the python script, passing through input/output dirs and any extra args
if ! "${pipeline_command[@]}"; then
    echo ""
    echo "Error: The pipeline script ($PIPELINE_SCRIPT) failed."
    exit 1
fi

# Fix permissions if requested
if [ "$FIX_PERMISSIONS" = true ]; then
    fix_permissions "$OUTPUT_DIR"
    
    # Also fix permissions of the feature extraction container workflows
    if [ -d "Feature_extraction_Container/workflows" ]; then
        echo "Fixing permissions for Feature_extraction_Container/workflows..."
        sudo chmod -R 775 "Feature_extraction_Container/workflows"
        echo "Feature extraction workflow permissions fixed."
    fi
fi

echo ""
echo "--- Combined Pipeline Finished ---"
echo "Check logs and the output directory '$OUTPUT_DIR' for results."

exit 0 
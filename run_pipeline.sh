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
    echo "Usage: $0 [OPTIONS] INPUT_DIR OUTPUT_DIR [ADDITIONAL_ARGS]"
    echo
    echo "Required Arguments:"
    echo "  INPUT_DIR               Path to the BIDS input directory"
    echo "  OUTPUT_DIR              Path to the output directory"
    echo
    echo "Options:"
    echo "  --force_unlock          Force unlock any snakemake locks"
    echo "  --fix_permissions       Fix permissions of the output directory"
    echo "  --cores NUM             Number of CPU cores to use (default: auto-detect)"
    echo "  --memory MB             Memory limit in MB (default: 0 - no limit)"
    echo "  --skip_fmriprep         Skip the fMRIPrep stage and only run feature extraction"
    echo "  --help                  Display this help message"
    echo
    echo "Any additional arguments passed will be forwarded to the pipeline script."
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
    echo "Checking for Snakemake locks in all relevant directories..."
    
    # Check fmriprep directory
    if [ -d "fmriprep/.snakemake" ]; then
        echo "Removing locks from fmriprep/.snakemake..."
        rm -f fmriprep/.snakemake/*.lock
        rm -rf fmriprep/.snakemake/locks
        rm -rf fmriprep/.snakemake/incomplete
        # Also remove metadata that might cause issues
        rm -f fmriprep/.snakemake/metadata/*.metadata.json 2>/dev/null || true
        echo "fMRIPrep locks removed."
    fi
    
    # Check Feature_extraction_Container
    if [ -d "Feature_extraction_Container/workflows/.snakemake" ]; then
        echo "Removing locks from Feature_extraction_Container/workflows/.snakemake..."
        rm -f Feature_extraction_Container/workflows/.snakemake/*.lock
        rm -rf Feature_extraction_Container/workflows/.snakemake/locks
        rm -rf Feature_extraction_Container/workflows/.snakemake/incomplete
        # Also remove metadata that might cause issues
        rm -f Feature_extraction_Container/workflows/.snakemake/metadata/*.metadata.json 2>/dev/null || true
        echo "Feature extraction locks removed."
    fi
    
    echo "Lock check and cleanup complete."
}

fix_permissions() {
    local directory="$1"
    echo "Fixing permissions for directory: $directory"
    
    # Try multiple strategies, starting with non-sudo
    if chmod -R u+rw "$directory" 2>/dev/null; then
        echo "Permissions fixed (regular chmod)."
        return 0
    fi
    
    # If that failed, try with sudo
    if sudo chmod -R u+rw "$directory" 2>/dev/null; then
        echo "Permissions fixed (sudo chmod u+rw)."
        return 0
    fi
    
    # More aggressive approach
    if sudo chmod -R 775 "$directory" 2>/dev/null; then
        echo "Permissions fixed (sudo chmod 775)."
        return 0
    fi
    
    # Last resort - change ownership
    if sudo chown -R "$(whoami):$(whoami)" "$directory" 2>/dev/null; then
        echo "Permissions fixed (changed ownership)."
        return 0
    fi
    
    echo "Warning: Could not fix permissions for $directory"
    return 1
}

check_and_unlock_existing_outputs() {
    local directory="$1"
    
    echo "Checking for existing outputs in: $directory"
    
    if [ ! -d "$directory" ]; then
        echo "Directory doesn't exist yet, nothing to check or unlock."
        return 0
    fi
    
    echo "Checking if outputs need permission fixes..."
    
    # Check derivatives directory which contains most outputs
    if [ -d "$directory/derivatives" ]; then
        # Find files with problematic permissions
        local readonly_files=$(find "$directory/derivatives" -type f -not -writable 2>/dev/null | wc -l)
        
        if [ "$readonly_files" -gt 0 ]; then
            echo "Found $readonly_files files with read-only permissions in derivatives directory. Fixing..."
            fix_permissions "$directory/derivatives"
            
            # Also check specifically for fMRIPrep outputs
            for subject_dir in "$directory/derivatives/sub-"*; do
                if [ -d "$subject_dir" ]; then
                    echo "Ensuring subject directory is writable: $subject_dir"
                    chmod -R u+rw "$subject_dir" 2>/dev/null || \
                    sudo chmod -R u+rw "$subject_dir" 2>/dev/null || \
                    echo "Could not fix permissions for $subject_dir"
                fi
            done
        fi
    fi
    
    # Also check the main output directory
    local main_readonly_files=$(find "$directory" -maxdepth 1 -type f -not -writable 2>/dev/null | wc -l)
    
    if [ "$main_readonly_files" -gt 0 ]; then
        echo "Found $main_readonly_files files with read-only permissions in main directory. Fixing..."
        chmod -R u+rw "$directory" 2>/dev/null || \
        sudo chmod -R u+rw "$directory" 2>/dev/null || \
        echo "Could not fix permissions for main directory"
    else
        echo "Main directory permissions look good."
    fi
    
    echo "Permissions check and fixes completed."
}

# --- Process custom flags and extract them from arguments ---
# These variables will hold arguments that should be passed to the Python script
PYTHON_ARGS=()
FIX_PERMISSIONS=false
FORCE_EXECUTION=false

# Save the first two positional arguments (input and output directories)
if [ "$#" -lt 2 ]; then
    echo "Error: Missing required arguments."
    usage
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
shift 2 # Remove the first two arguments, leaving any extras for processing

# Parse arguments
FORCE_UNLOCK=false
FIX_PERMISSIONS=false
CORES=""
MEMORY=""
SKIP_FMRIPREP=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force_unlock)
            FORCE_UNLOCK=true
            shift
            ;;
        --fix_permissions)
            FIX_PERMISSIONS=true
            shift
            ;;
        --cores)
            CORES="$2"
            shift 2
            ;;
        --memory)
            MEMORY="$2"
            shift 2
            ;;
        --skip_fmriprep)
            SKIP_FMRIPREP=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            break
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

# Check and fix permissions of existing output files if they exist
check_and_unlock_existing_outputs "$OUTPUT_DIR"

# Build the pipeline command
PIPELINE_CMD="python $PIPELINE_SCRIPT $INPUT_DIR $OUTPUT_DIR"

# Add optional arguments if provided
if [ -n "$CORES" ]; then
    PIPELINE_CMD="$PIPELINE_CMD --cores $CORES"
fi

if [ -n "$MEMORY" ]; then
    PIPELINE_CMD="$PIPELINE_CMD --memory $MEMORY"
fi

if [ "$SKIP_FMRIPREP" = true ]; then
    PIPELINE_CMD="$PIPELINE_CMD --skip_fmriprep"
fi

# Add any remaining arguments
if [ $# -gt 2 ]; then
    REMAINING_ARGS=("${@:3}")
    for arg in "${REMAINING_ARGS[@]}"; do
        PIPELINE_CMD="$PIPELINE_CMD $arg"
    done
fi

echo "Executing: $PIPELINE_CMD"
echo ""

# Run the python script, passing through input/output dirs and any extra args
if ! $PIPELINE_CMD; then
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
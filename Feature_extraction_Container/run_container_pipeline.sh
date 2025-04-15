#!/bin/bash
# Script to simplify running the fMRI Feature Extraction Pipeline
# This script:
# 1. Checks if the Docker image exists, builds it if not
# 2. Takes an input folder with fMRI data
# 3. Takes specific features to extract and their parameters
# 4. Places outputs in a folder called "analytical_metrics" inside the input folder

set -e

# Default values
IMAGE_NAME="fmri-feature-extraction"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
INPUT_DIR=""
OUTPUT_DIR=""
FEATURES=()
CORES=""
FORCE=false
SUBJECT=""
PARAMS=()

# Function to display usage information
function usage() {
    echo "Usage: $0 --input <input_directory> [options]"
    echo ""
    echo "Options:"
    echo "  --input DIR         Input directory containing fMRI data in BIDS format (required)"
    echo "  --subject SUB-ID    Subject ID to process (default: all subjects in config)"
    echo "  --features LIST     Comma-separated list of features to extract"
    echo "                      Available: alff,falff,reho,hurst,fractal,qm_fft,rsn"
    echo "                      Default: all features"
    echo "  --cores N           Number of CPU cores to use (default: all cores)"
    echo "  --force             Force re-run of all rules (--forceall)"
    echo "  --param KEY=VALUE   Pass custom parameters to override config.yaml settings"
    echo "                      Can be specified multiple times"
    echo "  --help              Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 --input /data/fmri_dataset --features alff,reho --cores 4 --param alff_bandpass_low=0.01 --param alff_bandpass_high=0.1"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
        --input)
            INPUT_DIR="$2"
            shift
            shift
            ;;
        --subject)
            SUBJECT="$2"
            shift
            shift
            ;;
        --features)
            IFS=',' read -r -a FEATURES <<< "$2"
            shift
            shift
            ;;
        --cores)
            CORES="$2"
            shift
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --param)
            PARAMS+=("$2")
            shift
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if input directory is provided
if [[ -z "$INPUT_DIR" ]]; then
    echo "Error: Input directory is required."
    usage
    exit 1
fi

# Convert to absolute path if relative
if [[ ! "$INPUT_DIR" = /* ]]; then
    INPUT_DIR="$(pwd)/$INPUT_DIR"
fi

# Set output directory inside input directory
# OUTPUT_DIR="${INPUT_DIR}/analytical_metrics"

# Create output directory if it doesn't exist
# mkdir -p "$OUTPUT_DIR"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker image exists, build if not
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    echo "Docker image '$IMAGE_NAME' not found. Building now..."
    "$SCRIPT_DIR/run_container.sh" build
fi

# Generate temporary config file with custom parameters if provided
CONFIG_FILE=""
if [[ ${#PARAMS[@]} -gt 0 ]]; then
    CONFIG_FILE=$(mktemp)
    
    # Copy existing config
    cp "$SCRIPT_DIR/workflows/config/config.yaml" "$CONFIG_FILE"
    
    # Add custom parameters
    echo -e "\n# Custom parameters" >> "$CONFIG_FILE"
    for param in "${PARAMS[@]}"; do
        KEY="${param%%=*}"
        VALUE="${param#*=}"
        echo "$KEY: $VALUE" >> "$CONFIG_FILE"
    done
    
    # Create volume mount for custom config
    CONFIG_MOUNT="-v $CONFIG_FILE:/app/workflows/config/config.yaml"
else
    CONFIG_MOUNT="-v $SCRIPT_DIR/workflows/config:/app/workflows/config"
fi

# Build snakemake targets based on selected features
TARGETS=""

# Function to add a target for a specific feature
add_target() {
    local feature=$1
    local file_pattern=$2
    
    if [[ -z "$SUBJECT" ]]; then
        TARGETS+=" /data/output/*/func/Analytical_metrics/$feature/$file_pattern"
    else
        TARGETS+=" /data/output/$SUBJECT/func/Analytical_metrics/$feature/$file_pattern"
    fi
}

# Add targets for selected features
if [[ ${#FEATURES[@]} -eq 0 ]]; then
    # If no features specified, run all features
    if [[ -z "$SUBJECT" ]]; then
        TARGETS=""  # Empty targets means run the default "all" rule
    else
        # Add specific targets for the selected subject for all features
        add_target "ALFF" "${SUBJECT}_alff.nii.gz"
        add_target "ALFF" "${SUBJECT}_falff.nii.gz"
        add_target "ReHo" "${SUBJECT}_reho.nii.gz"
        add_target "Hurst" "${SUBJECT}_hurst.nii.gz"
        add_target "Fractal" "${SUBJECT}_fractal.nii.gz"
        add_target "QM_FFT" "${SUBJECT}_qm_fft.h5"
        add_target "RSN" "${SUBJECT}_rsn_activity.h5"
    fi
else
    # Add targets for specified features
    for feature in "${FEATURES[@]}"; do
        case $feature in
            alff)
                add_target "ALFF" "*_alff.nii.gz"
                ;;
            falff)
                add_target "ALFF" "*_falff.nii.gz"
                ;;
            reho)
                add_target "ReHo" "*_reho.nii.gz"
                ;;
            hurst)
                add_target "Hurst" "*_hurst.nii.gz"
                ;;
            fractal)
                add_target "Fractal" "*_fractal.nii.gz"
                ;;
            qm_fft)
                add_target "QM_FFT" "*_qm_fft.h5"
                ;;
            rsn)
                add_target "RSN" "*_rsn_activity.h5"
                ;;
            *)
                echo "Warning: Unknown feature '$feature' - skipping"
                ;;
        esac
    done
fi

# Set cores parameter
if [[ -n "$CORES" ]]; then
    CORES_ARG="--cores $CORES"
else
    CORES_ARG="--cores"
fi

# Set force flag if requested
if [[ "$FORCE" = true ]]; then
    FORCE_ARG="--forceall"
else
    FORCE_ARG=""
fi

echo "Starting fMRI Feature Extraction Pipeline..."
echo "Input directory: $INPUT_DIR"
# echo "Output directory: $OUTPUT_DIR" # This variable is no longer used here
echo "Features: ${FEATURES[*]:-all}"
echo "Subject: ${SUBJECT:-all subjects in config}"

# Build arguments for run_container.sh run
RUN_ARGS=(
    run
    -v "$INPUT_DIR:/data/input"
    # -v "$OUTPUT_DIR:/data/output" # This mount is intentionally removed
    -v "$SCRIPT_DIR/workflows:/app/workflows"
)
if [[ -n "$CONFIG_MOUNT" ]]; then
    # Add config mount if it exists (split string into array elements)
    read -r -a config_mount_array <<< "$CONFIG_MOUNT"
    RUN_ARGS+=("${config_mount_array[@]}")
fi
RUN_ARGS+=(
    snakemake
    --snakefile /app/workflows/Snakefile
    -d /app/workflows
)
if [[ -n "$CORES_ARG" ]]; then
    read -r -a cores_arg_array <<< "$CORES_ARG"
    RUN_ARGS+=("${cores_arg_array[@]}")
fi
if [[ -n "$FORCE_ARG" ]]; then
    RUN_ARGS+=("$FORCE_ARG")
fi
if [[ -n "$TARGETS" ]]; then
    # Add targets if they exist (handle potential spaces in target list)
    read -r -a target_array <<< "$TARGETS"
    RUN_ARGS+=("${target_array[@]}")
fi

# Execute the container
echo "Running command in container: ${RUN_ARGS[*]:1}" # Print command excluding 'run'
echo "With base volumes: -v $INPUT_DIR:/data/input -v $SCRIPT_DIR/workflows:/app/workflows $CONFIG_MOUNT"
"$SCRIPT_DIR/run_container.sh" "${RUN_ARGS[@]}"

# Cleanup temporary config file if it was created
if [[ -n "$CONFIG_FILE" && -f "$CONFIG_FILE" ]]; then
    rm -f "$CONFIG_FILE"
fi

echo "Pipeline completed successfully!"
# The following line is commented out as OUTPUT_DIR is no longer defined this way
# echo "Results are available in: $OUTPUT_DIR" 
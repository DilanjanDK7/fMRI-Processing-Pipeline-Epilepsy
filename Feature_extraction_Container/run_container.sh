#!/bin/bash
# Script to build and run the feature extraction container

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
IMAGE_NAME="fmri-feature-extraction"
CONTAINER_NAME="fmri-feature-container"

# Build the Docker image
build_image() {
    echo "Building Docker image: $IMAGE_NAME with args: $@..."
    docker build $@ -t $IMAGE_NAME -f $SCRIPT_DIR/docker/Dockerfile $SCRIPT_DIR
}

# Run container with test data
run_test() {
    if [ $# -eq 0 ]; then
        echo "Error: No test data provided. Please specify a sample fMRI file."
        echo "Usage: $0 test path/to/sample/data.nii.gz [--tr TR_VALUE]"
        exit 1
    fi
    
    SAMPLE_DATA="$1"
    shift
    EXTRA_ARGS="$@"
    
    echo "Running test with sample data: $SAMPLE_DATA"
    docker run --rm -it \
        -v "$SAMPLE_DATA:/data/sample.nii.gz" \
        -v "$SCRIPT_DIR/test_outputs:/test_outputs" \
        $IMAGE_NAME \
        python /app/scripts/test_features.py --sample-data /data/sample.nii.gz --output-dir /test_outputs $EXTRA_ARGS
}

# Run container with custom command
run_command() {
    local volume_args=()
    local cmd_args=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--volume)
                if [[ -z "$2" ]]; then
                    echo "Error: Missing argument for $1" >&2
                    exit 1
                fi
                volume_args+=("-v" "$2")
                shift 2
                ;;
            *)
                cmd_args+=("$1")
                shift
                ;;
        esac
    done

    # Use default volumes if none are provided
    if [ ${#volume_args[@]} -eq 0 ]; then
        volume_args=("-v" "$SCRIPT_DIR/data:/data" "-v" "$SCRIPT_DIR/outputs:/outputs")
    fi
    
    echo "Running command in container: ${cmd_args[@]}"
    echo "With volumes: ${volume_args[@]}"

    docker run --rm -it \
        "${volume_args[@]}" \
        "$IMAGE_NAME" \
        "${cmd_args[@]}"
}

# Print usage information
usage() {
    echo "Usage: $0 [command] [arguments]"
    echo ""
    echo "Commands:"
    echo "  build          Build the Docker image"
    echo "  test [file]    Run a test on the specified fMRI file"
    echo "  run [-v|--volume HOST_PATH:CONTAINER_PATH]... [cmd] Run a custom command in the container, optionally overriding default volume mounts."
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build                           # Build the Docker image"
    echo "  $0 test /path/to/sample.nii.gz     # Run test with sample data"
    echo "  $0 run python scripts/alff.py --help  # Run a specific command with default mounts"
    echo "  $0 run -v /my/data:/data -v /my/out:/outputs bash # Run bash with custom mounts"
}

# Main script logic
case "$1" in
    build)
        shift # Remove 'build' command itself
        build_image $@ # Pass remaining args to build_image
        ;;
    test)
        shift
        run_test $@
        ;;
    run)
        shift
        run_command $@
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        usage
        exit 1
        ;;
esac 
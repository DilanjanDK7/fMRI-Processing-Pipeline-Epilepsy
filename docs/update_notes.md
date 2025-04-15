# Pipeline Update Notes

## Command Structure Updates

### April 2025 Update

The command structure for the pipeline scripts has been modified to improve usability and command-line compatibility:

#### 1. Changed Parameter Structure

The main Python script `run_combined_pipeline.py` now accepts the input and output directories as positional arguments rather than named parameters. This change was implemented to ensure better compatibility with standard command-line conventions and simplify the command interface.

**Previous command structure:**
```bash
python run_combined_pipeline.py --input_dir "/path/to/input" --output_dir "/path/to/output" [OPTIONS]
```

**New command structure:**
```bash
python run_combined_pipeline.py "/path/to/input" "/path/to/output" [OPTIONS]
```

#### 2. Updated Shell Script

The shell wrapper script `run_pipeline.sh` has been updated to correctly pass positional arguments to the Python script:

**Previous implementation:**
```bash
PIPELINE_CMD="python $PIPELINE_SCRIPT --input_dir \"$INPUT_DIR\" --output_dir \"$OUTPUT_DIR\""
```

**New implementation:**
```bash
PIPELINE_CMD="python $PIPELINE_SCRIPT $INPUT_DIR $OUTPUT_DIR"
```

#### 3. Flag Consistency

For better command-line consistency, the flag to skip fMRIPrep has been standardized to use hyphens rather than underscores:

**Previous flag:** `--skip_fmriprep`
**New flag:** `--skip-fmriprep`

This change provides more consistent command syntax across the pipeline.

## Impact on Usage

This update **does not change** how end users interact with the pipeline. The main entry point remains `run_pipeline.sh` with the same argument structure:

```bash
./run_pipeline.sh /path/to/input_dir /path/to/output_dir [OPTIONS]
```

All existing documentation examples remain valid. Users only need to note the consistent use of hyphens in the `--skip-fmriprep` flag instead of underscores.

## Benefits of These Changes

1. **Improved compatibility** with standard command-line interfaces
2. **Simplified usage** with positional arguments for required parameters
3. **More consistent** flag naming convention 
4. **Better error handling** for input validation

## Implementation Details

The changes were made to:
1. `run_pipeline.sh` - Updated the command construction logic
2. Documentation - Updated all examples and descriptions to reflect the new flag format

The underlying Python script argument parser in `run_combined_pipeline.py` was already properly configured to handle both positional arguments and the flag with hyphens. 
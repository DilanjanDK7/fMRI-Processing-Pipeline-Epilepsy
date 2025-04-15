# Quick Reference Guide

This guide provides common commands and procedures for the fMRI Feature Extraction Container.

## Common Commands

### Simplified Pipeline Script

```bash
# Run all analyses for all subjects
./run_container_pipeline.sh --input /path/to/your/data

# Run specific features (ALFF and ReHo)
./run_container_pipeline.sh --input /path/to/your/data --features alff,reho

# Run for a specific subject with custom parameters
./run_container_pipeline.sh --input /path/to/your/data --subject sub-17017 --features qm_fft --param qm_fft_eps=1e-5

# Run with specific core count and force reprocessing
./run_container_pipeline.sh --input /path/to/your/data --cores 4 --force
```

### Building the Container

```bash
# Standard build
./run_container.sh build

# Clean build (no cache)
./run_container.sh build --no-cache
```

### Running the Pipeline

```bash
# Run entire pipeline on all subjects in config
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores

# Run with forced execution
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores --forceall

# Dry run (show what would be executed)
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows -n
```

### Specific Feature Analysis

```bash
# Run ALFF analysis only
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores /data/output/sub-17017/func/Analytical_metrics/ALFF/sub-17017_alff.nii.gz

# Run QM-FFT analysis only
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores /data/output/sub-17017/func/Analytical_metrics/QM_FFT/sub-17017_qm_fft.h5

# Run RSN analysis only
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --cores /data/output/sub-17017/func/Analytical_metrics/RSN/sub-17017_rsn_activity.h5
```

### Examining Outputs

```bash
# View HDF5 structure
./run_container.sh run -v $(pwd)/pipeline_outputs:/data/output h5ls -r /data/output/sub-17017/func/Analytical_metrics/QM_FFT/sub-17017_qm_fft.h5

# View NIfTI header
./run_container.sh run -v $(pwd)/pipeline_outputs:/data/output nib-ls /data/output/sub-17017/func/Analytical_metrics/ALFF/sub-17017_alff.nii.gz
```

### Troubleshooting

```bash
# Unlock a directory
./run_container.sh run -v /path/to/input/data:/data/input -v $(pwd)/pipeline_outputs:/data/output -v $(pwd)/workflows:/app/workflows snakemake --snakefile /app/workflows/Snakefile -d /app/workflows --unlock

# Clean up Docker
docker system prune -a

# Fix permissions
sudo chown -R $(id -u):$(id -g) ./pipeline_outputs
```

## Configuration Checklist

Before running the pipeline, ensure the following:

1. ☐ Input data is in correct BIDS format
2. ☐ Correct subjects are listed in config.yaml
3. ☐ Input and output paths are correctly specified
4. ☐ Sufficient disk space for outputs
5. ☐ Docker has enough memory allocated

## Common Workflows

### Full Pipeline for New Subject

1. Add subject ID to `workflows/config/config.yaml`
2. Ensure data is in correct location: `/path/to/input/data/sub-XXXX/func/...`
3. Run pipeline:
   ```bash
   ./run_container_pipeline.sh --input /path/to/input/data --subject sub-XXXX
   ```

### Test Run with Sampling

1. Ensure test subject is in config.yaml
2. Run single feature with 1 core:
   ```bash
   ./run_container_pipeline.sh --input /path/to/input/data --subject sub-XXXX --features qm_fft --cores 1
   ```

### Create Backup

```bash
tar -czf feature_extraction_backup_$(date +%Y-%m-%d_%H%M%S).tar.gz workflows scripts docker run_container.sh environment.yml README.md requirements.txt
```

## Feature Checklist

| Feature | Output File | Status |
|---------|-------------|--------|
| ALFF    | `sub-ID_alff.nii.gz` | ☐ |
| fALFF   | `sub-ID_falff.nii.gz` | ☐ |
| ReHo    | `sub-ID_reho.nii.gz` | ☐ |
| Hurst   | `sub-ID_hurst.nii.gz` | ☐ |
| Fractal | `sub-ID_fractal.nii.gz` | ☐ |
| QM-FFT  | `sub-ID_qm_fft.h5` | ☐ |
| RSN     | `sub-ID_rsn_activity.h5` | ☐ | 
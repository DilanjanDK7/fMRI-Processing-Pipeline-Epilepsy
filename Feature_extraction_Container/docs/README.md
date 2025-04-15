# fMRI Feature Extraction Documentation

Welcome to the documentation for the fMRI Feature Extraction Container. This documentation provides comprehensive information about setting up, configuring, and using the pipeline for extracting various analytical features from fMRI data.

## Documentation Index

### Core Documentation

- [**User Guide**](USER_GUIDE.md) - Comprehensive guide for setting up and using the pipeline
- [**Quick Reference**](QUICK_REFERENCE.md) - Common commands and procedures for everyday use

### Feature-Specific Documentation

- [**RSN Guide**](RSN_GUIDE.md) - Detailed information about Resting State Network analysis

### Analysis & Visualization

- [**Visualization Guide**](VISUALIZATION_GUIDE.md) - Instructions for visualizing and interpreting outputs

### Additional Resources

- [Main README](../README.md) - Overview and quick start information
- [Configuration Template](../workflows/config/config.yaml) - Reference for pipeline configuration

## Pipeline Overview

The fMRI Feature Extraction Container is designed to extract the following analytical metrics from resting-state fMRI data:

1. **Amplitude of Low-Frequency Fluctuation (ALFF/fALFF)** - Measures the strength of spontaneous brain activity
2. **Regional Homogeneity (ReHo)** - Measures local synchronization of brain activity
3. **Hurst Exponent** - Quantifies long-range temporal dependence
4. **Fractal Dimension** - Estimates complexity of time series
5. **Quantum Mechanical Fourier Transform (QM-FFT)** - Applies quantum principles to frequency analysis
6. **Resting State Network (RSN) Analysis** - Extracts time series from established brain networks

Each of these metrics provides unique insights into brain function, and they can be run individually or as part of a comprehensive analysis pipeline.

## Getting Started

### Prerequisites

Before using the pipeline, ensure you have:

- Docker installed on your system
- Sufficient system resources (8GB+ RAM recommended)
- fMRI data in BIDS-compatible format

### Installation

1. Clone the repository
2. Build the Docker container
3. Configure your analysis in `config.yaml`
4. Run the pipeline using the Snakemake commands

For detailed installation instructions, refer to the [User Guide](USER_GUIDE.md).

## Contributing

If you'd like to contribute to this documentation or the pipeline itself, please follow these steps:

1. Fork the repository
2. Create a new branch for your changes
3. Make your changes
4. Submit a pull request

## Contact

For questions or support, please contact [your.email@example.com]. 
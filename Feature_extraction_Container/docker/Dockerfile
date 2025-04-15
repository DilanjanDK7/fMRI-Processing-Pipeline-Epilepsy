FROM ubuntu:24.04

LABEL maintainer="Brain Lab <your.email@example.com>"
LABEL description="Container for fMRI feature extraction: ALFF, ReHo, Hurst, Fractal, QM-FFT"
LABEL version="1.0.0"

# Set frontend to noninteractive to avoid prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

# Install basic dependencies + wget/curl for Miniconda download
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    curl \
    bzip2 \
    git \
    tcsh \
    bash \
    libgsl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download and install Miniconda
ENV MINICONDA_VERSION=latest
ENV CONDA_DIR=/opt/conda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-${MINICONDA_VERSION}-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p ${CONDA_DIR} && \
    rm ~/miniconda.sh && \
    ${CONDA_DIR}/bin/conda init bash

# Set PATH to include conda bin
ENV PATH=${CONDA_DIR}/bin:${PATH}

# Make sure conda is available in subsequent RUN commands
SHELL ["/bin/bash", "-lc"]

# Update conda and set up environment before AFNI install
RUN conda update -n base -c defaults conda -y && \
    conda config --set auto_activate_base false

# Download and run official AFNI install scripts (Admin + User parts)
# Skipping c_nice part as it's for interactive terminals
# Ensure AFNI install scripts run with bash
RUN cd /tmp && \
    curl -O https://raw.githubusercontent.com/afni/afni/master/src/other_builds/OS_notes.linux_ubuntu_24_64_a_admin.txt && \
    curl -O https://raw.githubusercontent.com/afni/afni/master/src/other_builds/OS_notes.linux_ubuntu_24_64_b_user.tcsh && \
    # Run admin script (installs dependencies via apt)
    bash OS_notes.linux_ubuntu_24_64_a_admin.txt && \
    # Run user script (installs AFNI binaries via @update.afni.binaries to /root/abin)
    # The -no_recur prevents it from downloading itself again inside the container
    # It might try to edit dotfiles, which is ok but less relevant here.
    # Create .cshrc first as the script might expect it
    touch /root/.cshrc && \
    tcsh OS_notes.linux_ubuntu_24_64_b_user.tcsh -no_recur && \
    # Cleanup scripts
    rm -f OS_notes.linux_ubuntu_24_64_a_admin.txt OS_notes.linux_ubuntu_24_64_b_user.tcsh

# Set working directory
WORKDIR /app

# Copy environment and requirements files
COPY environment.yml .
COPY requirements.txt .

# Create conda environment from file
# Activate conda for this RUN instruction
RUN conda env create -f environment.yml && \
    conda clean -afy

# Install pip packages into the environment
# Activate conda env for this RUN instruction
RUN echo "source activate feature_extraction" > ~/.bashrc && \
    pip install -r requirements.txt

# Clone QM_FFT_Feature_Package from GitHub into /app
RUN git clone https://github.com/DilanjanDK7/QM_FFT_Feature_Package.git /app/QM_FFT_Feature_Package

# Add conda environment AND AFNI bin to path for ENTRYPOINT/CMD
# Note: AFNI install script puts binaries in /root/abin
ENV PATH=/opt/conda/envs/feature_extraction/bin:/root/abin:${PATH}

# Reset shell to default for ENTRYPOINT/CMD
SHELL ["/bin/bash", "-c"]

# Copy code
COPY scripts /app/scripts
COPY workflows /app/workflows

# Make scripts executable
RUN chmod +x /app/scripts/*.py

# Set entrypoint to run commands within the conda environment
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "feature_extraction"]

# Default command
CMD ["python", "-c", "import sys; print('Feature Extraction Container Ready!'); print(f'Python version: {sys.version}')"] 
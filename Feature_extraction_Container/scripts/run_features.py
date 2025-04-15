#!/usr/bin/env python3
import argparse
import os
import time
from pathlib import Path

from alff import compute_alff
from reho import compute_reho
from hurst import compute_hurst
from fractal import compute_fractal
from qm_fft import compute_qm_fft

def run_all_features(input_file, output_dir, tr=2.0, mask_file=None, 
                    reho_cluster_size=27, alff_low=0.01, alff_high=0.08,
                    hurst_method='dfa', fractal_method='higuchi', fractal_kmax=10,
                    qm_fft_eps=1e-6, qm_fft_radius=0.6, qm_fft_local_k=5):
    """
    Run all feature extraction methods on the input fMRI file.
    
    Parameters:
    -----------
    input_file : str
        Path to the input fMRI file.
    output_dir : str
        Directory to save output files.
    tr : float, optional
        Repetition time of the fMRI data in seconds. Default is 2.0.
    mask_file : str, optional
        Path to binary mask file. If None, a mask will be created from the fMRI data.
    reho_cluster_size : int, optional
        Size of the cluster for ReHo KCC calculation. Default is 27.
    alff_low : float, optional
        Lower bound of bandpass filter (Hz) for ALFF. Default is 0.01.
    alff_high : float, optional
        Upper bound of bandpass filter (Hz) for ALFF. Default is 0.08.
    hurst_method : str, optional
        Method for Hurst exponent calculation ('dfa' or 'rs'). Default is 'dfa'.
    fractal_method : str, optional
        Method for fractal dimension calculation ('higuchi' or 'psd'). Default is 'higuchi'.
    fractal_kmax : int, optional
        Maximum lag parameter for Higuchi method. Default is 10.
    qm_fft_eps : float, optional
        FINUFFT precision for QM-FFT. Default is 1e-6.
    qm_fft_radius : float, optional
        K-space mask radius for QM-FFT. Default is 0.6.
    qm_fft_local_k : int, optional
        Number of neighbors for local variance in QM-FFT. Default is 5.
    """
    start_time = time.time()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract base filename without extension
    base_name = Path(input_file).stem
    if base_name.endswith('.nii'):
        base_name = Path(base_name).stem
    
    # Extract subject ID
    subject_id = base_name.split('_')[0]
    
    # Setup output paths
    reho_output = os.path.join(output_dir, f"{base_name}_reho.nii.gz")
    alff_output = os.path.join(output_dir, f"{base_name}_alff.nii.gz")
    hurst_output = os.path.join(output_dir, f"{base_name}_hurst.nii.gz")
    fractal_output = os.path.join(output_dir, f"{base_name}_fractal.nii.gz")
    qm_fft_output = os.path.join(output_dir, f"{base_name}_qm_fft.h5")
    
    print(f"=== Running feature extraction on {input_file} ===")
    
    # Run ReHo
    print("\n=== Running ReHo ===")
    compute_reho(
        input_file, 
        reho_output, 
        cluster_size=reho_cluster_size, 
        mask_file=mask_file
    )
    
    # Run ALFF
    print("\n=== Running ALFF ===")
    compute_alff(
        input_file,
        alff_output,
        tr=tr,
        bandpass_low=alff_low,
        bandpass_high=alff_high,
        mask_file=mask_file
    )
    
    # Run Hurst exponent
    print("\n=== Running Hurst exponent calculation ===")
    compute_hurst(
        input_file,
        hurst_output,
        method=hurst_method,
        mask_file=mask_file
    )
    
    # Run Fractal dimension
    print("\n=== Running Fractal dimension calculation ===")
    compute_fractal(
        input_file,
        fractal_output,
        method=fractal_method,
        kmax=fractal_kmax,
        mask_file=mask_file
    )
    
    # Run QM-FFT
    print("\n=== Running QM-FFT analysis ===")
    compute_qm_fft(
        input_file,
        qm_fft_output,
        mask_file=mask_file,
        subject_id=subject_id,
        eps=qm_fft_eps,
        radius=qm_fft_radius,
        local_k=qm_fft_local_k
    )
    
    # Summary
    elapsed_time = time.time() - start_time
    print(f"\n=== All features extracted successfully in {elapsed_time:.2f} seconds ===")
    print(f"ReHo output: {reho_output}")
    print(f"ALFF output: {alff_output}")
    print(f"Hurst output: {hurst_output}")
    print(f"Fractal output: {fractal_output}")
    print(f"QM-FFT output: {qm_fft_output}")
    
    return {
        'reho': reho_output,
        'alff': alff_output,
        'hurst': hurst_output,
        'fractal': fractal_output,
        'qm_fft': qm_fft_output
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract multiple features from fMRI data')
    parser.add_argument('--input', required=True, help='Path to input fMRI file')
    parser.add_argument('--output-dir', required=True, help='Directory to save output files')
    parser.add_argument('--tr', type=float, default=2.0, help='Repetition time in seconds (default: 2.0)')
    parser.add_argument('--mask', help='Path to mask file (optional)')
    
    # ReHo parameters
    parser.add_argument('--reho-cluster-size', type=int, default=27, choices=[7, 19, 27],
                      help='Cluster size for ReHo (7, 19, or 27; default: 27)')
    
    # ALFF parameters
    parser.add_argument('--alff-low', type=float, default=0.01, help='Lower bound of bandpass filter in Hz (default: 0.01)')
    parser.add_argument('--alff-high', type=float, default=0.08, help='Upper bound of bandpass filter in Hz (default: 0.08)')
    
    # Hurst parameters
    parser.add_argument('--hurst-method', choices=['dfa', 'rs'], default='dfa',
                      help='Method for Hurst calculation (dfa or rs; default: dfa)')
    
    # Fractal parameters
    parser.add_argument('--fractal-method', choices=['higuchi', 'psd'], default='higuchi',
                      help='Method for fractal dimension calculation (higuchi or psd; default: higuchi)')
    parser.add_argument('--fractal-kmax', type=int, default=10,
                      help='Maximum lag for Higuchi method (default: 10)')
    
    # QM-FFT parameters
    parser.add_argument('--qm-fft-eps', type=float, default=1e-6,
                      help='FINUFFT precision for QM-FFT (default: 1e-6)')
    parser.add_argument('--qm-fft-radius', type=float, default=0.6,
                      help='K-space mask radius for QM-FFT (default: 0.6)')
    parser.add_argument('--qm-fft-local-k', type=int, default=5,
                      help='Number of neighbors for local variance in QM-FFT (default: 5)')
    
    args = parser.parse_args()
    
    run_all_features(
        args.input,
        args.output_dir,
        tr=args.tr,
        mask_file=args.mask,
        reho_cluster_size=args.reho_cluster_size,
        alff_low=args.alff_low,
        alff_high=args.alff_high,
        hurst_method=args.hurst_method,
        fractal_method=args.fractal_method,
        fractal_kmax=args.fractal_kmax,
        qm_fft_eps=args.qm_fft_eps,
        qm_fft_radius=args.qm_fft_radius,
        qm_fft_local_k=args.qm_fft_local_k
    ) 
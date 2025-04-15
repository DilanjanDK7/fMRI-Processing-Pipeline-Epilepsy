#!/usr/bin/env python3
"""
Test script to run feature extraction on sample data.
"""

import os
import argparse
from pathlib import Path
from run_features import run_all_features

def main():
    parser = argparse.ArgumentParser(description='Test feature extraction on sample data')
    parser.add_argument('--sample-data', required=True, help='Path to sample fMRI data (NIFTI format)')
    parser.add_argument('--output-dir', default='test_outputs', help='Directory to save outputs (default: test_outputs)')
    parser.add_argument('--tr', type=float, default=2.0, help='Repetition time in seconds (default: 2.0)')
    parser.add_argument('--mask', help='Optional path to brain mask file')
    
    # ReHo parameters
    parser.add_argument('--reho-cluster-size', type=int, default=27, choices=[7, 19, 27],
                      help='Cluster size for ReHo (7, 19, or 27; default: 27)')
    
    # ALFF parameters
    parser.add_argument('--alff-low', type=float, default=0.01, help='Lower bound of bandpass filter in Hz (default: 0.01)')
    parser.add_argument('--alff-high', type=float, default=0.08, help='Upper bound of bandpass filter in Hz (default: 0.08)')
    
    # Feature selection
    parser.add_argument('--run-reho', action='store_true', help='Run ReHo calculation')
    parser.add_argument('--run-alff', action='store_true', help='Run ALFF calculation')
    parser.add_argument('--run-hurst', action='store_true', help='Run Hurst exponent calculation')
    parser.add_argument('--run-fractal', action='store_true', help='Run fractal dimension calculation')
    parser.add_argument('--run-qm-fft', action='store_true', help='Run QM-FFT analysis')
    parser.add_argument('--run-all', action='store_true', help='Run all feature extraction methods')
    
    args = parser.parse_args()
    
    # If no specific features are selected, run them all
    run_all = args.run_all or not (args.run_reho or args.run_alff or args.run_hurst or args.run_fractal or args.run_qm_fft)
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"=== Testing Feature Extraction Container ===")
    print(f"Sample data: {args.sample_data}")
    print(f"Output directory: {args.output_dir}")
    print(f"TR: {args.tr} seconds")
    print(f"Mask: {args.mask if args.mask else 'Not provided (will be generated)'}")
    
    if run_all:
        print("Running all features")
        # Run the feature extraction
        results = run_all_features(
            args.sample_data,
            args.output_dir,
            tr=args.tr,
            mask_file=args.mask,
            reho_cluster_size=args.reho_cluster_size,
            alff_low=args.alff_low,
            alff_high=args.alff_high
        )
    else:
        # Extract base filename without extension
        base_name = Path(args.sample_data).stem
        if base_name.endswith('.nii'):
            base_name = Path(base_name).stem
        
        results = {}
        
        if args.run_reho:
            from reho import compute_reho
            print("\n=== Running ReHo ===")
            reho_output = os.path.join(args.output_dir, f"{base_name}_reho.nii.gz")
            compute_reho(
                args.sample_data, 
                reho_output, 
                cluster_size=args.reho_cluster_size, 
                mask_file=args.mask
            )
            results['reho'] = reho_output
            
        if args.run_alff:
            from alff import compute_alff
            print("\n=== Running ALFF ===")
            alff_output = os.path.join(args.output_dir, f"{base_name}_alff.nii.gz")
            compute_alff(
                args.sample_data,
                alff_output,
                tr=args.tr,
                bandpass_low=args.alff_low,
                bandpass_high=args.alff_high,
                mask_file=args.mask
            )
            results['alff'] = alff_output
            
        if args.run_hurst:
            from hurst import compute_hurst
            print("\n=== Running Hurst exponent calculation ===")
            hurst_output = os.path.join(args.output_dir, f"{base_name}_hurst.nii.gz")
            compute_hurst(
                args.sample_data,
                hurst_output,
                mask_file=args.mask
            )
            results['hurst'] = hurst_output
            
        if args.run_fractal:
            from fractal import compute_fractal
            print("\n=== Running Fractal dimension calculation ===")
            fractal_output = os.path.join(args.output_dir, f"{base_name}_fractal.nii.gz")
            compute_fractal(
                args.sample_data,
                fractal_output,
                mask_file=args.mask
            )
            results['fractal'] = fractal_output
            
        if args.run_qm_fft:
            from qm_fft import compute_qm_fft
            print("\n=== Running QM-FFT analysis ===")
            qm_fft_output = os.path.join(args.output_dir, f"{base_name}_qm_fft.h5")
            compute_qm_fft(
                args.sample_data,
                qm_fft_output,
                mask_file=args.mask
            )
            results['qm_fft'] = qm_fft_output
    
    print("\n=== Test Complete ===")
    print("Outputs:")
    for feature, output_file in results.items():
        print(f"- {feature.upper()}: {output_file}")

if __name__ == '__main__':
    main() 
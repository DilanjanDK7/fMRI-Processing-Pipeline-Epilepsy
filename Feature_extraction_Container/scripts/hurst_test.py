#!/usr/bin/env python3
import argparse
import nibabel as nib
from hurst_dfa import hurst_roi_map

def main():
    parser = argparse.ArgumentParser(
        description='Compute ROI‐wise Hurst exponent via DFA'
    )
    parser.add_argument('--fmri',    required=True,
                        help='Path to 4D BOLD NIfTI')
    parser.add_argument('--atlas',   required=True,
                        help='Atlas NIfTI for ROI labels or maps')
    parser.add_argument('--output',  required=True,
                        help='Path to save Hurst NIfTI')
    parser.add_argument('--maps',    action='store_true',
                        help='Use NiftiMapsMasker instead of LabelsMasker')
    parser.add_argument('--n-jobs',  type=int, default=8,
                        help='Number of parallel jobs')
    parser.add_argument('--min-var', type=float, default=1e-6,
                        help='Minimum time‐series variance threshold')
    args = parser.parse_args()

    out_img = hurst_roi_map(
        fmri_img=args.fmri,
        atlas_img=args.atlas,
        use_maps_masker=args.maps,
        n_jobs=args.n_jobs,
        min_var=args.min_var
    )
    nib.save(out_img, args.output)
    print(f"[+] Saved Hurst map to {args.output}")

if __name__ == '__main__':
    main()

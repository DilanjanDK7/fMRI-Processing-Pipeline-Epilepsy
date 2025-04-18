#!/usr/bin/env python3
import argparse
import nibabel as nib
from fractal_nolds import fractal_roi_map

def main():
    parser = argparse.ArgumentParser(
        description='Compute ROI‐wise fractal dimension'
    )
    parser.add_argument('--fmri',    required=True,
                        help='Path to 4D BOLD NIfTI')
    parser.add_argument('--atlas',   required=True,
                        help='Atlas NIfTI for ROI labels or maps')
    parser.add_argument('--output',  required=True,
                        help='Path to save FD NIfTI')
    parser.add_argument('--maps',    action='store_true',
                        help='Use NiftiMapsMasker instead of LabelsMasker')
    parser.add_argument('--method',  choices=['hfd','katz'], default='hfd',
                        help='Fractal algorithm')
    parser.add_argument('--kmax',    type=int, default=64,
                        help='HFD kmax parameter')
    parser.add_argument('--n-jobs',  type=int, default=8,
                        help='Number of parallel jobs')
    parser.add_argument('--min-var', type=float, default=1e-6,
                        help='Minimum time‐series variance threshold')
    args = parser.parse_args()

    out_img = fractal_roi_map(
        fmri_img=args.fmri,
        atlas_img=args.atlas,
        use_maps_masker=args.maps,
        fd_method=args.method,
        kmax=args.kmax,
        n_jobs=args.n_jobs,
        min_var=args.min_var
    )
    nib.save(out_img, args.output)
    print(f"[+] Saved FD map ({args.method}) to {args.output}")

if __name__ == '__main__':
    main()

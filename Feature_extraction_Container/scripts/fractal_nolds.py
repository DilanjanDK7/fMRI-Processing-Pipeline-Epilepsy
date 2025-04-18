#!/usr/bin/env python3
import numpy as np
import nibabel as nib
from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker
import nolds
from joblib import Parallel, delayed

def compute_fd(ts, method='hfd', kmax=64):
    """Return Higuchi or Katz fractal dimension."""
    if method == 'hfd':
        return nolds.hfd(ts, kmax=kmax)
    elif method == 'katz':
        return nolds.katz_fd(ts)
    else:
        raise ValueError("method must be 'hfd' or 'katz'")

def fractal_roi_map(fmri_img, atlas_img, use_maps_masker=False,
                   fd_method='hfd', kmax=64, n_jobs=8, min_var=1e-6):
    """
    Compute ROI‐wise fractal dimension and return a Nifti1Image.
    
    Parameters
    ----------
    fmri_img : str
        Path to 4D BOLD NIfTI file.
    atlas_img : str
        Path to atlas labels/maps NIfTI.
    use_maps_masker : bool
        If True use NiftiMapsMasker, else NiftiLabelsMasker.
    fd_method : {'hfd','katz'}
        Fractal algorithm.
    kmax : int
        K‐max parameter for HFD.
    n_jobs : int
        Number of parallel jobs.
    min_var : float
        Minimum time‐series variance threshold.
    """
    # 1) Initialize masker
    if use_maps_masker:
        masker = NiftiMapsMasker(maps_img=atlas_img, standardize=True)
    else:
        masker = NiftiLabelsMasker(labels_img=atlas_img, standardize=True)

    # 2) Extract ROI time‐series
    ts_data = masker.fit_transform(fmri_img)
    _, n_rois = ts_data.shape

    # 3) Parallel FD computation
    def _process(i):
        ts = ts_data[:, i]
        if np.var(ts) < min_var:
            return np.nan
        return compute_fd(ts, method=fd_method, kmax=kmax)

    fd_vals = Parallel(n_jobs=n_jobs)(
        delayed(_process)(i) for i in range(n_rois)
    )

    # 4) Build 3D ROI map
    atlas = nib.load(atlas_img)
    atlas_data = atlas.get_fdata()
    fd_map = np.zeros_like(atlas_data, dtype=np.float32)

    labels = np.unique(atlas_data)
    if not use_maps_masker:
        labels = labels[labels != 0]

    for idx, lab in enumerate(labels):
        fd_map[atlas_data == lab] = fd_vals[idx]

    # 5) Return Nifti1Image
    return nib.Nifti1Image(fd_map, affine=atlas.affine, header=atlas.header)

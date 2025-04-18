#!/usr/bin/env python3
import numpy as np
import nibabel as nib
from nilearn.input_data import NiftiLabelsMasker, NiftiMapsMasker
import nolds
from joblib import Parallel, delayed

def compute_hurst_dfa(ts, nvals=(4,8,16,32,64)):
    """DFA‐based Hurst exponent via nolds."""
    return nolds.dfa(ts, overlap=True, nvals=nvals)

def hurst_roi_map(fmri_img, atlas_img, use_maps_masker=False,
                  n_jobs=8, min_var=1e-6):
    """
    Compute ROI‐wise Hurst exponent and return a Nifti1Image.
    
    Parameters
    ----------
    fmri_img : str
        Path to 4D BOLD NIfTI file.
    atlas_img : str
        Path to atlas labels/maps NIfTI.
    use_maps_masker : bool
        If True use NiftiMapsMasker, else NiftiLabelsMasker.
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

    # 2) Extract ROI time‐series: shape (T, R)
    ts_data = masker.fit_transform(fmri_img)
    _, n_rois = ts_data.shape

    # 3) Parallel Hurst computation
    def _process(i):
        ts = ts_data[:, i]
        if np.var(ts) < min_var:
            return np.nan
        try:
            return compute_hurst_dfa(ts)
        except Exception:
            return np.nan

    hurst_vals = Parallel(n_jobs=n_jobs)(
        delayed(_process)(i) for i in range(n_rois)
    )

    # 4) Load atlas and build ROI‐map
    atlas = nib.load(atlas_img)
    atlas_data = atlas.get_fdata()
    roi_map = np.zeros_like(atlas_data, dtype=np.float32)

    labels = np.unique(atlas_data)
    if not use_maps_masker:
        labels = labels[labels != 0]

    for idx, lab in enumerate(labels):
        roi_map[atlas_data == lab] = hurst_vals[idx]

    # 5) Return Nifti1Image
    return nib.Nifti1Image(roi_map, affine=atlas.affine, header=atlas.header)

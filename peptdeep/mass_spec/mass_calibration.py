# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/mass_spec/mass_calibration.ipynb (unless otherwise specified).

__all__ = ['get_fragment_median', 'calibrate_one', 'MassCalibratorForRT_KNN']

# Cell
from sklearn.neighbors import KNeighborsRegressor
import pandas as pd
import numpy as np

def get_fragment_median(start_end_idxes, frag_df:pd.DataFrame):
    start_idx, end_idx = start_end_idxes
    return np.nanmedian(frag_df.values[start_idx:end_idx])

def calibrate_one(start_end_shift, frag_df):
    start_idx, end_idx, mass_shift = start_end_shift
    frag_df.values[int(start_idx):int(end_idx)] -= mass_shift

class MassCalibratorForRT_KNN:
    def __init__(self, n_neighbors=5):
        self._n_neighbors = n_neighbors
        self.model = KNeighborsRegressor(n_neighbors)

    def fit(self, psm_df:pd.DataFrame, mass_error_df:pd.DataFrame):
        mass_error_df = mass_error_df.replace(np.inf, np.nan)
        mean_merrs = psm_df[['frag_start_idx','frag_end_idx']].apply(
            get_fragment_median, axis=1, frag_df=mass_error_df
        ).values
        self.model.fit(psm_df.rt.values.reshape((-1,1)), mean_merrs.reshape(-1,1))

    def calibrate(self,
        psm_df:pd.DataFrame, mass_error_df:pd.DataFrame
    )->pd.DataFrame:
        psm_df['frag_mass_shift'] = self.model.predict(
            psm_df.rt.values.reshape((-1,1))
        ).reshape(-1)
        psm_df[['frag_start_idx','frag_end_idx','frag_mass_shift']].apply(
            calibrate_one, axis=1, frag_df=mass_error_df
        ).values
        return mass_error_df
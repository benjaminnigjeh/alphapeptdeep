# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/spec_lib/predict_lib.ipynb (unless otherwise specified).

__all__ = ['PredictSpecLib']

# Cell
import pandas as pd
import numpy as np
import torch
from peptdeep.utils import logging

from alphabase.spectrum_library.library_base import SpecLibBase
from peptdeep.pretrained_models import ModelManager
from peptdeep.model.rt import convert_predicted_rt_to_irt

class PredictSpecLib(SpecLibBase):
    def __init__(self,
        model_manager: ModelManager,
        charged_frag_types = ['b_z1','b_z2','y_z1','y_z2'],#['b_modloss_z1', ...]
        min_precursor_mz = 400, max_precursor_mz = 2000,
        decoy:str = 'pseudo_reverse'
    ):
        super().__init__(
            charged_frag_types,
            min_precursor_mz=min_precursor_mz,
            max_precursor_mz=max_precursor_mz,
            decoy = decoy
        )
        self.model_manager = model_manager

        self.intensity_factor = 1

        self._precursor_df = pd.DataFrame()
        self._fragment_intensity_df = pd.DataFrame()
        self._fragment_mz_df = pd.DataFrame()

    def set_precursor_and_fragment(self,
        *,
        precursor_df: pd.DataFrame,
        fragment_mz_df: pd.DataFrame,
        fragment_intensity_df: pd.DataFrame,
    ):
        self._precursor_df = precursor_df
        self._fragment_intensity_df = fragment_intensity_df
        self._fragment_mz_df = fragment_mz_df

        self._fragment_mz_df.drop(columns=[
            col for col in self._fragment_mz_df.columns
            if col not in self.charged_frag_types
        ], inplace=True)

        self._fragment_intensity_df.drop(columns=[
            col for col in self._fragment_intensity_df.columns
            if col not in self.charged_frag_types
        ], inplace=True)

    def rt_to_irt_pred(self):
        """ Add 'irt_pred' into columns based on 'rt_pred' """
        return convert_predicted_rt_to_irt(
            self._precursor_df, self.model_manager.rt_model
        )

    def predict_all(self):
        """ Add 'rt_pred' into columns """
        logging.info('predicting RT/IM/MS2 ...')
        res = self.model_manager.predict_all(
            self._precursor_df,
            predict_items=['rt','mobility','ms2'],
        )
        self.set_precursor_and_fragment(**res)
        logging.info('End Predicting RT/IM/MS2')

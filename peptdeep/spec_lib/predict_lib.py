# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/spec_lib/predict_lib.ipynb (unless otherwise specified).

__all__ = ['PredictSpecLib', 'lib_settings']

# Cell
import pandas as pd
import numpy as np
import torch
from peptdeep.utils import logging

from alphabase.peptide.precursor import (
    calc_precursor_isotope_mp, calc_precursor_isotope
)
from peptdeep.utils import process_bar
from alphabase.spectral_library.library_base import SpecLibBase
from peptdeep.pretrained_models import ModelManager
from peptdeep.settings import global_settings

lib_settings = global_settings['library']

class PredictSpecLib(SpecLibBase):
    def __init__(self,
        model_manager: ModelManager = None,
        charged_frag_types = ['b_z1','b_z2','y_z1','y_z2'],#['b_modloss_z1', ...]
        precursor_mz_min = 400, precursor_mz_max = 2000,
        decoy:str = 'pseudo_reverse'
    ):
        super().__init__(
            charged_frag_types,
            precursor_mz_min=precursor_mz_min,
            precursor_mz_max=precursor_mz_max,
            decoy = decoy
        )
        if model_manager is None:
            self.model_manager = ModelManager(
                mask_modloss=False
            )
        else:
            self.model_manager = model_manager

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
        return self.model_manager.rt_model.add_irt_column_to_precursor_df(self._precursor_df)

    def predict_all(self,
        min_required_precursor_num_for_mp:int=2000
    ):
        """
        1. Predict RT/IM/MS2 for self._precursor_df
        2. Calculate isotope information in self._precursor_df
        """
        logging.info('Calculating precursor isotope distributions ...')
        self.calc_precursor_mz()
        if len(self.precursor_df) < min_required_precursor_num_for_mp:
            self._precursor_df = calc_precursor_isotope(
                self._precursor_df
            )
        else:
            self._precursor_df = calc_precursor_isotope_mp(
                self._precursor_df, process_bar=process_bar
            )
        logging.info('Predicting RT/IM/MS2 ...')
        res = self.model_manager.predict_all(
            self._precursor_df,
            predict_items=['rt','mobility','ms2'],
            frag_types=self.charged_frag_types,
        )
        self.set_precursor_and_fragment(**res)
        logging.info('End Predicting RT/IM/MS2')

# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/reader/psm_reader.ipynb (unless otherwise specified).

__all__ = ['translate_other_modification', 'keep_modifications', 'PSMReaderBase']

# Cell
import typing
import pandas as pd

from alphabase.peptide.fragment import get_charged_frag_types

def translate_other_modification(mod_str: str, mod_dict: dict):
    if not mod_str: return ""
    ret_mods = []
    for mod in mod_str.split(';'):
        if mod in mod_dict:
            ret_mods.append(mod_dict[mod])
        else:
            return pd.NA
    return ";".join(ret_mods)

def keep_modifications(mod_str: str, mod_set):
    if not mod_str: return ""
    for mod in mod_str.split(';'):
        if not mod in mod_set:
            return pd.NA
    return mod_str


class PSMReaderBase(object):
    def __init__(self,
        frag_types=['b','y','b-modloss','y-modloss'],
        max_frag_charge=2
    ):
        self.modification_convert_dict = {}
        self.charged_ion_types = get_charged_frag_types(
            frag_types, max_frag_charge
        )

    @property
    def psm_df(self):
        return self._psm_df

    @property
    def fragment_inten_df(self):
        return self._fragment_inten_df

    def translate_modification(self):
        '''
            Raise: KeyError if `mod` in `mod_names` is not in `self.modification_convert_dict`
        '''
        self._psm_df.mods = self._psm_df.mods.apply(
            translate_other_modification,
            mod_dict=self.modification_convert_dict
        )

        self._psm_df.dropna(
            subset=['mods'], inplace=True
        )
        self._psm_df.reset_index(drop=True, inplace=True)

    def filter_psm_by_modifications(self, include_mod_list = [
        'Oxidation@M','Phospho@S','Phospho@T','Phospho@Y','Acetyl@Protein N-term'
    ]):
        mod_set = set(include_mod_list)
        self._psm_df.mods = self._psm_df.mods.apply(keep_modifications, mod_set=mod_set)

        self._psm_df.dropna(
            subset=['mods'], inplace=True
        )
        self._psm_df.reset_index(drop=True, inplace=True)

    def load(self, filename):
        self._load_file(filename)
        self.translate_modification()

    def _load_file(self, filename):
        raise NotImplementedError(
            f'Sub-class of "{self.__class__}" must re-implement "_load_file()"'
        )

    def load_fragment_inten_df(self,
        ms_files=None
    ):
        raise NotImplementedError(
            f'Sub-class of "{self.__class__}" must re-implement "load_fragment_inten_df()"'
        )
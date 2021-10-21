# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/reader/spectronaut_reader.ipynb (unless otherwise specified).

__all__ = ['SpectronautReader']

# Cell
import pandas as pd
import numpy as np

from alphadeep.reader.psm_reader import \
    psm_reader_provider

from alphadeep.reader.maxquant_reader import parse_mq, \
    MaxQuantReader

class SpectronautReader(MaxQuantReader):
    def __init__(self):
        super().__init__(None)
        self.mod_sep = '[]'

    def _load_file(self, filename):
        df = pd.read_csv(filename, sep='\t')
        df.drop_duplicates([
            'ReferenceRun','ModifiedPeptide', 'PrecursorCharge'
        ], inplace=True)
        df.reset_index(drop=True, inplace=True)
        psm_df = pd.DataFrame()
        psm_df['sequence'] = df['StrippedPeptide']
        df['nAA'] = df['StrippedPeptide'].str.len() # place holder for future
        psm_df['nAA'] = df['nAA']
        psm_df['mods'], psm_df['mod_sites'] = zip(
            *df['ModifiedPeptide'].apply(
                parse_mq, mod_sep=self.mod_sep
            )
        )
        psm_df['charge'] = df['PrecursorCharge']

        psm_df['RT'] = df['iRT']
        min_rt = psm_df.RT.min()
        psm_df.RT = (
            psm_df.RT - min_rt
        )/(psm_df.RT.max() - min_rt)

        if 'K0' in df.columns:
            psm_df['mobility'] = 1/df['K0']
        elif 'IonMobility' in df.columns:
            psm_df['mobility'] = df['IonMobility']
        else:
            psm_df['mobility'] = pd.NA

        if 'CCS' in df.columns:
            psm_df['CCS'] = df['CCS']
        else:
            psm_df['CCS'] = pd.NA

        psm_df['proteins'] = df['Protein Name']
        if 'Genes' in df.columns:
            psm_df['genes'] = df['Genes']
        else:
            psm_df['genes'] = ''
        self._psm_df = psm_df

psm_reader_provider.register_reader(
    'spectronaut', SpectronautReader
)
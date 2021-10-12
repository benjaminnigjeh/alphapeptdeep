# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/model/msms.ipynb (unless otherwise specified).

__all__ = ['ModelMSMSpDeep3', 'IntenAwareLoss', 'pDeepModel', 'mod_feature_size', 'max_instrument_num', 'frag_types',
           'max_frag_charge', 'num_ion_types', 'nce_factor', 'charge_factor', 'pearson', 'spectral_angle', 'spearman',
           'evaluate_msms', 'add_cutoff_metric']

# Cell
import torch
import pandas as pd
import numpy as np

from typing import List, Tuple

from tqdm import tqdm

from alphabase.peptide.fragment import \
    init_fragment_by_precursor_dataframe, \
    set_sliced_fragment_dataframe, \
    get_sliced_fragment_dataframe, \
    get_charged_frag_types

from alphadeep.model.featurize import \
    parse_aa_indices, parse_instrument_indices, \
    get_batch_mod_feature

from alphadeep._settings import \
    global_settings as settings, \
    model_const

import alphadeep.model.base as model_base

class ModelMSMSpDeep3(torch.nn.Module):
    def __init__(self,
        mod_feature_size,
        num_ion_types,
        max_instrument_num,
        dropout=0.2
    ):
        super().__init__()
        BiRNN = True
        self.aa_embedding_size = 27
        hidden=model_const['hidden']
        ins_nce_embed_size=3
        hidden_rnn_layer=2

        self.max_instrument_num = max_instrument_num
        self.instrument_nce_embed = torch.nn.Linear(max_instrument_num+1,ins_nce_embed_size)
        # ins_nce_embed_size = conf.max_instrument_num+1
        # self.instrument_nce_embed = torch.nn.Identity()

        output_hidden_size = hidden+ins_nce_embed_size+1

        # mod_embed_size = 8
        # self.mod_embed_weights = torch.nn.Parameter(
            # torch.empty(mod_size, mod_embed_size),
            # requires_grad = True
        # )
        self.dropout = torch.nn.Dropout(dropout)

#         self.input_cnn = model_base.SeqCNN(
#             self.aa_embedding_size+mod_feature_size
#         )

        self.input_rnn = model_base.SeqLSTM(
            self.aa_embedding_size+mod_feature_size,
            hidden,
            rnn_layer=1, bidirectional=BiRNN
        )

        self.hidden = model_base.SeqLSTM(
            output_hidden_size,
            hidden, rnn_layer=hidden_rnn_layer,
            bidirectional=BiRNN
        )

        self.output = model_base.SeqLSTM(
            output_hidden_size,
            num_ion_types,
            rnn_layer=1, bidirectional=False
        )

    def forward(self,
        aa_indices,
        mod_x,
        charges:torch.Tensor,
        NCEs:torch.Tensor,
        instrument_indices,
    ):
        aa_x = torch.nn.functional.one_hot(aa_indices, self.aa_embedding_size)
        inst_x = torch.nn.functional.one_hot(instrument_indices, self.max_instrument_num)

        ins_nce = torch.cat((inst_x, NCEs), 1)
        ins_nce = self.instrument_nce_embed(ins_nce)
        ins_nce_charge = torch.cat((ins_nce, charges), 1)
        ins_nce_charge = ins_nce_charge.unsqueeze(1).repeat(1, aa_x.size(1), 1)

        x = torch.cat((aa_x, mod_x), 2)
        x = self.input_rnn(x)
        x = self.dropout(x)

        x = torch.cat((x, ins_nce_charge), 2)
        x = self.hidden(x)
        x = self.dropout(x)

        x = torch.cat((x, ins_nce_charge), 2)

        x = self.output(x)[:,3:,:]

        return x


# Cell
class IntenAwareLoss(torch.nn.Module):
    def __init__(self, base_weight=0.2):
        super().__init__()
        self.w = base_weight

    def forward(self, pred, target):
        return torch.mean(
            (target+self.w)*torch.abs(target-pred)
        )

# Cell
mod_feature_size = len(model_const['mod_elements'])
max_instrument_num = model_const['max_instrument_num']
frag_types = settings['model']['frag_types']
max_frag_charge = settings['model']['max_frag_charge']
num_ion_types = len(frag_types)*max_frag_charge
nce_factor = model_const['nce_factor']
charge_factor = model_const['charge_factor']

class pDeepModel(model_base.ModelImplBase):
    def __init__(self,
        dropout=0.2,
        lr=0.001,
        model_class:torch.nn.Module=ModelMSMSpDeep3,
    ):
        super().__init__()
        self.charged_frag_types = get_charged_frag_types(
            frag_types, max_frag_charge
        )
        self.charge_factor = charge_factor
        self.NCE_factor = nce_factor
        self.build(
            model_class,
            mod_feature_size = mod_feature_size,
            num_ion_types = len(self.charged_frag_types),
            max_instrument_num = max_instrument_num,
            dropout=dropout,
            lr=lr
        )
        self.loss_func = IntenAwareLoss()
        # self.loss_func = torch.nn.L1Loss()
        self.min_inten = 1e-4

    def _prepare_train_data_df(self,
        precursor_df:pd.DataFrame,
        fragment_inten_df:pd.DataFrame=None,
    ):
        self.frag_inten_df = fragment_inten_df[self.charged_frag_types]
        if np.all(precursor_df['NCE'].values > 1):
            precursor_df['NCE'] = precursor_df['NCE']*self.NCE_factor

    def _prepare_predict_data_df(self,
        precursor_df:pd.DataFrame,
        reference_frag_df:pd.DataFrame=None,
    ):

        self.predict_df = init_fragment_by_precursor_dataframe(
            precursor_df, self.charged_frag_types, reference_frag_df
        )

        if np.all(precursor_df['NCE'].values > 1):
            precursor_df['NCE'] = precursor_df['NCE']*self.NCE_factor

    def _get_features_from_batch_df(self,
        batch_df: pd.DataFrame,
        nAA, **kargs,
    ) -> Tuple[torch.Tensor]:
        aa_indices = torch.LongTensor(
            parse_aa_indices(
                batch_df['sequence'].values.astype('U')
            )
        )

        mod_x_batch = get_batch_mod_feature(batch_df, nAA)
        mod_x = torch.Tensor(mod_x_batch)

        charges = torch.Tensor(
            batch_df['charge'].values
        ).unsqueeze(1)*self.charge_factor

        nces = torch.Tensor(batch_df['NCE'].values).unsqueeze(1)

        instrument_indices = torch.LongTensor(
            parse_instrument_indices(batch_df['instrument'])
        )
        return aa_indices, mod_x, charges, nces, instrument_indices

    def _get_targets_from_batch_df(self,
        batch_df: pd.DataFrame, nAA,
        fragment_inten_df:pd.DataFrame=None
    ) -> torch.Tensor:
        return torch.Tensor(
            get_sliced_fragment_dataframe(
                fragment_inten_df,
                batch_df[
                    ['frag_start_idx','frag_end_idx']
                ].values
            ).values
        ).view(-1, nAA-1, len(self.charged_frag_types))

    def _set_batch_predict_data(self,
        batch_df: pd.DataFrame,
        predicts:np.array,
        **kargs,
    ):
        predicts = predicts.clip(max=1)
        predicts[predicts<self.min_inten] = 0
        set_sliced_fragment_dataframe(
            self.predict_df,
            predicts.reshape(
                (-1, len(self.charged_frag_types))
            ),
            batch_df[
                ['frag_start_idx','frag_end_idx']
            ].values,
            self.charged_frag_types
        )

# Cell

def pearson(x, y):
    return torch.cosine_similarity(
        x-x.mean(dim=1, keepdim=True),
        y-y.mean(dim=1, keepdim=True),
        dim = 1
    )

def spectral_angle(cos):
    cos[cos>1] = 1
    return 1 - 2 * torch.arccos(cos) / np.pi

def _get_ranks(x: torch.Tensor, device) -> torch.Tensor:
    sorted_idx = x.argsort(dim=1)
    flat_idx = (
        sorted_idx+torch.arange(
            x.size(0), device=device
        ).unsqueeze(1)*x.size(1)
    ).flatten()
    ranks = torch.zeros_like(flat_idx)
    ranks[flat_idx] = torch.arange(
        x.size(1), device=device
    ).unsqueeze(0).repeat(x.size(0),1).flatten()
    ranks = ranks.reshape(x.size())
    ranks[x==0] = 0
    return ranks

def spearman(x: torch.Tensor, y: torch.Tensor, device):
    """Compute correlation between 2 2-D tensors
    Args:
        x: Shape (N, M)
        y: Shape (N, M)
    """
    x_rank = _get_ranks(x, device)
    y_rank = _get_ranks(y, device)

    n = x.size(1)
    upper = 6 * torch.sum((x_rank - y_rank).pow(2), dim=1)
    down = n * (n ** 2 - 1.0)
    return 1.0 - (upper / down)

def evaluate_msms(
    psm_df: pd.DataFrame,
    predict_inten_df: pd.DataFrame,
    fragment_inten_df: pd.DataFrame,
    charged_frag_types: List=None,
    metrics = ['PCC','COS','SA','SPC'],
    GPU = True,
    batch_size=10240,
    verbose=False,
)->pd.DataFrame:

    if torch.cuda.is_available() and GPU:
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')

    if not charged_frag_types:
        charged_frag_types = fragment_inten_df.columns.values

    _grouped = psm_df.groupby('nAA')

    if verbose:
        batch_tqdm = tqdm(_grouped)
    else:
        batch_tqdm = _grouped

    for met in metrics:
        psm_df[met] = 0

    for nAA, df_group in batch_tqdm:
        for i in range(0, len(df_group), batch_size):
            batch_end = i+batch_size
            batch_df = df_group.iloc[i:batch_end,:]

            pred_intens = torch.Tensor(
                get_sliced_fragment_dataframe(
                    predict_inten_df,
                    batch_df[
                        ['frag_start_idx','frag_end_idx']
                    ].values,
                    charged_frag_types
                ).values
            ).reshape(
                -1, (nAA-1)*len(charged_frag_types)
            ).to(device)

            frag_intens = torch.Tensor(
                get_sliced_fragment_dataframe(
                    fragment_inten_df,
                    batch_df[
                        ['frag_start_idx','frag_end_idx']
                    ].values,
                    charged_frag_types
                ).values
            ).reshape(
                -1, (nAA-1)*len(charged_frag_types)
            ).to(device)

            if 'PCC' in metrics:
                psm_df.loc[batch_df.index,'PCC'] = pearson(
                    pred_intens, frag_intens
                ).cpu().detach().numpy()

            if 'COS' in metrics or 'SA' in metrics:
                cos = torch.cosine_similarity(
                    pred_intens, frag_intens, dim=1
                )
                psm_df.loc[
                    batch_df.index,'COS'
                ] = cos.cpu().detach().numpy()

                if 'SA' in metrics:
                    psm_df.loc[
                        batch_df.index,'SA'
                    ] = spectral_angle(
                        cos
                    ).cpu().detach().numpy()

            if 'SPC' in metrics:
                psm_df.loc[batch_df.index,'SPC'] = spearman(
                    pred_intens, frag_intens, device
                ).cpu().detach().numpy()

    metrics_describ = psm_df[metrics].describe()
    add_cutoff_metric(metrics_describ, psm_df, thres=0.9)
    add_cutoff_metric(metrics_describ, psm_df, thres=0.75)

    torch.cuda.empty_cache()
    return psm_df, metrics_describ

def add_cutoff_metric(
    metrics_describ, metrics_df, thres=0.9
):
    vals = []
    for col in metrics_describ.columns.values:
        vals.append(metrics_df.loc[metrics_df[col]>thres, col].count()/len(metrics_df))
    metrics_describ.loc[f'>{thres:.2f}'] = vals
    return metrics_describ
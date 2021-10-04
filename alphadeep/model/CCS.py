# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/model/CCS.ipynb (unless otherwise specified).

__all__ = ['TorchModelCCS']

# Cell
import torch
import pandas as pd
import numpy as np

from tqdm import tqdm

from alphadeep.model.featurize import \
    parse_aa_indices, \
    get_batch_mod_feature

from alphadeep._settings import \
    global_settings as settings, \
    const_settings

import alphadeep.model.base as model_base

class TorchModelCCS(torch.nn.Module):
    def __init__(self,
        mod_feature_size,
        dropout=0.2
    ):
        super().__init__()
        BiRNN = True
        self.aa_embedding_size = 27
        hidden=128
        hidden_rnn_layer=2

        # ins_nce_embed_size = conf.max_instrument_num+1
        # self.instrument_nce_embed = torch.nn.Identity()

        output_hidden_size = hidden*(2 if BiRNN else 1)

        # mod_embed_size = 8
        # self.mod_embed_weights = torch.nn.Parameter(
            # torch.empty(mod_size, mod_embed_size),
            # requires_grad = True
        # )
        self.dropout = torch.nn.Dropout(dropout)

        self.input = model_base.SeqLSTM(
            self.aa_embedding_size+mod_feature_size+1,
            hidden, rnn_layer=1,
            bidirectional=BiRNN
        )

        self.hidden = model_base.SeqLSTM(
            output_hidden_size+1,
            hidden, rnn_layer=hidden_rnn_layer,
            bidirectional=BiRNN
        )

        self.output = model_base.LinearDecoder(
            output_hidden_size*2,
            1
        )

    def forward(self,
        aa_indices,
        mod_x,
        charges:torch.Tensor,
    ):
        aa_x = torch.nn.functional.one_hot(aa_indices, self.aa_embedding_size)
        charges = charges.unsqueeze(2)

        x = torch.cat((aa_x, mod_x, charges), 2)
        x = self.input(x)
        x = self.dropout(x)

        x = torch.cat((x, charges), 2)
        x = self.hidden(x)
        x = self.dropout(x)

        x = torch.cat((x[:,0,:],x[:,-1,:]),1)

        return self.output(x).squeeze(1)

# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/protein/fasta.ipynb (unless otherwise specified).

__all__ = ['protease_dict', 'read_fasta_file', 'load_all_proteins', 'read_fasta_file_entries', 'concat_proteins',
           'cleave_sequence_with_cut_pos', 'Digest', 'get_fix_mods', 'get_candidate_sites', 'get_var_mod_sites',
           'get_var_mods_per_sites_multi_mods_on_aa', 'get_var_mods_per_sites_single_mod_on_aa', 'get_var_mods',
           'get_var_mods_per_sites', 'get_mods', 'FastaPeptideLibrary']

# Cell
import regex as re
import numpy as np
import pandas as pd
import numba
import os
from Bio import SeqIO

from alphabase.yaml_utils import load_yaml
from alphadeep.spec_lib.predict_lib import PredictLib
from alphadeep.pretrained_models import AlphaDeepModels

protease_dict = load_yaml(
    os.path.join(
        os.path.dirname(
            __file__
        ),
        'protease.yaml'
    )
)

# Cell

from alphabase.peptide.fragment import update_precursor_mz

def read_fasta_file(fasta_filename:str=""):
    """
    Read a FASTA file line by line
    Args:
        fasta_filename (str): fasta.
    Yields:
        dict {id:str, name:str, description:str, sequence:str}: protein information.
    """
    with open(fasta_filename, "rt") as handle:
        iterator = SeqIO.parse(handle, "fasta")
        while iterator:
            try:
                record = next(iterator)
                parts = record.id.split("|")  # pipe char
                if len(parts) > 1:
                    id = parts[1]
                else:
                    id = record.name
                sequence = str(record.seq)
                entry = {
                    "id": id,
                    "name": record.name,
                    "description": record.description,
                    "sequence": sequence,
                }

                yield entry
            except StopIteration:
                break

def load_all_proteins(fasta_file_list:list):
    protein_dict = {}
    for fasta in fasta_file_list:
        for protein in read_fasta_file(fasta):
            protein_dict[protein['id']] = protein
    return protein_dict

def read_fasta_file_entries(fasta_filename=""):
    """
    Function to count entries in fasta file
    Args:
        fasta_filename (str): fasta.
    Returns:
        int: number of entries.
    """
    with open(fasta_filename, "rt") as handle:
        iterator = SeqIO.parse(handle, "fasta")
        count = 0
        while iterator:
            try:
                record = next(iterator)
                count+=1
            except StopIteration:
                break

        return count

def concat_proteins(protein_dict):
    seq_list = ['']
    seq_count = 1
    for key in protein_dict:
        protein_dict[key]['offset'] = seq_count
        seq_list.append(protein_dict[key]['sequence'])
        seq_count += protein_dict[key]['sequence']+1
    seq_list.append('')
    return '$'.join(seq_list)

# Cell
@numba.njit
def cleave_sequence_with_cut_pos(
    sequence:str,
    cut_pos:np.array,
    n_missed_cleavages:int=2,
    pep_length_min:int=6,
    pep_length_max:int=45,
)->np.array:
    """
    Cleave a sequence with cut postions (cut_pos).
    Filters to have a minimum and maximum length.
    Args:
        sequence (str): protein sequence
        cut_pos (np.array): cut postions determined by a given protease.
        n_missed_cleavages (int): the number of max missed cleavages.
        pep_length_min (int): min peptide length.
        pep_length_max (int): max peptide length.
    Returns:
        list (str): cleaved peptide sequences with missed cleavages.
        list (int): number of miss cleavage of each peptide
    """
    seq_list = []
    miss_list = []
    for i,start_pos in enumerate(cut_pos):
        for n_miss,end_pos in enumerate(
            cut_pos[i+1:i+2+n_missed_cleavages]
        ):
            if end_pos > start_pos + pep_length_max:
                break
            elif end_pos < start_pos + pep_length_min:
                continue
            else:
                seq_list.append(sequence[start_pos:end_pos])
                miss_list.append(n_miss)
    return seq_list, miss_list

class Digest(object):
    def __init__(self,
        protease='trypsin',
        n_missed_cleavages:int=2,
        pep_length_min:int=6,
        pep_length_max:int=45,
    ):
        self.n_miss_cleave = n_missed_cleavages
        self.pep_length_min = pep_length_min
        self.pep_length_max = pep_length_max
        self.regex_pattern = re.compile(
            protease_dict[protease]
        )

    def cleave_sequence(self,
        sequence:str,
    )->list:
        """
        Cleave a sequence.
        Args:
            sequence (str): the given (protein) sequence.
        Returns:
            list (of str): cleaved peptide sequences with missed cleavages.
        """

        cut_pos = [0]
        cut_pos.extend([
            m.start()+1 for m in
            self.regex_pattern.finditer(sequence)
        ])
        cut_pos.append(len(sequence))
        cut_pos = np.array(cut_pos, dtype=np.int64)

        return cleave_sequence_with_cut_pos(
            sequence, cut_pos,
            self.n_miss_cleave,
            self.pep_length_min,
            self.pep_length_max,
        )

# Cell
import numba
import itertools

def get_fix_mods(
    sequence:str,
    fix_mod_aas:str,
    fix_mod_dict:dict
)->tuple:
    mods = []
    mod_sites = []
    for i,aa in enumerate(sequence):
        if aa in fix_mod_aas:
            mod_sites.append(i+1)
            mods.append(fix_mod_dict[aa])
    return ';'.join(mods), mod_sites

# Cell
def get_candidate_sites(
    sequence:str, target_mod_aas:str
)->list:
    candidate_sites = []
    for i,aa in enumerate(sequence):
        if aa in target_mod_aas:
            candidate_sites.append(i+1) #alphabase mod sites
    return candidate_sites

def get_var_mod_sites(
    sequence:str,
    target_mod_aas:str,
    max_var_mod: int,
    max_combs: int
)->list:
    candidate_sites = get_candidate_sites(
        sequence, target_mod_aas
    )
    mod_sites = [(s,) for s in candidate_sites]
    for n_var_mod in range(2, max_var_mod+1):
        if len(mod_sites)>=max_combs: break
        mod_sites.extend(
            itertools.islice(
                itertools.combinations(
                    candidate_sites, n_var_mod
                ),
                max_combs-len(mod_sites)
            )
        )
    return mod_sites

# Cell
import copy
def get_var_mods_per_sites_multi_mods_on_aa(
    sequence:str,
    mod_sites:tuple,
    var_mod_dict:dict
)->list:
    mods_str_list = ['']
    for i,site in enumerate(mod_sites):
        _new_list = []
        for mod in var_mod_dict[sequence[site-1]]:
            _lst = copy.deepcopy(mods_str_list)
            for i in range(len(_lst)):
                _lst[i] += mod+';'
            _new_list.extend(_lst)
        mods_str_list = _new_list
    return [mod[:-1] for mod in mods_str_list]

def get_var_mods_per_sites_single_mod_on_aa(
    sequence:str,
    mod_sites:tuple,
    var_mod_dict:dict
)->list:
    mod_str = ''
    for site in mod_sites:
            mod_str += var_mod_dict[sequence[site-1]]+';'
    return [mod_str[:-1]]

get_var_mods_per_sites = get_var_mods_per_sites_single_mod_on_aa

def get_var_mods(
    sequence:str,
    var_mod_aas:str,
    mod_dict:dict,
    max_var_mod:int,
    max_combs:int,
)->list:
    mod_sites_list = get_var_mod_sites(
        sequence, var_mod_aas,
        max_var_mod, max_combs
    )
    ret_mods = []
    ret_sites_list = []
    for mod_sites in mod_sites_list:
        _mods = get_var_mods_per_sites(
            sequence,mod_sites,mod_dict
        )
        ret_mods.extend(_mods)
        ret_sites_list.extend([mod_sites]*len(_mods))
    return ret_mods, ret_sites_list

# Cell
def get_mods(
    sequence:str,
    fix_mod_aas:str,
    fix_mod_dict:dict,
    var_mod_aas:str,
    var_mod_dict:dict,
    max_var_mod:int,
    max_combs:int,
):
    fix_mods, fix_mod_sites = get_fix_mods(
        sequence, fix_mod_aas, fix_mod_dict
    )
    var_mods_list, var_mod_sites_list = get_var_mods(
        sequence, var_mod_aas, var_mod_dict,
        max_var_mod, max_combs-1, # 1 for unmodified
    )
    if len(var_mods_list) == 0 and len(fix_mods) == 0:
        return [''],['']
    elif len(var_mods_list) == 0:
        fix_mod_sites = ';'.join([str(i) for i in fix_mod_sites])
        return [fix_mods], [fix_mod_sites]
    elif len(fix_mods) == 0:
        return (
            ['']+var_mods_list,
            ['']+[
                ';'.join([str(i) for i in var_mod_sites])
                for var_mod_sites in var_mod_sites_list
            ]
        )
    else:
        fix_mod_sites = ';'.join([str(i) for i in fix_mod_sites])
        return (
            [fix_mods]+[
                fix_mods+';'+var_mods
                for var_mods in var_mods_list
            ],
            [fix_mod_sites]+[
                fix_mod_sites+';'
                +';'.join([str(i) for i in var_mod_sites])
                for var_mod_sites in var_mod_sites_list
            ]
        )

# Cell
def _flatten(list_of_lists):
    '''
    Flatten a list of lists
    '''
    return list(
        itertools.chain.from_iterable(list_of_lists)
    )

class FastaPeptideLibrary(PredictLib):
    def __init__(self,
        models:AlphaDeepModels,
        charged_frag_types = ['b_z1','b_z2','y_z1','y_z2'],
        min_frag_mz = 50, max_frag_mz = 2000,
        min_precursor_mz = 400, max_precursor_mz = 2000,
        protease:str = 'trypsin',
        n_missed_cleavages = 3,
        pep_length_min = 7,
        pep_length_max = 35,
        min_charge = 2,
        max_charge = 4,
        var_mods = ['Oxidation@M'],
        max_var_mod_num = 3,
        fix_mods = ['Carbamidomethyl@C'],
    ):
        super().__init__(
            models, charged_frag_types,
            min_frag_mz, max_frag_mz,
            min_precursor_mz, max_precursor_mz
        )
        self.max_mod_combs = 100
        self._digest = Digest(
            protease, n_missed_cleavages,
            pep_length_min, pep_length_max
        )
        self.min_charge = min_charge
        self.max_charge = max_charge

        self.var_mods = numba.typed.List(var_mods)
        self.fix_mods = numba.typed.List(fix_mods)
        self.max_var_mod_num = max_var_mod_num

        self.fix_mod_aas = ''
        self.fix_mod_nterm = []
        self.fix_mod_cterm = []
        self.fix_mod_dict = {}

        for mod in fix_mods:
            if mod.find('@')+2 == len(mod):
                self.fix_mod_aas += mod[-1]
                self.fix_mod_dict[mod[-1]] = mod

        self.var_mod_aas = ''
        self.var_mod_nterm = []
        self.var_mod_cterm = []
        self.var_mod_dict = {}

        if self._check_if_multi_mods_on_aa(var_mods):
            for mod in var_mods:
                if mod.find('@')+2 == len(mod):
                    if mod[-1] in self.fix_mod_dict: continue
                    self.var_mod_aas += mod[-1]
                    if mod[-1] in self.var_mod_dict:
                        self.var_mod_dict[mod[-1]].append(mod)
                    else:
                        self.var_mod_dict[mod[-1]] = [mod]
            global get_var_mods_per_sites
            get_var_mod_sites = get_var_mods_per_sites_multi_mods_on_aa
        else:
            for mod in var_mods:
                if mod.find('@')+2 == len(mod):
                    if mod[-1] in self.fix_mod_dict: continue
                    self.var_mod_aas += mod[-1]
                    self.var_mod_dict[mod[-1]] = mod
            global get_var_mods_per_sites
            get_var_mod_sites = get_var_mods_per_sites_single_mod_on_aa

    def _check_if_multi_mods_on_aa(self, var_mods):
        mod_set = set()
        for mod in var_mods:
            if mod.find('@')+2 == len(mod):
                if mod[-1] in mod_set: return True
                mod_set.add(mod[-1])
        return False

    def from_fasta_list(self, fasta_file_list:list):
        protein_dict = load_all_proteins(fasta_file_list)
        self.from_protein_dict(protein_dict)

    def from_protein_dict(self, protein_dict:dict):
        pep_set = set()
        for prot_id, protein in protein_dict:
            (
                seq_list, miss_list
            ) = self._digest.cleave_sequence(protein['sequence'])
            pep_set.update(seq_list)
        self._precursor_df = pd.DataFrame()
        self._precursor_df['sequence'] = seq_list
        self._precursor_df['mods'] = ''
        self._precursor_df['mod_sites'] = ''
        self._precursor_df['mod_sites'] = ''
        self._precursor_df['charge'] = [
            list(range(self.min_charge, self.max_charge+1))
        ]*len(pep_set)
        self._precursor_df = self._precursor_df.explode('charge')
        self._precursor_df = update_precursor_mz(self._precursor_df)

    def add_modifications(self):
        (
            self._precursor_df['mods'],
            self._precursor_df['mod_sites']
        ) = zip(*self._precursor_df['sequence'].apply(
            get_mods,
            fix_mod_aas=self.fix_mod_aas,
            fix_mod_dict=self.fix_mod_dict,
            var_mod_aas=self.var_mod_aas,
            var_mod_dict=self.var_mod_dict,
            max_var_mod=self.max_var_mod_num,
            max_combs=self.max_mod_combs,
        ))
        self._precursor_df = self._precursor_df.explode(
            ['mods','mod_sites']
        ).reset_index(drop=True)

        self._precursor_df = update_precursor_mz(self._precursor_df)

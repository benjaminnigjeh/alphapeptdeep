peptdeep cmd-flow \
--settings_yaml "/xx/peptdeep.yaml" \
--peak_matching--ms2_ppm True \
--peak_matching--ms2_tol_value 10.0 \
--model_mgr--default_nce 25.0 \
--model_mgr--default_instrument ThermoTOF \
--model_mgr--external_ms2_model /xxx/ms2.pth \
--model_mgr--external_rt_model /xxx/rt.pth \
--model_mgr--external_ccs_model /xxx/ccs.pth \
--model_mgr--transfer--psm_modification_mapping "Dimethyl@Any_N-term:_(Dimethyl-n-0);_(Dimethyl)" "Dimethyl@K:K(Dimethyl-K-0);K(Dimethyl)" \
--model_mgr--transfer--model_output_folder /Users/wenfengzeng/data/orbi_dia/hla/refined-models \
--model_mgr--transfer--epoch_ms2 10 \
--model_mgr--transfer--warmup_epoch_ms2 5 \
--model_mgr--transfer--epoch_rt_ccs 10 \
--model_mgr--transfer--warmup_epoch_rt_ccs 5 \
--model_mgr--transfer--psm_type diann \
--model_mgr--transfer--psm_files /Users/wenfengzeng/data/orbi_dia/hla/20200317_QE_HFX2_LC3_DIA_RA957_R01.tsv \
--model_mgr--transfer--ms_file_type alpharaw_hdf \
--model_mgr--transfer--ms_files /Users/wenfengzeng/data/orbi_dia/hla/20200317_QE_HFX2_LC3_DIA_RA957_R01.raw.hdf \
--model_mgr--transfer--psm_num_to_train_ms2 10000 \
--model_mgr--transfer--psm_num_to_test_ms2 10000 \
--model_mgr--transfer--psm_num_to_train_rt_ccs 10000 \
--model_mgr--transfer--psm_num_to_test_rt_ccs 10000 \
--library--output_folder /Users/wenfengzeng/data/orbi_dia/hla/apd_speclib \
--library--infile_type diann \
--library--infiles /Users/wenfengzeng/data/orbi_dia/hla/20200317_QE_HFX2_LC3_DIA_RA957_R01.tsv \
--library--min_var_mod_num 0 \
--library--max_var_mod_num 1 \
--library--min_precursor_charge 2 \
--library--max_precursor_charge 4 \
--library--min_peptide_len 7 \
--library--max_peptide_len 30 \
--library--min_precursor_mz 400.0 \
--library--max_precursor_mz 1200.0 \
--library--var_mods "Oxidation@M" "Acetyl@Protein_N-term" \
--library--fix_mods "Carbamidomethyl@C" \
--library--fasta--protease trypsin \
--library--fasta--max_miss_cleave 2 \
--library--decoy None \
--library--output_tsv--enabled True \
--library--rt_to_irt True \
--task_workflow train library \
# --library--labeling_channels "0:Dimethyl@Any_N-term;Dimethyl@K" \
# In windows/powershell, use replace " \" with " `" 
# End of the `peptdeep cmd-flow`




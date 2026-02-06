"""File-mapper JSON mapping definitions (source path → destination path).

Mappings are prepared manually and consumed by prepare.py with the file-mapper library.
Keys are paths under the source (BIDS-style with {SUBJECT}, {SESSION}); values are
paths under the destination (often NDA-style with {GUID}).

Example (anat T1w, no session) from nda_ds004869 image03_sourcedata.anat.t1w.json:

    {
        "CHANGES": "CHANGES",
        "README": "README",
        "dataset_description.json": "dataset_description.json",
        "LICENSE": "LICENSE",
        "sub-{SUBJECT}/anat/sub-{SUBJECT}_T1w.nii.gz": "sub-{GUID}/anat/sub-{GUID}_T1w.nii.gz",
        "sub-{SUBJECT}/anat/sub-{SUBJECT}_T1w.json": "sub-{GUID}/anat/sub-{GUID}_T1w.json"
    }

Example (PET with session) from nda_ds004869 image03_sourcedata.pet.pet.json:

    {
        "CHANGES": "CHANGES",
        "README": "README",
        "dataset_description.json": "dataset_description.json",
        "LICENSE": "LICENSE",
        "sub-{SUBJECT}/ses-{SESSION}/pet/sub-{SUBJECT}_ses-{SESSION}_pet.nii.gz": "sub-{GUID}/ses-{SESSION}/pet/sub-{GUID}_ses-{SESSION}_pet.nii.gz",
        "sub-{SUBJECT}/ses-{SESSION}/pet/sub-{SUBJECT}_ses-{SESSION}_pet.json": "sub-{GUID}/ses-{SESSION}/pet/sub-{GUID}_ses-{SESSION}_pet.json",
        "sub-{SUBJECT}/ses-{SESSION}/pet/sub-{SUBJECT}_ses-{SESSION}_recording-manual_blood.json": "sub-{GUID}/ses-{SESSION}/pet/sub-{GUID}_ses-{SESSION}_recording-manual_blood.json",
        "sub-{SUBJECT}/ses-{SESSION}/pet/sub-{SUBJECT}_ses-{SESSION}_recording-manual_blood.tsv": "sub-{GUID}/ses-{SESSION}/pet/sub-{GUID}_ses-{SESSION}_recording-manual_blood.tsv"
    }
"""
import bids
import re

from typing import Union
from pathlib import Path

supported_bids_datatypes = ['anat', 'pet']

class QueriedLayout():
    def __init__(self, bids_layout:bids.BIDSLayout):
        self.bids_layout = bids_layout
        self.datatypes = self.bids_layout.get_datatypes()
        self.subject_mappings = {
            subject: {datatype: [] for datatype in self.datatypes} for subject in self.bids_layout.get_subjects()}
        self.general_mappings = {modality: [] for modality in self.datatypes}
        self.finished_product = {modality: {} for modality in self.datatypes}
        self.populate_subject_mappings()
        self.aggregate_mappings()

    def populate_subject_mappings(self):
        for subject, datatype in self.subject_mappings.items():
            for d in datatype.keys():
                self.subject_mappings[subject][d] = [re.sub(f'sub-{subject}', 'sub-{SUBJECT}', file.relpath) for file in self.bids_layout.get(subject=subject, datatype=d)]
        
    def aggregate_mappings(self):
        for subject, datatype in self.subject_mappings.items():
            for d in datatype.keys():
                self.general_mappings[d].extend(self.subject_mappings[subject][d])
        # create a set of all unique mappings
        for datatype, mappings in self.general_mappings.items():
            self.general_mappings[datatype] = list(set(mappings))

        # extend the mappings into a dictionary with their nda targets
        for datatype, mappings in self.general_mappings.items():
            self.finished_product[datatype] = {m: re.sub('SUBJECT', 'GUID', m) for m in mappings}
    
    #def build_nda_half(self):


        


def create_jsons(bids_dataset: Union[bids.BIDSLayout, Path, str], upload_dir):
    # make a bids layout
    if type(bids_dataset) is not bids.BIDSLayout:
        layout = bids.BIDSLayout(bids_dataset)
    else:
        layout = bids_dataset

    return None

def create_yamls(bids_dataset, upload_dir):
    if type(bids_dataset) is not bids.BIDSLayout:
        layout = bids.BIDSLayout(bids_dataset)
    else:
        layout = bids_dataset
    return None
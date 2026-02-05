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


def create_jsons(bids_dataset, upload_dir):
    # make a bids layout
    layout = bids.BIDSLayout(bids_dataset)
    return None

def create_yamls(bids_dataset, upload_dir):
    layout = bids.BIDSLayout(bids_dataset)
    return None
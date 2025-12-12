import bids
import pathlib
import os
import pandas
import json
from typing import Any, Union

def load_bids(path_to_bids_dataset:str):
    # cast as string for pybids
    path_to_bids_dataset = str(path_to_bids_dataset)
    bids_layout = bids.BIDSLayout(path_to_bids_dataset)

    # check for a participants.tsv and .json
    participants_tsv = None
    participants_json = None
    if bids_layout.get(suffix='participants', extension='tsv'):
        try:
            participants_tsv = pandas.read_csv(
                bids_layout.get(suffix='participants', extension='tsv', index_col='participant_id'
                )
            )
        except (FileExistsError, FileNotFoundError):
            pass
    if participants_tsv and bids_layout.get(suffix='participants', extension='json'):
        try:
            participants_json = json.load(bids_layout.get(suffix='participants', extension='json'))
        except (FileExistsError, FileNotFoundError, json.JSONDecodeError):
            pass
    
    pull_from_participants = bool(participants_tsv and participants_json)

    age_multiplier = 0
    if pull_from_participants:
        # check to see what units are in age
        if 'y' in str.lower(participants_json.get('age', {}).get('Units', "")):
            age_multiplier = 12
        elif 'm' in str.lower(participants_json.get('age', {}).get('Units', "")):
            age_multiplier = 1
        elif 'w' in str.lower(participants_json.get('age', {}).get('Units', "")):
            age_multiplier = (1/4)
        else:
            print(f"unable to determine participant.age.Units from {bids.layout.get(suffix='participants', extension='json')}, not converting to weeks.")

    subject_list = bids_layout.get_subjects()
    subject_session_list = []
    for s in subject_list:    
        # get any non-session folders/files
        for entities in bids_layout.get(subject=s):
            ents = entities.get_entities()
            bids_subject_session = "sub-" + ents.get("subject")
            if ents.get("session"):
                bids_subject_session += f'_ses-{ents.get("session")}'
                
                info = {
                "bids_subject_session": bids_subject_session,
                "subjectkey": "",
                "src_subject_id": f"sub-{s}",
                "interview_date": "",
                "interview_age": "",
                "sex": "",
                "datatype": ents.get('datatype', '')
            }
            

            subject_session_list.append()
    
    


    return subject_session_list
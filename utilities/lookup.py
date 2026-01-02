import bids
import pathlib
import os
import pandas
import json
from typing import Union

class LookUpTable():
    def __init__(self, path_to_bids_dataset: str, destination_path=""):
        self.path_to_bids_dataset = str(path_to_bids_dataset)
        self.bids_layout = bids.BIDSLayout(self.path_to_bids_dataset)
        self.destination_path = destination_path
        self.participants_tsv = None
        self.participants_json = None
        self.subject_list = self.bids_layout.get_subjects()
        self.subject_session_list = []
        self.lookup_table = pandas.DataFrame()
    
    def create_lookup_table(self):
    # check for a participants.tsv and .json
        if self.bids_layout.get(suffix='participants', extension='tsv'):
            try:
                participants_tsv = pandas.read_csv(
                    os.path.join(self.path_to_bids_dataset, self.bids_layout.get(suffix='participants', extension='tsv')[0]),
                    index_col='participant_id',
                    sep='\t'
                )
            except (FileExistsError, FileNotFoundError):
                pass
        if participants_tsv is not None and self.bids_layout.get(suffix='participants', extension='json'):
            try:
                with open(self.bids_layout.get(suffix='participants', extension='json')[0], 'r') as infile:
                    participants_json = json.load(infile)
            except (FileExistsError, FileNotFoundError, json.JSONDecodeError):
                pass
        
        # we need a participants.json and participants.tsv to continue forward
        if participants_tsv is None and participants_json is None:
            raise f"Requires valid participants.tsv and participants.json for the dataset located at {path_to_bids_dataset}"
        else:
            age_multiplier = 1
            # check to see what units are in age
            if 'y' in str.lower(participants_json.get('age', {}).get('Units', "")):
                age_multiplier = 12
            elif 'm' in str.lower(participants_json.get('age', {}).get('Units', "")):
                age_multiplier = 1
            elif 'w' in str.lower(participants_json.get('age', {}).get('Units', "")):
                age_multiplier = (1/4)
            else:
                print(
                    f"unable to determine participant.age.Units from \
                    {bids.layout.get(suffix='participants', extension='json')}, \
                    not converting to months."
                    )
            print(f"age_multiplyer={age_multiplier}")
        
        # create a subject/session list
        for s in self.subject_list:
            for entities in self.bids_layout.get(subject=s):
                ents = entities.get_entities()
                bids_subject_session = "sub-" + ents.get("subject")
                if ents.get("session"):
                    bids_subject_session += f'_ses-{ents.get("session")}'

                info = {
                "bids_subject_session": bids_subject_session,
                "subjectkey": "",
                "src_subject_id": f"sub-{s}",
                "interview_date": "",
                "interview_age": age_multiplier * float(participants_tsv['age'][f"sub-{s}"]),
                "sex": participants_tsv['sex'][f"sub-{s}"],
                "datatype": ents.get('datatype', '')
                }
                self.subject_session_list.append(info)
        self.lookup_table = pandas.DataFrame(self.subject_session_list)

        return self.lookup_table

    def write_lookup_table(self):
        if self.lookup_table.empty:
            self.create_lookup_table()
        self.lookup_table.to_csv(self.destination_path, sep=',', na_rep="n/a", index=False)

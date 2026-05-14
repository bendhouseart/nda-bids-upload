import bids
import pathlib
import os
import pandas
import json
from argparse import ArgumentParser

# NDA expects interview_age in months. TSV values are usually in calendar years.
YEARS_TO_NDA_MONTHS = 12.0
# When age cannot be read from participants, assume this many years, then convert to months.
DEFAULT_MISSING_AGE_YEARS = 89


class LookUpTable:
    def __init__(self, bids_dataset: str, destination_path=""):
        self.path_to_bids_dataset = str(bids_dataset)
        self.bids_layout = bids.BIDSLayout(self.path_to_bids_dataset)
        if not destination_path:
            self.destination_path = "lookup.csv"
        else:
            dest_path = pathlib.Path(destination_path) 
            if dest_path.suffix.lower() == '.csv':
                self.destination_path = dest_path
            else:
                self.destination_path = pathlib.Path(destination_path) / "lookup.csv"
        
        self.participants_tsv = pandas.DataFrame()
        self.participants_json = None
        self.subject_list = self.bids_layout.get_subjects()
        self.subject_session_list = []
        self.lookup_table = pandas.DataFrame()

    def create_lookup_table(self):
        # check for a participants.tsv and .json
        if self.bids_layout.get(suffix="participants", extension="tsv"):
            try:
                self.participants_tsv = pandas.read_csv(
                    os.path.join(
                        self.path_to_bids_dataset,
                        self.bids_layout.get(suffix="participants", extension="tsv")[0],
                    ),
                    index_col="participant_id",
                    sep="\t",
                )
            except (FileExistsError, FileNotFoundError) as err:
                raise (err)
        if not self.participants_tsv.empty:
            participants_json_path = os.path.join(
                self.path_to_bids_dataset, "participants.json"
            )
            try:
                with open(participants_json_path, "r") as infile:
                    self.participants_json = json.load(infile)
            except (FileExistsError, FileNotFoundError, json.JSONDecodeError) as err:
                if isinstance(err, json.JSONDecodeError):
                    raise err
                else:
                    raise FileNotFoundError(
                        f"participants.json not found: {participants_json_path}"
                    ) from err

        # recast gender column and sidecar as sex if gender is present
        gender_col, sex_column = next(
            (
                column
                for column in self.participants_tsv.columns
                if column.lower() == "gender"
            ),
            None,
        ), next(
            (
                column
                for column in self.participants_tsv.columns
                if column.lower() == "sex"
            ),
            None,
        )

        if gender_col and not sex_column:
            self.participants_tsv = self.participants_tsv.rename(
                columns={gender_col: "sex"}
            )

            self.participants_json["sex"] = self.participants_json[gender_col]
            self.participants_json.pop(gender_col)

        age_col, age_to_months_mult = self._age_column_and_months_multiplier()

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
                    "datatype": ents.get("datatype", ""),
                }
                try:
                    raw_age = self.participants_tsv.loc[f"sub-{s}", age_col]
                    months = float(raw_age) * float(age_to_months_mult)
                    info["interview_age"] = int(round(months))
                except (KeyError, TypeError):
                    info["interview_age"] = int(
                        DEFAULT_MISSING_AGE_YEARS * YEARS_TO_NDA_MONTHS
                    )
                for field, default in (("sex", "F"), ("weight", 89)):
                    try:
                        info[field] = self.participants_tsv.loc[f"sub-{s}", field]
                    except (KeyError, TypeError):
                        info[field] = default

                # We're ignoring folders that don't have a datatype for now as their
                # contents are covered by folders that do have a datatype
                if info.get("datatype"):
                    self.subject_session_list.append(info)

        self.lookup_table = pandas.DataFrame(self.subject_session_list).drop_duplicates(
            ignore_index=True
        )

        return self.lookup_table

    def _age_column_and_months_multiplier(self):
        """Column for raw age and multiplier so NDA months = raw * multiplier.

        Early exit still returns YEARS_TO_NDA_MONTHS (years→months), not a default age.
        Missing per-subject age uses DEFAULT_MISSING_AGE_YEARS * YEARS_TO_NDA_MONTHS.
        """
        if self.participants_tsv.empty or not self.participants_json:
            return "age", YEARS_TO_NDA_MONTHS
        age_col = next(
            (
                c
                for c in self.participants_tsv.columns
                if c.lower() in ("interview_age", "age")
            ),
            None,
        )
        if age_col is None:
            return "age", YEARS_TO_NDA_MONTHS
        units = str(
            self.participants_json.get(age_col, {}).get("Units", "") or ""
        ).lower()
        if "month" in units:
            mult = 1.0
        elif "week" in units:
            mult = 0.25
        elif "year" in units:
            mult = YEARS_TO_NDA_MONTHS
        else:
            print(
                "unable to determine participant.age.Units; not converting to months "
                f"(column={age_col!r}, Units={units!r})"
            )
            mult = 1.0
        return age_col, mult

    def write_lookup_table(self):
        if self.lookup_table.empty:
            self.create_lookup_table()
        # create output dir if it doesn't exist
        self.destination_path.parent.mkdir(exist_ok=True)
        self.lookup_table.to_csv(
            self.destination_path, sep=",", na_rep="n/a", index=False
        )
        return self.destination_path


def cli():
    parser = ArgumentParser()
    parser.add_argument("bids_dataset", 
    help="Path to BIDS dataset", 
    type=pathlib.Path)
    parser.add_argument(
        "destination_path", 
        help="Path to NDA upload folder", 
        type=pathlib.Path
    )
    parser.add_argument(
        "--edit-now",
        action="store_true",
        default=False,
        help="Add interview dates and GUID's to lookup csv now",
    )
    args = parser.parse_args()
    lookup_table = LookUpTable(
        str(args.bids_dataset), destination_path=str(args.destination_path)
    )
    df = lookup_table.create_lookup_table()
    lookup_table_path = lookup_table.write_lookup_table()

    if args.edit_now:
        from utilities.lookup_editor import run_lookup_editor

        run_lookup_editor(pathlib.Path(lookup_table_path))


if __name__ == "__main__":
    cli()

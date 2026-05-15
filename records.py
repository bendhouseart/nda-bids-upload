#! /usr/bin/env python3

"""
DCAN Labs NDA BIDS preparation tool

Created  02/20/2020  Eric Earl (earl@ohsu.edu)
"""

import argparse
import csv
import math
import os
import shutil
import sys
import yaml
from argparse import Namespace
from datetime import datetime
from glob import glob
from pathlib import Path

# load nda_manifests.py from submodule
sys.path.append(os.path.abspath("manifest-data"))
from nda_manifests import Manifest


HERE = os.path.dirname(os.path.realpath(__file__))


def vtcmd_path() -> str | None:
    """Resolve ``vtcmd`` (nda-tools).

    Callers assume the active Python environment already has project dependencies
    installed (``nda-tools`` in ``pyproject.toml``). We try ``PATH`` first, then the
    directory next to ``sys.executable`` so a minimal ``PATH`` still finds the script.
    """
    found = shutil.which("vtcmd")
    if found:
        return found
    name = "vtcmd.exe" if sys.platform == "win32" else "vtcmd"
    candidate = Path(sys.executable).parent / name
    if candidate.is_file():
        return str(candidate)
    return None


__doc__ = """
This python command-line tool allows the user to do 
more automated NDA BIDS data upload preparation 
given an input folder structure hierarchy that obeys 
the DCAN Labs NDA BIDS preparation standard.
"""


def generate_parser():

    parser = argparse.ArgumentParser(prog="records.py", description=__doc__)

    parser.add_argument(
        "-p",
        "--parent",
        dest="parent",
        metavar="PARENT_DIR",
        type=str,
        required=True,
        help=(
            'Path to the "parent" folder to be prepared for upload. "Parent" '
            'folder should be of the format: ".../ndastructure_type.class.subset" '
            'containing subfolders called "sub-subject_ses-session.type.class.subset" '
            'where "ndastructure" is fmriresults01, image03, or imagingcollection01, '
            '"subject" is the BIDS subject ID/participant label, '
            '"session" is the BIDS session ID, "type" is either "inputs" or '
            '"derivatives", "class" is "anat", "dwi", "fmap", "func", or something '
            'similar, and "subset" is the user-defined "data subset type".'
            'For example: "image03_inputs.anat.T1w" containing subfolders like '
            '"sub-NDAR123456_ses-baseline.inputs.anat.T1w"'
        ),
    )

    return parser


# Sanity check against user inputs
def records_sanity_check(input):

    # check if input is a directory
    if not os.path.isdir(input):
        print(input + " is not a directory!  Exiting...")
        sys.exit(1)
    else:
        parent = os.path.abspath(os.path.realpath(input))

    dest_dir = os.path.dirname(parent)
    lookup_csv = os.path.join(dest_dir, "lookup.csv")
    manifest_script = os.path.join(HERE, "manifest-data", "nda_manifests.py")

    # check if manifest_script exists
    if not os.path.isfile(manifest_script):
        print(
            manifest_script
            + ' is not a file, contained a directory above "parent" in a directory called manifest-data.  Exiting...'
        )
        sys.exit(2)

    # check if lookup_csv exists
    if not os.path.isfile(lookup_csv):
        print(
            lookup_csv
            + ' is not a file, contained a directory above "parent" called "lookup.csv".  Exiting...'
        )
        sys.exit(3)

    # grab parent's basename
    basename = os.path.basename(parent)
    nda_struct, file_config = basename.split("_", 1)
    if not (
        nda_struct == "fmriresults01"
        or nda_struct == "image03"
        or nda_struct == "imagingcollection01"
    ):
        print(
            basename
            + " is not a valid entry for section A.  Improper parent folder name.  Exiting..."
        )
        sys.exit(4)

    if file_config.count(".") != 2:
        print(
            file_config
            + " is an improper parent folder naming convention.  The parent folder MUST only contain two periods total.  Exiting..."
        )
        sys.exit(5)
    else:
        input_deriv, subsets, types = file_config.split(".")

    if not (
        input_deriv == "inputs"
        or input_deriv == "derivatives"
        or input_deriv == "sourcedata"
    ):
        print(
            input_deriv
            + ' is not a valid entry for section X.  Section X MUST be either "inputs", "derivatives", or "sourcedata".  Improper parent folder name.  Exiting...'
        )
        sys.exit(6)

    if subsets.count("_") != 0:
        print(
            subsets
            + " is not a valid entry for section Y.  Section Y MUST have no underscores.  Improper parent folder name.  Exiting..."
        )
        sys.exit(7)

    problem_child_flag = False
    # here top level refers to common files contained in the top level of the BIDS dataset
    is_bids_toplevel = basename == "image03_sourcedata.bids.toplevel"

    for root, dirs, files in os.walk(parent):
        if root == parent:
            for directory in dirs:
                if is_bids_toplevel and directory == "toplevel.sourcedata.bids.toplevel":
                    continue
                if not directory.startswith("sub-NDAR"):
                    problem_child_flag = True
                    print(
                        "Improper child folder name: "
                        + directory
                        + '.  Child directories MUST start with "sub-NDAR".  Exiting after full check...'
                    )
                else:
                    sub_ses, sub_directory_config = directory.split(".", 1)
                    if sub_directory_config != file_config:
                        problem_child_flag = True
                        print(
                            "Improper child folder name.  Sections X.Y.Z MUST match between parent and child folders.  Exiting after full check..."
                        )

    if problem_child_flag:
        sys.exit(8)

    # compare basename to available "content" YAML files
    content_yamls = [
        content
        for content in glob(os.path.join(dest_dir, "*.yaml"))
        if os.path.basename(content) == basename + ".yaml"
    ]

    if not len(content_yamls) == 1:

        if len(content_yamls) > 1:
            print(
                "More than one content file matches your parent directory's basename ("
                + basename
                + "):"
            )
            for content in content_yamls:
                print("  " + content)
            print("This should never happen.  Please debug records.py.")

        elif len(content_yamls) == 0:
            print(
                "No content .yaml files in "
                + dest_dir
                + " match the basename: "
                + basename
            )
            print(
                "Make sure a matching content .yaml file exists in the folder above the parent folder you provided."
            )

        print("Exiting...")
        sys.exit(9)
    else:
        content_yaml = content_yamls[0]

    # sanity-check entries in correct content YAML file
    print("Sanity-checking: " + content_yaml)
    with open(content_yaml, "r") as f:
        content = yaml.load(f, Loader=yaml.CLoader)

    badflag = False
    for key in content:
        value = content[key]
        if value == "" or value == None:
            badflag = True
            print("Empty field in " + content_yaml + ":")
            print(f"{key}: {value}")
            # print(f'    ' + {key} + ': "' + {value} + '"')

    if badflag:
        print("No empty fields allowed in content .yaml files.  Exiting...")
        sys.exit(10)


def cli(input):

    # setting easy use variables from argparse
    parent = os.path.abspath(os.path.realpath(input))
    dest_dir = os.path.dirname(parent)
    manifest_script = os.path.join(HERE, "manifest-data", "nda_manifests.py")
    lookup_csv = os.path.join(dest_dir, "lookup.csv")

    # grab parent's basename
    basename = os.path.basename(parent)

    # start an empty data template
    if basename.startswith("fmriresults01"):
        ndaheader = '"fmriresults","01"'
        with open(
            os.path.join(HERE, "templates", "fmriresults01_template.csv"), "r"
        ) as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 1:
                    header = row
    elif basename.startswith("imagingcollection01"):
        ndaheader = '"imagingcollection","01"'
        with open(
            os.path.join(HERE, "templates", "imagingcollection01_template.csv"), "r"
        ) as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 1:
                    header = row
    elif basename.startswith("image03"):
        ndaheader = '"image","03"'
        with open(os.path.join(HERE, "templates", "image03_template.csv"), "r") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 1:
                    header = row

    # grabbing yaml
    content_yamls = [
        content
        for content in glob(os.path.join(dest_dir, "*.yaml"))
        if os.path.basename(content) == basename + ".yaml"
    ]

    content_yaml = content_yamls[0]

    # sanity-check entries in correct content YAML file
    with open(content_yaml, "r") as f:
        content = yaml.load(f, Loader=yaml.CLoader)

    # load lookup CSV file
    with open(lookup_csv, "r") as f:
        lookup = [row for row in csv.DictReader(f)]

    ### DO WORK ###

    # get original working dir (just to not break things)
    original_working_dir = os.getcwd()

    # change into parent directory get get relative paths
    os.chdir(parent)

    # 1. GLOB all .../ndastructure_type.class.subset/sub-subject_ses-session.type.class.subset/ folders
    uploads = glob("*.*.*.*")
    # uploads = glob(os.path.join(parent, "*.*.*.*"))
    print(f"parent: {parent}, uploads: {uploads}")
    # 2. loop over the folders
    print(f"{datetime.now()} Creating NDA records")
    records = []
    folders = []
    for upload_dir in uploads:
        # skip to the next iteration of the for loop if the upload_dir is not a directory
        if not os.path.isdir(upload_dir):
            continue

        # create an NDA record for each folder using the content YAML file
        upload_basename = os.path.basename(upload_dir)
        # First segment is NDAR folder id: sub-<GUID>_ses-<label> or sub-<GUID> (not BIDS sub-01)
        folder_stem, datatype, dataclass, datasubset = upload_basename.split(
            "."
        )
        bids_subject_session = folder_stem

        # BIDS toplevel: single folder, use first lookup row and top-level-only manifest
        if basename == "image03_sourcedata.bids.toplevel":
            lookup_record = lookup[0] if lookup else {}
            manifest = Manifest()
            manifest.create_from_dir(upload_dir)
            #manifest.create_from_dir(upload_dir, top_level_only=True)
        else:
            # Folder stem uses NDAR GUID (e.g. sub-NDAR123_ses-baseline); lookup uses BIDS
            # bids_subject_session (sub-01_ses-baseline) + subjectkey. Match GUID + session
            # so each visit folder gets the correct interview_date (do not map GUID→one session).
            rest = folder_stem[4:] if folder_stem.startswith("sub-") else folder_stem
            session_label = None
            if "_ses-" in rest:
                ndar_guid_raw, session_label = rest.split("_ses-", 1)
            else:
                ndar_guid_raw = rest
            ndar_guid = ndar_guid_raw.replace("_", "")

            lookup_record = None
            for row in lookup:
                row_guid = row["subjectkey"].replace("_", "")
                if row_guid != ndar_guid:
                    continue
                bss = row.get("bids_subject_session", "")
                if session_label is None:
                    if "_ses-" not in bss:
                        lookup_record = row
                        break
                else:
                    if "_ses-" in bss and bss.split("_ses-", 1)[1] == session_label:
                        lookup_record = row
                        break

            if lookup_record is None:
                print(
                    f"Warning: No lookup record for folder stem {folder_stem!r} "
                    f"(guid={ndar_guid!r}, session_label={session_label!r})"
                )
                continue

        manifest = Manifest()
        manifest.create_from_dir(upload_dir)
        manifest.output_as_file(
            os.path.join(upload_dir, f"{bids_subject_session}.manifest.json")
        )

        # correct the manifest contents to remove the leading "./" from each manifest element
        # Read the manifest file, replace "./" with "", and write it back
        manifest_json_path = os.path.join(
            upload_dir, f"{bids_subject_session}.manifest.json"
        )
        # Use the absolute parent directory as the base for relative
        # paths so that the manifest column matches the original
        # working_directory behavior (e.g.,
        # "sub-NDAR.../sub-NDAR....manifest.json") and does not
        # include unnecessary "../" segments when the CLI is invoked
        # with a relative -p argument.
        manifest_json_relative_path = os.path.relpath(manifest_json_path, parent)
        try:
            with open(manifest_json_path, "r") as f:
                manifest_content = f.read()
            manifest_content = manifest_content.replace("./", "")
            with open(manifest_json_path, "w") as f:
                f.write(manifest_content)
        except Exception as e:
            print(f"Warning: Could not process manifest file {manifest_json_path}: {e}")

        # write the new record for entry into the larger output CSV
        new_record = {}
        for column in header:
            if column in content:
                new_record[column] = content[column]
            else:
                new_record[column] = ""

        if basename.startswith("fmriresults01") or basename.startswith("image03"):
            # Use relative path from the parent directory instead of absolute path
            new_record["manifest"] = manifest_json_relative_path
            new_record["image_description"] = ".".join(
                [datatype, dataclass, datasubset]
            )
        elif basename.startswith("imagingcollection01"):
            # Use relative path from the parent directory instead of absolute path
            manifest_filename = f"{bids_subject_session}.manifest.json"
            new_record["image_manifest"] = manifest_filename
            new_record["image_collection_desc"] = ".".join(
                [datatype, dataclass, datasubset]
            )

        for column in lookup_record:
            if column != "bids_subject_session" and column in header:
                new_record[column] = lookup_record[column]

        records.append(new_record)
        folders.append(upload_dir)

    os.chdir(original_working_dir)

    with open(parent + ".complete_records.csv", "w") as f:
        f.write(ndaheader + "\n")

        writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    with open(parent + ".complete_folders.txt", "w") as f:
        for folder in folders:
            f.write(folder + "\n")

    max_batch_size = 500  # @TODO this needs to become an integer input defaulted to 500
    total = len(records)
    print(f"total={total}")
    count = math.ceil(float(total) / max_batch_size)
    batch_size = math.ceil(float(total) / count)

    low = 0
    print(f"{datetime.now()} Creating batch files")
    for i in range(1, count + 1):
        if i < count or total == batch_size:
            B = batch_size
        else:
            B = total % batch_size

        records_subset = records[low : (low + B)]
        folders_subset = folders[low : (low + B)]
        low = i * batch_size

        batchname = "_".join([str(total), str(max_batch_size), str(i)])
        records_batch = parent + ".records_" + batchname + ".csv"
        folders_batch = parent + ".folders_" + batchname + ".txt"

        with open(records_batch, "w") as f:
            f.write(ndaheader + "\n")

            writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for record in records_subset:
                writer.writerow(record)

        with open(folders_batch, "w") as f:
            for folder in folders_subset:
                f.write(folder + "\n")

    print("FINISHED " + basename + " RECORDS PREPARATION.")

    validation = run_vtcmd_realtime(parent + ".complete_records.csv", input, log_dir=dest_dir)
    # int 0 is success; `False` is failure (must not use `validation == 0` alone — False == 0 in Python).
    validation_ok = validation is not False and validation == 0
    if validation_ok:
        print(f"Files prepped at {input} with {parent}.complete_records.csv are valid.")
    else:
        print(
            f"Files prepped at {input} with {parent}.complete_records.csv are invalid, run\n"
            f"vtcmd {parent}.complete_records.csv -m {input} --verbose\n"
            f"for more details on how to fix"
        )
    # run_vtcmd_realtime returns False on exception; check before `== 0` because False == 0 in Python.
    if validation is False:
        return 1
    if validation == 0:
        return 0
    if isinstance(validation, int):
        return validation
    return 1


def _build_vtcmd_args(csv_file, manifest_dir, log_dir=None):
    """Arguments matching ``vtcmd`` CLI flags used by this project (-m, -w, -f)."""
    nda_user = (
        os.environ.get("NDA_USERNAME") or os.environ.get("NDA_TOOLS_USERNAME") or ""
    ).strip() or None
    manifest_path = [manifest_dir] if manifest_dir else None
    custom_log_dir = log_dir if log_dir and os.path.isdir(log_dir) else None
    return Namespace(
        files=[csv_file],
        listDir=None,
        manifestPath=manifest_path,
        warning=True,
        buildPackage=False,
        collectionID=None,
        description=None,
        title=None,
        username=nda_user,
        scope=None,
        replace_submission=0,
        resume=False,
        JSON=False,
        workerThreads=None,
        batch=50,
        hideProgress=False,
        force=True,
        validation_timeout=300,
        verbose=False,
        log_dir=custom_log_dir,
    )


def _qa_error_count_excluding_duplicate_records(qa_results):
    """Match legacy CSV parsing: ignore QA rows whose error code is duplicateRecords."""
    return sum(
        1
        for error in qa_results.errors
        if "duplicateRecords" not in (error.err_code or "")
    )


def _run_vtcmd_validate(args, config):
    """Run the same validation steps as ``vtcmd`` without ``os._exit`` on failures."""
    import logging

    from NDATools import authenticate

    logger = logging.getLogger(__name__)

    if not config.is_authenticated():
        authenticate(config)

    validated_files = config.upload_cli.validate(args.files, args.manifestPath)

    if any(vf.system_error() for vf in validated_files):
        errors_file = config.validation_results_writer.write_errors(validated_files)
        logger.info(
            "Unexpected error occurred while validating one or more of the csv files. "
            "See %s",
            errors_file,
        )
        return 1

    has_errors = False
    for vf in validated_files:
        if vf.has_errors():
            has_errors = True
            if vf.has_manifest_errors():
                vf.preview_manifest_errors(10)
            else:
                vf.preview_validation_errors(10)

    if has_errors:
        errors_file = config.validation_results_writer.write_errors(validated_files)
        logger.info(
            "\nComplete list of structural errors saved to: %s", errors_file
        )
    else:
        logger.info("All structural checks have passed.")

    if args.warning:
        warnings_file = config.validation_results_writer.write_warnings(validated_files)
        logger.info("Warnings output to: %s", warnings_file)

    if not has_errors and config.qa_enabled:
        logger.info(
            "\nRunning preliminary data consistency (QA) checks on %s files...",
            len(args.files),
        )
        qa_results = config.upload_cli.qa_validated_files(validated_files)
        if _qa_error_count_excluding_duplicate_records(qa_results) > 0:
            qa_results.preview_errors(10)
            qa_file = config.validation_results_writer.write_qa_results(qa_results)
            logger.info("\nComplete list of qa errors saved to: %s", qa_file)
            return 1

    return 1 if has_errors else 0


# Usage:
# run_vtcmd('image03_sourcedata.pet.pet.complete_records.csv', 'image03_sourcedata.pet.pet/')
def run_vtcmd_realtime(csv_file, manifest_dir, log_dir=None):
    """Validate a records CSV via the nda-tools Python API (same path as ``vtcmd``)."""
    try:
        import NDATools
        from NDATools.Configuration import ClientConfiguration
    except ImportError:
        print(
            "nda-tools is not installed for this Python environment; "
            "install it (e.g. uv sync).",
            file=sys.stderr,
        )
        return 127

    args = _build_vtcmd_args(csv_file, manifest_dir, log_dir=log_dir)
    nda_password = os.environ.get("NDA_PASSWORD", "").strip()

    try:
        NDATools.init(args, NDATools.NDA_TOOLS_VTCMD_LOGS_FOLDER)
        config = ClientConfiguration(args)
        if nda_password:
            config.password = nda_password
        return _run_vtcmd_validate(args, config)
    except Exception as e:
        print(f"Error running vtcmd validation: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    # command line interface parse
    parser = generate_parser()
    args = parser.parse_args()

    records_sanity_check(args.parent)
    sys.exit(cli(args.parent))

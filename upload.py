#! /usr/bin/env python3

"""
NDA BIDS NDA upload tool

Created  03/09/2020  Natalie Alton (altonn@ohsu.edu)
Modified 03/18/2020  Eric Earl (earl@ohsu.edu)
Modified 05/15/2026  Anthony Galassi (anthony.galassi@nih.gov)
"""

import argparse
import math
import os
import sys
from argparse import Namespace
from datetime import datetime

__doc__ = """
This python command-line tool allows the user a more
automated upload process to the NDA production environment
using the nda-tools Python API (same behavior as ``vtcmd -b``).
"""


def generate_parser():

    parser = argparse.ArgumentParser(prog="upload.py", description=__doc__)
    parser.add_argument(
        "-c",
        "--collection",
        dest="collection_id",
        metavar="COLLECTION_ID",
        type=int,
        required=True,
        help=("The collection ID that files are being uploaded to."),
    )
    parser.add_argument(
        "-s",
        "--source",
        "-p",
        "--parent",
        dest="source",
        metavar="SOURCE_DIR",
        type=str,
        required=True,
        help=(
            "Path to the folder that were prepared for upload. "
            'Folder should be of the format: ".../ndastructure_type.class.subset" '
            'containing folders called "sub-subject_ses-session.type.class.subset" '
            'where "ndastructure" is fmriresults01 or imagingcollection01, '
            '"subject" is the BIDS subject ID/participant label, '
            '"session" is the BIDS session ID, "type" is either "inputs" or '
            '"derivatives", "class" is "anat", "dwi", "fmap", "func", or something '
            'similar, and "subset" is the user-defined "data subset type".'
            "For example: "
            ".../imagingcollection01_inputs.anat.T1w/sub-NDARABC123_ses-baseline.inputs.anat.T1w"
        ),
    )
    return parser


def input_checks():

    # command line interface parse
    parser = generate_parser()
    args = parser.parse_args()

    # check if args.source is a directory
    if not os.path.isdir(args.source):
        print(args.source + " is not a directory!  Exiting...")
        sys.exit(1)
    else:
        source = os.path.abspath(os.path.realpath(args.source))

    basename = os.path.basename(source)
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
        sys.exit(2)

    if file_config.count(".") != 2:
        print(
            file_config
            + " is an improper parent folder naming convention.  The parent folder MUST only contain two periods total.  Exiting..."
        )
        sys.exit(3)
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
        sys.exit(4)

    if subsets.count("_") != 0:
        print(
            subsets
            + " is not a valid entry for section Y.  Section Y MUST have no underscores.  Improper parent folder name.  Exiting..."
        )
        sys.exit(5)

    problem_child_flag = False

    for root, dirs, files in os.walk(source):
        if root == source:
            for directory in dirs:
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
        sys.exit(6)

    try:
        import NDATools  # noqa: F401
    except ImportError:
        print(
            "nda-tools is not installed for this Python environment; "
            "install it (e.g. uv sync). Exiting...",
            file=sys.stderr,
        )
        sys.exit(7)


def _read_nonempty_lines(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def _build_upload_args(
    records_batch,
    source,
    collection_id,
    title,
    description,
    associated_dirs,
):
    """Arguments matching ``vtcmd`` upload invocation (-m, -l, -c, -t, -d, -b)."""
    nda_user = (
        os.environ.get("NDA_USERNAME") or os.environ.get("NDA_TOOLS_USERNAME") or ""
    ).strip() or None
    return Namespace(
        files=[records_batch],
        listDir=associated_dirs,
        manifestPath=[source],
        warning=False,
        buildPackage=True,
        collectionID=collection_id,
        description=description,
        title=title,
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
        log_dir=None,
    )


def _run_upload_batch(
    records_batch,
    source,
    collection_id,
    title,
    description,
    folders_batch,
):
    """Validate a batch CSV and submit via nda-tools (``vtcmd -b`` equivalent)."""
    import logging

    try:
        import NDATools
        from NDATools import authenticate
        from NDATools.Configuration import ClientConfiguration
    except ImportError:
        print(
            "nda-tools is not installed for this Python environment; "
            "install it (e.g. uv sync).",
            file=sys.stderr,
        )
        return 127

    associated_dirs = _read_nonempty_lines(folders_batch)
    args = _build_upload_args(
        records_batch, source, collection_id, title, description, associated_dirs
    )
    nda_password = os.environ.get("NDA_PASSWORD", "").strip()
    logger = logging.getLogger(__name__)

    try:
        NDATools.init(args, NDATools.NDA_TOOLS_VTCMD_LOGS_FOLDER)
        config = ClientConfiguration(args)
        if nda_password:
            config.password = nda_password
        if not config.is_authenticated():
            authenticate(config)

        validated_files = config.upload_cli.validate(args.files, args.manifestPath)

        if any(vf.system_error() for vf in validated_files):
            errors_file = config.validation_results_writer.write_errors(validated_files)
            logger.error(
                "Unexpected error occurred while validating one or more of the csv files. "
                "See %s",
                errors_file,
            )
            return 1

        has_errors = any(vf.has_errors() for vf in validated_files)
        if has_errors:
            for vf in validated_files:
                if vf.has_errors():
                    if vf.has_manifest_errors():
                        vf.preview_manifest_errors(10)
                    else:
                        vf.preview_validation_errors(10)
            errors_file = config.validation_results_writer.write_errors(validated_files)
            logger.error(
                "Validation failed for %s. Errors saved to: %s",
                records_batch,
                errors_file,
            )
            return 1

        submission = config.upload_cli.submit(
            validated_files,
            collection_id,
            title,
            description,
            associated_dirs,
        )
        print(
            "\nYou have successfully completed uploading files for submission {} "
            "with status: {}".format(submission.id, submission.status.value)
        )
        return 0
    except Exception as e:
        print(f"Error running NDA upload: {e}", file=sys.stderr)
        return 1


def nda_vt():

    # command line interface parse
    parser = generate_parser()
    args = parser.parse_args()

    source = os.path.abspath(args.source)
    basename = os.path.basename(source)

    _, data_subset = basename.split("_", 1)
    complete_csv = source + ".complete_records.csv"

    with open(complete_csv) as f:
        all_records = f.readlines()

    max_batch_size = 500  # @TODO this needs to become an integer input defaulted to 500
    total = (
        len(all_records) - 2
    )  # minus two because of two header lines in the complete records file
    count = int(math.ceil(float(total) / max_batch_size))
    upload_record = source + ".uploaded_" + data_subset + ".upload"

    with open(upload_record, "a+") as upload_file:
        file_list = [line.rstrip() for line in upload_file]

        for i in range(1, count + 1):
            batchname = "_".join([str(total), str(max_batch_size), str(i)])

            description = basename + ".batch_" + batchname
            records_batch = source + ".records_" + batchname + ".csv"
            folders_batch = source + ".folders_" + batchname + ".txt"

            if records_batch in file_list:
                print(
                    "WARNING: "
                    + records_batch
                    + " appears in "
                    + upload_record
                    + " so may already have been uploaded to the NDA."
                )
                continue

            print(datetime.now(), "Uploading:", description)
            upload_rc = _run_upload_batch(
                records_batch,
                source,
                args.collection_id,
                description,
                description,
                folders_batch,
            )
            if upload_rc != 0:
                print(
                    f"Upload failed for {records_batch} (exit {upload_rc}). Exiting.",
                    file=sys.stderr,
                )
                sys.exit(upload_rc)

            upload_file.write(records_batch + "\n")

    upload_file.close()


if __name__ == "__main__":
    input_checks()
    nda_vt()
    sys.exit(0)

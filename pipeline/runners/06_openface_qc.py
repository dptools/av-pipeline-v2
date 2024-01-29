#!/usr/bin/env python

import sys
from pathlib import Path

file = Path(__file__).resolve()
parent = file.parent
root = None
for parent in file.parents:
    if parent.name == "av-pipeline-v2":
        root = parent
sys.path.append(str(root))

# remove current directory from path
try:
    sys.path.remove(str(parent))
except ValueError:
    pass

import logging
from typing import Optional, List

from rich.logging import RichHandler
import pandas as pd

from pipeline import orchestrator, data
from pipeline.helpers import utils, db
from pipeline.helpers.timer import Timer
from pipeline.models.openface_qc import OpenfaceQC

MODULE_NAME = "openface_qc"

logger = logging.getLogger(MODULE_NAME)
logargs = {
    "level": logging.DEBUG,
    # "format": "%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s",
    "format": "%(message)s",
    "handlers": [RichHandler(rich_tracebacks=True)],
}
logging.basicConfig(**logargs)

console = utils.get_console()


def get_file_to_process(config_file: Path, study_id: str) -> Optional[Path]:
    sql_query = f"""
        SELECT of_processed_path
        FROM openface AS of
        INNER JOIN video_streams vs USING (vs_path)
        INNER JOIN (
            SELECT decrypted_files.destination_path, interview_files.interview_file_tags
            FROM interview_files JOIN decrypted_files
            ON interview_files.interview_file = decrypted_files.source_path
        ) AS if
        ON vs.video_path = if.destination_path
        WHERE of_processed_path not in (
            SELECT of_processed_path FROM openface_qc
        ) AND vs.video_path IN (
            SELECT destination_path FROM decrypted_files
            JOIN interview_files ON interview_files.interview_file = decrypted_files.source_path
            JOIN interviews USING (interview_path)
            WHERE interviews.study_id = '{study_id}'
        )
        ORDER BY RANDOM()
        LIMIT 1;
    """

    of_processed_path = db.fetch_record(config_file=config_file, query=sql_query)

    if of_processed_path is None:
        return None

    return Path(of_processed_path)


def openface_qc(of_processed_path: Path) -> OpenfaceQC:
    """
    Function to perform quality control on OpenFace output.

    Args:
        of_processed_path (str): Path containing the OpenFace output.

    Returns:
        OpenfaceQC: Object containing the results of the quality control.
    """

    openface_csv_path = of_processed_path.glob("*.csv")

    csv_paths: List[Path] = []
    for path in openface_csv_path:
        csv_paths.append(Path(path))

    if len(csv_paths) == 0:
        logger.error(f"No CSV files found in {of_processed_path}")
        raise FileNotFoundError(f"No CSV files found in {of_processed_path}")
    if len(csv_paths) > 1:
        logger.error(f"Multiple CSV files found in {of_processed_path}")
        raise FileNotFoundError(f"Multiple CSV files found in {of_processed_path}")

    df = pd.read_csv(csv_paths[0], on_bad_lines="warn")

    faces_count = df["face_id"].nunique()
    frames_count = df.shape[0]

    sucessful_frames_count = df[df["success"] == 1].shape[0]
    sucessful_frames_percentage = sucessful_frames_count / frames_count * 100

    success_df = df[df["success"] == 1]
    successful_frames_confidence_mean = success_df["confidence"].mean()
    successful_frames_confidence_std = success_df["confidence"].std()
    successful_frames_confidence_median = success_df["confidence"].median()

    passed = True
    # Fail if less than 50% of frames are successful
    if sucessful_frames_percentage < 50:
        passed = False

    return OpenfaceQC(
        of_processed_path=of_processed_path,
        faces_count=faces_count,
        frames_count=frames_count,
        sucessful_frames_count=sucessful_frames_count,
        sucessful_frames_percentage=sucessful_frames_percentage,
        successful_frames_confidence_mean=successful_frames_confidence_mean,
        successful_frames_confidence_std=successful_frames_confidence_std,
        successful_frames_confidence_median=successful_frames_confidence_median,
        passed=passed,
    )


def log_openface_qc(config_file: Path, openface_qc_result: OpenfaceQC) -> None:
    query = openface_qc_result.to_sql()

    db.execute_queries(config_file=config_file, queries=[query], show_commands=True)


if __name__ == "__main__":
    config_file = utils.get_config_file_path()
    utils.configure_logging(
        config_file=config_file, module_name=MODULE_NAME, logger=logger
    )

    console.rule(f"[bold red]{MODULE_NAME}")
    logger.info(f"Using config file: {config_file}")

    config_params = utils.config(config_file, section="general")
    study_id = config_params["study"]

    counter = 0

    logger.info("[bold green]Starting openface_qc loop...", extra={"markup": True})

    while True:
        # Get file to process
        file_to_process = get_file_to_process(
            config_file=config_file, study_id=study_id
        )

        if file_to_process is None:
            # Log if any files were processed
            if counter > 0:
                data.log(
                    config_file=config_file,
                    module_name=MODULE_NAME,
                    message=f"Ran OpenFace QC on {counter} files.",
                )
                counter = 0
                streams_counter = 0

            # Snooze if no files to process
            orchestrator.snooze(config_file=config_file)
            continue

        counter += 1
        logger.info(
            f"[cyan]Running OpenFace QC on {file_to_process.stem}...",
            extra={"markup": True},
        )

        with Timer() as timer:
            openface_qc_result = openface_qc(of_processed_path=file_to_process)

        openface_qc_result.ofqc_process_time = timer.duration
        log_openface_qc(config_file=config_file, openface_qc_result=openface_qc_result)
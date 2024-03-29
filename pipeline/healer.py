"""
Attemps to self-heal the pipeline by removing stale data
"""

import logging
from pathlib import Path

from pipeline.helpers import cli, db, utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def self_heal_is_enabled(config_file: Path) -> bool:
    """
    Checks if self-healing is enabled in the configuration file.

    Args:
        config_file (Path): The path to the configuration file.

    Returns:
        bool: True if self-healing is enabled, False otherwise.
    """
    general_params = utils.config(path=config_file, section="general")
    self_heal = bool(general_params["self_heal"])
    return self_heal


def remove_pdf_report(interview_name: str, config_file: Path) -> None:
    """
    Removes the PDF report from the database, if self-healing is enabled.

    Args:
        interview_name (str): The interview name.
        config_file (Path): The path to the configuration file.

    Returns:
        None
    """
    logger.info(f"Self-healing: PDF report for {interview_name} is stale.")

    if self_heal_is_enabled(config_file=config_file) is False:
        logger.info("Self-healing is disabled. Ignoring...")
        return

    query = f"""
        DELETE FROM
            pdf_reports
        WHERE
            interview_name = '{interview_name}'
    """

    logger.info(
        f"Self-healing: Purging records for {interview_name} from pdf_reports..."
    )
    db.execute_queries(config_file=config_file, queries=[query])


def set_report_generation_not_possible(
    config_file: Path,
    interview_name: str,
    reason: str,
) -> None:
    """
    Sets the report generation status to 'not possible' in the database.

    Args:
        config_file (Path): The path to the configuration file.
        interview_name (str): The interview name.
        reason (str): The reason why the report generation is not possible.

    Returns:
        None
    """
    logger.info(
        f"Self-healing: Report generation for {interview_name} is not possible."
    )
    logger.info(f"Self-healing: Reason: {reason}")

    if self_heal_is_enabled(config_file=config_file) is False:
        logger.info("Self-healing is disabled. Ignoring...")
        return

    query = f"""
        UPDATE
            load_openface
        SET
            lof_report_generation_possible = False,
            lof_notes = '{reason}'
        WHERE
            interview_name = '{interview_name}'
    """

    db.execute_queries(
        config_file=config_file,
        queries=[query],
        show_commands=False,
        silent=True,
    )
    logger.info(f"Self-healing: Updated report generation status for {interview_name}.")


def clean_openface(
    config_file: Path,
    openface_dir: Path,
) -> None:
    """
    Cleans the OpenFace directory for the given interview, removing all data,
    clearing data from DB, if self-healing is enabled.

    Args:
        config_file (Path): The path to the configuration file.
        openface_dir (Path): The path to the OpenFace directory.

    Returns:
        None
    """
    logger.info(f"Self-healing: OpenFace data on {openface_dir} is inconsistent.")

    if self_heal_is_enabled(config_file=config_file) is False:
        logger.info("Self-healing is disabled. Ignoring...")
        return

    query = f"""
        DELETE FROM
            openface
        WHERE
            of_processed_path = '{openface_dir}';
    """

    db.execute_queries(config_file=config_file, queries=[query])
    logger.info(f"Self-healing: Purged records for {openface_dir} from openface.")

    # Remove OpenFace directory
    if openface_dir.exists():
        logger.info(f"Self-healing: Removing OpenFace directory for {openface_dir}.")
        cli.remove_directory(path=openface_dir)
    else:
        logger.info(f"Self-healing: OpenFace directory {openface_dir} does not exist.")
        logger.info("Self-healing: Skipping directory removal.")

    logger.info(f"Self-healing: OpenFace data on {openface_dir} has been cleaned.")

import logging
import subprocess
import sys
from typing import Callable, Optional


def get_repo_root() -> str:
    """
    Returns the root directory of the current Git repository.

    Uses the command `git rev-parse --show-toplevel` to get the root directory.
    """
    repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    repo_root = repo_root.decode("utf-8").strip()
    return repo_root


def check_if_running(process_name: str) -> bool:
    """
    Check if a process with the same path is running in the background.

    Args:
        process_name (str): The name of the process to check.

    Returns:
        bool: True if the process is running, False otherwise.
    """
    command = f"ps -ef | grep -v grep | grep -c {process_name}"
    result = subprocess.run(command, stdout=subprocess.PIPE, shell=True)
    num_processes = int(result.stdout.decode("utf-8"))
    return num_processes > 0


def get_number_of_running_processes(process_name: str) -> int:
    """
    Returns the number of instances of a process running with the given name.

    Args:
        process_name (str): The name of the process to search for.

    Returns:
        int: The number of instances of the process running.
    """
    # Get the number of instances of the process running
    command_array = [
        "ps",
        "-ef",
        "|",
        "grep",
        process_name,
        "|",
        "grep",
        "-v",
        "grep",
        "|",
        "wc",
        "-l",
    ]

    # Run the command
    output = execute_commands(
        command_array=command_array,
        shell=True,
    )

    # Get the number of processes
    num_processes = int(output.stdout.decode("utf-8"))

    return num_processes


def execute_commands(
    command_array: list,
    shell: bool = False,
    logger: Optional[logging.Logger] = None,
    on_fail: Callable = lambda: sys.exit(1),
) -> subprocess.CompletedProcess:
    """
    Executes a command and returns the result.

    Args:
        command_array (list): The command to execute as a list of strings.
        shell (bool, optional): Whether to execute the command in a shell. Defaults to False.
        logger (Optional[logging.Logger], optional): The logger to use for logging. Defaults to None.
        on_fail (Callable, optional): The function to call if the command fails. Defaults to lambda: sys.exit(1).

    Returns:
        subprocess.CompletedProcess: The result of the command execution.

    """

    if logger is None:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

    logger.debug("Executing command:")
    # cast to str to avoid error when command_array is a list of Path objects
    command_array = [str(x) for x in command_array]

    if logger:
        logger.debug(" ".join(command_array))

    if shell:
        result = subprocess.run(
            " ".join(command_array),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
    else:
        result = subprocess.run(
            command_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    if result.returncode != 0:
        logger.error("=====================================")
        logger.error("Command: " + " ".join(command_array))
        logger.error("=====================================")
        logger.error("stdout:")
        logger.error(result.stdout.decode("utf-8"))
        logger.error("=====================================")
        logger.error("stderr:")
        logger.error(result.stderr.decode("utf-8"))
        logger.error("=====================================")
        logger.error("Exit code: " + str(result.returncode))
        logger.error("=====================================")

        if on_fail:
            on_fail()

    return result

import subprocess
from langchain.tools import tool


ALLOWED_COMMANDS = [
    "ls",
    "dir",
    "pwd",
    "echo"
]


@tool
def run_terminal_command(command: str) -> str:
    """
    Execute safe terminal commands.
    """

    if not command or not command.strip():
        return "Command cannot be empty"

    base = command.split()[0]

    if base not in ALLOWED_COMMANDS:
        return "Command not allowed"

    try:

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout

        return result.stderr or result.stdout or f"Command exited with code {result.returncode}"

    except Exception as e:
        return str(e)
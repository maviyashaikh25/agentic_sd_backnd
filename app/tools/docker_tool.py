import subprocess
from langchain.tools import tool


@tool
def run_docker_container(image_name: str) -> str:
    """
    Run Docker container.
    """

    try:

        result = subprocess.run(
            ["docker", "run", "-d", image_name],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()

        return result.stderr or result.stdout or f"Docker exited with code {result.returncode}"

    except Exception as e:
        return str(e)
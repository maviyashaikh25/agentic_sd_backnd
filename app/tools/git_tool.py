import subprocess
from langchain.tools import tool


@tool
def git_commit(message: str) -> str:
    """
    Commit current changes to git.
    """

    try:

        subprocess.run(["git", "add", "."], check=True)

        subprocess.run(
            ["git", "commit", "-m", message],
            check=True
        )

        return "Git commit successful"

    except Exception as e:
        return str(e)
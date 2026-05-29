import os
import subprocess
import sys
import tempfile
from langchain.tools import tool


@tool
def execute_python(code: str) -> str:
    """
    Execute Python code safely.
    """

    temp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=".py",
            delete=False,
            mode="w",
            encoding="utf-8"
        ) as temp_file:

            temp_file.write(code)

            temp_path = temp_file.name

        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return result.stdout

        return result.stderr or result.stdout or f"Python exited with code {result.returncode}"

    except Exception as e:
        return str(e)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
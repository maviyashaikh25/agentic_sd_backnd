from pathlib import Path
from langchain.tools import tool


@tool
def scan_project_structure(project_path: str) -> str:
    """
    Scan folder structure.
    """

    path = Path(project_path)

    if not path.exists():
        return "Project path does not exist"

    output = []

    for item in sorted(path.rglob("*")):

        output.append(str(item))

    return "\n".join(output)
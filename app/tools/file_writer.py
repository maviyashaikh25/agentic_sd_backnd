from pathlib import Path
from langchain.tools import tool


BASE_DIR = Path("projects_generated")


@tool
def write_file(file_path: str, content: str) -> str:
    """
    Create or overwrite a file.
    """

    base_dir = BASE_DIR.resolve()
    full_path = (base_dir / file_path).resolve()

    if base_dir not in full_path.parents and full_path != base_dir:
        return "Invalid file path"

    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"File written successfully: {full_path}"
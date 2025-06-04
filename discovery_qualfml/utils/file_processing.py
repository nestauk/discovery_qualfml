import json
import pandas as pd
from typing import Union


def extract_text_from_file(file_path: str) -> str:
    """
    Extract plain text content from a file of type .txt, .docx, .vtt, or .csv.

    Supported file types:
      - .txt: reads the whole file as a UTF-8 text string.
      - .docx: extracts all paragraphs and joins them with newline characters.
      - .vtt: reads subtitle files, removing metadata lines and timestamps.
      - .csv: reads the first column and joins all non-null entries with newlines.

    Args:
        file_path (str): The path to the input file.

    Returns:
        str: The full text content extracted from the file.

    Raises:
        ValueError: If the file extension is unsupported.
    """
    import docx

    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file_path.endswith(".vtt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return "\n".join(
                [line.strip() for line in f.readlines() if not line.strip().startswith(("WEBVTT", "00:", "-->"))]
            )
    elif file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
        return "\n".join(df.iloc[:, 0].dropna().astype(str))
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


def save_json(obj: Union[dict, list], path: str) -> None:
    """
    Save a Python dictionary or list to a JSON file with UTF-8 encoding.

    Args:
        obj (Union[dict, list]): The data to save.
        path (str): The file path where the JSON should be saved.

    Returns:
        None
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

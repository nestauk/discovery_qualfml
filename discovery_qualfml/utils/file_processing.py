from docx import Document
import io
import pandas as pd
from pathlib import Path
from typing import Union, Optional
import uuid


def extract_text_from_docx(decoded_bytes: bytes) -> str:
    """
    Extract text content from a .docx file.

    Args:
        decoded_bytes (bytes): The decoded bytes of the .docx file.

    Returns:
        str: Extracted plain text with paragraphs separated by newlines.
    """
    doc = Document(io.BytesIO(decoded_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_txt(decoded_bytes: bytes) -> str:
    """
    Extract text content from a .txt file.

    Args:
        decoded_bytes (bytes): The decoded bytes of the .txt file.

    Returns:
        str: Extracted plain text.
    """
    return decoded_bytes.decode("utf-8")


def extract_text_from_vtt(decoded_bytes: bytes) -> str:
    """
    Extract text content from a .vtt file.

    Args:
        decoded_bytes (bytes): The decoded bytes of the .vtt file.

    Returns:
        str: Extracted plain text with unnecessary lines removed.
    """
    lines = decoded_bytes.decode("utf-8").splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line == "" or "-->" in line or line.isdigit():
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def merge_consecutive_turns(
    df: pd.DataFrame, conv_col: str = "source_file", role_col: str = "attendee", text_col: str = "transcript"
) -> pd.DataFrame:
    """
    Concatenate consecutive lines by the same speaker within a file/conversation.
    This function merges rows in a DataFrame where the speaker (role) and conversation (file) are the same,
    effectively concatenating their text into a single row.

    Args:
        df (pd.DataFrame): DataFrame containing conversation data.
        conv_col (str): Column name for conversation/file identifier.
        role_col (str): Column name for speaker/role identifier.
        text_col (str): Column name for text content to be concatenated.

    Returns:
        pd.DataFrame: DataFrame with consecutive turns merged.
    """
    # Ensure the required columns exist
    required_cols = {conv_col, role_col, text_col}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    # Make sure everything in the text col is a string
    df[text_col] = df[text_col].astype(str)

    # Identify breaks between consecutive rows with different speaker or file
    is_new_group = (df[conv_col] != df[conv_col].shift()) | (df[role_col] != df[role_col].shift())
    group_id = is_new_group.cumsum()

    # Define aggregation: join 'transcript', take first for others
    agg_dict = {col: (" ".join if col == text_col else "first") for col in df.columns}

    # Group and aggregate
    merged = df.groupby(group_id, as_index=False).agg(agg_dict)

    return merged


def extract_role_vtt(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts roles and text from VTT formatted text in a DataFrame.
    Assumes the text column contains strings formatted as "Role: Text".

    Args:
        df (pd.DataFrame): DataFrame containing a 'text' column with VTT formatted strings.

    Returns:
        pd.DataFrame: DataFrame with two new columns: 'role' and 'text'.
    """
    roles = []
    texts = []

    for _idx, row in df.iterrows():
        text_split = row["text"].split(":")
        role = text_split[0]
        text = "".join(text_split[1:]).strip()  # Join the rest of the text after the role
        roles.append(role)
        texts.append(text)

    df["role"] = roles
    df["text"] = texts

    return df


def format_for_topic_modelling(
    session_dir: Union[str, Path], role_col: Optional[str] = None, conv_col: str = "source_file", text_col: str = "text"
) -> pd.DataFrame:
    """
    Formats the data for topic modelling by reading from either a JSONL file or a CSV file.
    If a JSONL file is found, it processes the text files and extracts roles.
    If a CSV file is found, it processes the tabular data and renames the role column if specified.

    Args:
        session_dir (Union[str, Path]): Directory containing input data files.
        role_col (Optional[str]): Name of the role column in tabular data (if present).
        conv_col (str): Column name indicating conversation/file grouping.
        text_col (str): Column name containing text content.

    Returns:
        pd.DataFrame: A DataFrame ready for topic modelling, including UUIDs and role column.
    """

    if Path(f"{session_dir}/raw_text_files.jsonl").exists():
        print("text files")

        transcripts = pd.read_json(f"{session_dir}/raw_text_files.jsonl", lines=True)

        transcripts["text"] = transcripts["text"].str.split("\n")
        transcripts = transcripts.explode("text").reset_index(drop=True)

        transcripts = transcripts[transcripts["text"] != "WEBVTT"]

        # A UUID is needed in order to produce the scatterplot
        transcripts["uuid"] = [str(uuid.uuid4()) for _ in range(len(transcripts))]

        transcripts = extract_role_vtt(transcripts)

    elif Path(f"{session_dir}/raw_combined_data.csv").exists():
        print("tabular data")
        transcripts = pd.read_csv(f"{session_dir}/raw_combined_data.csv")

        # may need to create a UUID here if that hasn't been done

    else:
        print("error")

    if text_col:
        transcripts = transcripts[transcripts[text_col].fillna("").str.split().str.len() >= 4]
    else:
        transcripts = transcripts[transcripts["text"].fillna("").str.split().str.len() >= 4]

    return transcripts

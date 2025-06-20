import base64

from io import StringIO
import datetime
import uuid

import pandas as pd

from discovery_qualfml import PROJECT_DIR


def get_or_create_output_dir(session_id: str) -> str:
    """
    Returns the output directory for a session, creating it if needed.

    Args:
        session_id (str): Unique identifier for the session.

    Returns:
        str: Path to the output directory as a string.
    """
    output_dir = PROJECT_DIR / "outputs" / session_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


def read_data(contents: str) -> pd.DataFrame:
    """
    If you have used an upload box to pick a csv file, you will
    need this logic to read in the csv as a pandas dataframe (Dash can't pass pandas dataframes between callbacks)

    Args:
        contents (str): Base64-encoded string from Dash upload component.

    Returns:
        pd.DataFrame: DataFrame created by reading the uploaded CSV file.
    """
    _, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(StringIO(decoded.decode("utf-8")))
    return df


def make_session_id() -> str:
    """Make a unique session ID based on the current timestamp and a UUID."""
    timestamp_prefix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp_prefix}_{uuid.uuid4()}"


# def get_data_for_topic_modelling(session_id: str) -> pd.DataFrame:
#     output_dir = get_or_create_output_dir(session_id)

#     combined_path = os.path.join(output_dir, "combined_data.csv")
#     jsonl_path = os.path.join(output_dir, "raw_text_files.jsonl")

#     if os.path.exists(combined_path):
#         return pd.read_csv(combined_path)

#     elif os.path.exists(jsonl_path):
#         records = []
#         with open(jsonl_path, "r", encoding="utf-8") as f:
#             for line in f:
#                 record = json.loads(line)
#                 if isinstance(record, dict) and "filename" in record and "text" in record:
#                     records.append(record)
#         return pd.DataFrame(records)

#     else:
#         raise PreventUpdate

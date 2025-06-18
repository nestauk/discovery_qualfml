from datetime import datetime
import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

import pandas as pd

from discovery_utils.utils.llm import batch_check

from discovery_qualfml import PROJECT_DIR
from discovery_qualfml.utils.dash_utils import get_or_create_output_dir

PROMPT_PATH = PROJECT_DIR / "discovery_qualfml/utils/prompts/research_question_prompt.txt"


def parse_rqs(rq_text: str) -> Dict[str, str]:
    """Given research questions entered as one string,
    split these line by line and return a dict
    that maps an arbitrary ID for each RQ to the text of the question.

    The ID also includes a timestamp because if the user resubmits RQs during
    the Dash session and the index starts again, we need to make sure the results
    for the latest `rq_1` are distinct from the results for the previous `rq_1`.

    Args:
        rq_text (str): One string containing all the RQs.

    Returns:
        Dict[str, str]: Dict mapping an ID to the text of the RQ.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    research_questions = rq_text.strip().splitlines()
    rq_dict = {f"rq_{i + 1}_{timestamp}": q for i, q in enumerate(research_questions)}
    return rq_dict


def format_transcripts(session_id: str, conv_col: str = "source_file", text_col: str = "text") -> Dict[str, str]:
    """
    Load and format transcript data from disk for a given Dash app session.

    This function checks for either JSONL or CSV files in the output directory for the session,
    and returns a dictionary mapping conversation or file IDs to the corresponding full transcript text.

    If a JSONL file (`raw_text_files.jsonl`) exists, it assumes each line contains a dict with
    'filename' and 'text', and maps filenames to their text.

    If a CSV file (`raw_combined_data.csv`) exists, it groups the rows by `conv_col` and joins
    the `text_col` values with newlines to form full conversation transcripts.

    Args:
        session_id (str): The session ID used to determine the output directory path.
        conv_col (str): The name of the column that uniquely identifies each conversation in the CSV file.
                        This will have been set to 'source_file' if not identified by the user on the data upload tab.
        text_col (str, optional): The name of the column containing the text of the transcript. Defaults to 'text'.

    Returns:
        Dict[str, str]: A dictionary mapping conversation or file IDs to full transcript text.
    """
    session_dir = get_or_create_output_dir(session_id)

    if Path(f"{session_dir}/raw_text_files.jsonl").exists():
        print("text files")
        text_data = pd.read_json(f"{session_dir}/raw_text_files.jsonl", lines=True)
        conversation_text_dict = text_data.set_index("filename")["text"].to_dict()

    elif Path(f"{session_dir}/raw_combined_data.csv").exists():
        print("tabular data")
        tabular_data = pd.read_csv(f"{session_dir}/raw_combined_data.csv")
        tabular_data = tabular_data.dropna(subset=[text_col])
        conversation_text_dict = tabular_data.groupby(conv_col)[text_col].agg("\n".join).to_dict()
    else:
        print("error")
        conversation_text_dict = {}

    return conversation_text_dict


def build_question_prompt_dict(
    rq_dict: Dict[str, str], prompt_template_text: str
) -> Dict[str, Dict[str, Union[str, list]]]:
    """
    Constructs the output fields for each RQ.

    Args:
        rq_dict (Dict[str, str]): Mapping of question IDs to question text.
        prompt_template_text (str): The system prompt template, with {question} as a placeholder.

    Returns:
        Dict[str, Dict[str, Union[str, list]]]: A dictionary where each key is a question ID,
            and each value contains a system message and output field definitions.
    """
    prompt_dict = {}
    for k, question in rq_dict.items():
        system_message = prompt_template_text.format(question=question)
        fields = [
            {"name": "answer", "type": "str", "description": "Your answer to the question."},
            {
                "name": "text",
                "type": "List[str]",
                "description": """
             A list of quotes copied exactly as they appear in the transcript.
             Each item must match a verbatim substring from the original transcript.
             If no quotes are found, return an empty list `[]`.
             """,
            },
        ]
        prompt_dict[k] = {"system_message": system_message, "fields": fields}
    return prompt_dict


def run_batch_check(
    conversation_text_dict: Dict[Any, str],
    prompt_dict: Dict[str, Dict[str, Union[str, list]]],
    output_dir: Union[str, Path],
) -> Dict[str, str]:
    """
    Run the batch_check pipeline for each research question on the conversation data.

    Args:
        conversation_text_dict (Dict[Any, str]): Mapping of conversation IDs to full transcript strings.
        prompt_dict (Dict[str, Dict[str, Union[str, list]]]): Dict containing the system message and desired output fields for each RQ.
        output_dir (Union[str, Path]): Directory to write output `.jsonl` files (one per RQ).

    Returns:
        Dict[str, str]: A mapping from research question IDs to their respective output file paths.
    """

    output_paths = {}
    for qid, meta in prompt_dict.items():
        outpath = Path(output_dir) / f"{qid}_output.jsonl"
        processor = batch_check.LLMProcessor(
            model_name="gpt-4o-mini",
            temperature=0,
            output_path=str(outpath),
            system_message=meta["system_message"],
            session_name=qid,
            output_fields=meta["fields"],
        )
        processor.run(conversation_text_dict, batch_size=50, sleep_time=0.5)
        output_paths[qid] = str(outpath)
    return output_paths


def run_batch_check_for_all_rqs(
    rq_text: str,
    conversation_text_dict: Dict[str, str],
    output_dir: str,
    prompt_path: Path = PROMPT_PATH,
) -> Tuple[Dict[str, str], pd.DataFrame]:
    """Brings together the functions above to run batch_check for each RQ.

    Args:
        rq_text (str): Raw research question input string.
        conversation_text_dict (Dict[str, str]): Dictionary mapping conversation IDs to full transcript text.
        output_dir (str): Directory where results (real or mock) are saved.
        prompt_path (Path): Path to the prompt template file.

    Returns:
        Tuple[Dict[str, str], pd.DataFrame]:
            - Dictionary mapping RQ IDs to their output file paths.
            - DataFrame with batch_check results for each conversation and for each RQ.
    """

    rq_dict = parse_rqs(rq_text)

    prompt_template = prompt_path.read_text()

    prompt_dict = build_question_prompt_dict(rq_dict, prompt_template)

    output_paths = run_batch_check(conversation_text_dict, prompt_dict, output_dir)

    return output_paths, rq_dict


def check_quotes_were_in_original(conversation_text_dict: Dict[str, str], df: pd.DataFrame) -> Tuple[List[str], float]:
    """
    Take a df (the output of batch_check for *ONE* RQ) and verify that all quotes returned by the LLM
    can be found in the original data.

    Args:
        conversation_text_dict (Dict[str, str]): Dict containing original transcripts - this was
                            produced by `format_transcripts()`
        df (pd.DataFrame): batch_check output. Must be the output for ONE rq

    Returns:
        Tuple[List[str], float]:
            - A list of quotes that were NOT found in the original conversation text.
            - A float representing the percentage of quotes that were matched.
    """
    df = df.explode("text")

    total_quotes = len(df)

    unmatched_quotes = []

    for _idx, row in df.iterrows():
        if row["text"] in conversation_text_dict[row["id"]]:
            continue
        else:
            print("Quote NOT found in conversation text:")
            print(row["text"])
            unmatched_quotes.append(row["text"])

    accuracy = (total_quotes - len(unmatched_quotes)) / total_quotes * 100
    print(f"Accuracy of quotes found in original text: {accuracy:.2f}%")
    return unmatched_quotes, accuracy


def create_batch_check_output_single_rq(
    conversation_text_dict: Dict[str, str], outdir: str, rq_id: str, rq_dict: Dict[str, str]
) -> pd.DataFrame:
    """
    Once batch_check has been run, this function creates a df output for a single RQ.

    It also uses `check_quotes_were_in_original()` to verify the quotes and filter
    out ones that may have been hallucinated.

    Args:
        conversation_text_dict (Dict[str, str]):
            Dictionary mapping conversation IDs to full transcript text.
        outdir (str):
            Path for the current Dash session directory.
        rq_id (str):
            The ID of the research question.
        rq_dict (Dict[str, str]):
            Dictionary mapping research question IDs to question text.

    Returns:
        pd.DataFrame:
            A DataFrame version of batch_check output for one RQ,
            with any quotes that could not be found in the original text
            filtered out.
    """

    batch_check_output = pd.read_json(os.path.join(outdir, f"{rq_id}_output.jsonl"), lines=True)

    unmatched_quotes, _accuracy = check_quotes_were_in_original(conversation_text_dict, batch_check_output)

    batch_check_output_long = batch_check_output.explode("text")
    print(len(batch_check_output_long))
    batch_check_output_long = batch_check_output_long[~batch_check_output_long["text"].isin(unmatched_quotes)]
    print(len(batch_check_output_long))

    batch_check_output_long["rq"] = rq_dict[rq_id]

    return batch_check_output_long


def create_batch_check_outputs_all_rqs(
    conversation_text_dict: Dict[str, str], outdir: str, rq_dict: Dict[str, str]
) -> pd.DataFrame:
    """Runs the function above (`create_batch_check_output_single_rq()`) for
    all RQs and concatenates the results.

    Args:
        conversation_text_dict (Dict[str, str]): Dict containing original transcripts.
        outdir (str): Path for the current Dash session.
        rq_dict (Dict[str, str]): Dict mapping RQ IDs to question text.

    Returns:
        pd.DataFrame: Dataframe with the batch_check outputs for all RQs.
    """

    rq_ids = rq_dict.keys()

    batch_check_all_rqs = pd.DataFrame()

    for rq_id in rq_ids:
        batch_check_output_long = create_batch_check_output_single_rq(conversation_text_dict, outdir, rq_id, rq_dict)

        batch_check_all_rqs = pd.concat([batch_check_all_rqs, batch_check_output_long], ignore_index=True)

    return batch_check_all_rqs[
        [
            "rq",
            "id",
            "answer",
            "text",
            "timestamp",
            "model",
            "temperature",
        ]
    ]

from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import numpy as np
import pandas as pd

from bertopic import BERTopic
from bertopic.dimensionality import BaseDimensionalityReduction
from bertopic.representation import KeyBERTInspired
from bertopic.representation import MaximalMarginalRelevance
from hdbscan import HDBSCAN
from langchain_core.runnables import Runnable
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from umap import UMAP

from discovery_qualfml import logger, PROJECT_DIR
from discovery_qualfml.utils.topic_modelling_llm_utils import name_topics, get_chain, format_output_df, NameDescription

# TODO: put these in config
MODEL = "gpt-4o-mini"  # use "llama3.2" for local testing
PROVIDER = "azure"  # use "azure" on AWS, use "ollama" for local testing
BASIC_PROMPT_PATH = PROJECT_DIR / "discovery_qualfml/utils/prompts/topic_model_prompt.txt"
LLM_CHAIN = get_chain(
    BASIC_PROMPT_PATH,
    input_vars=["docs", "keywords"],
    output_template=NameDescription,
    provider=PROVIDER,
    model=MODEL,
    temp=0,
)


def embed_docs(
    docs: List[str], model: Optional[SentenceTransformer] = None, save: bool = False, outpath: str = "embeddings.npy"
) -> Tuple[List[str], np.ndarray]:
    """Embeds a list of documents using a SentenceTransformer model.
    Saves these to the local path specified as `outpath`.

    Args:
        docs (List[str]): List of text documents
        model (Optional[SentenceTransformer], optional): SentenceTransformer model to use. Defaults to None.
        save (bool, optional): Do you want the embeddings saved as `npy`? Defaults to False.
        outpath (str, optional): Local path for saving the embeddings - only used if `save==True`. Defaults to "embeddings.npy".

    Returns:
        Tuple[List[str], np.ndarray]: The input documents and their embeddings.
    """
    logger.info("Embedding user messages...")

    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")

    embeddings = model.encode(docs, show_progress_bar=True)
    if save:
        np.save(outpath, embeddings)
    return docs, embeddings


def init_topic_model(
    stop_words: Union[str, List[str]],
    min_cluster_size: int,
    hdbscan_selection_method: str,
    embedding_model: SentenceTransformer,
    seed: int = 42,
    empty_reduction: bool = False,
    nr_topics: Optional[int] = None,
) -> Tuple[BERTopic, TfidfVectorizer, Dict[str, Union[KeyBERTInspired, MaximalMarginalRelevance]]]:
    """
    Initializes and returns a BERTopic model along with vectorizer and representation models.
    The representation model and vectorizer can be reused later for noise reduction.

    Args:
        stop_words (Union[str, List[str]]): Stopwords to use for the vectorizer
        min_cluster_size (int): The smallest size of a cluster with HDBSCAN
        hdbscan_selection_method (str): "eom" or "leaf"
        embedding_model (SentenceTransformer): SentenceTransformer model to use for embeddings
        seed (int, optional): Random seed. Defaults to 42.
        empty_reduction (bool, optional): You can specify an empty reduction model
            if you have already reduced the embeddings. Defaults to False and allowing BERTopic to do the reduction.
        nr_topics (Optional[int], optional): If you want to specify the number of topics, you can do so here. Defaults to None.

    Returns:
        Tuple[BERTopic, TfidfVectorizer, Dict[str, Union[KeyBERTInspired, MaximalMarginalRelevance]]]:
            BERTopic model, vectorizer model, and representation models
    """

    if empty_reduction:
        reduction_model = BaseDimensionalityReduction()
    else:
        reduction_model = UMAP(
            n_neighbors=15,
            n_components=50,
            min_dist=0.1,
            metric="cosine",
            random_state=seed,
        )

    hdbscan_model = HDBSCAN(
        min_samples=5,
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        cluster_selection_method=hdbscan_selection_method,
        prediction_data=True,
    )

    vectorizer_model = TfidfVectorizer(
        stop_words=stop_words,
        min_df=1,
        max_df=0.85,
        ngram_range=(1, 3),
    )

    # KeyBERT
    keybert_model = KeyBERTInspired()

    # MMR
    mmr_model = MaximalMarginalRelevance(diversity=0.3)

    # All representation models
    representation_model = {
        "KeyBERT": keybert_model,
        "MMR": mmr_model,
    }

    if nr_topics is not None:
        topic_model = BERTopic(
            # Pipeline models
            embedding_model=embedding_model,
            umap_model=reduction_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            representation_model=representation_model,
            nr_topics=nr_topics,
            # Hyperparameters
            top_n_words=10,
            verbose=True,
            calculate_probabilities=True,
        )
    else:
        topic_model = BERTopic(
            # Pipeline models
            embedding_model=embedding_model,
            umap_model=reduction_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            representation_model=representation_model,
            # Hyperparameters
            top_n_words=10,
            verbose=True,
            calculate_probabilities=True,
        )

    return topic_model, vectorizer_model, representation_model


def get_topics_and_summaries(
    df: pd.DataFrame,
    text_col: str,
    num_topics: int = 10,
    model: str = MODEL,  # just for naming columns - not used as an actual model
    llm_chain: Runnable = LLM_CHAIN,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Performs topic modelling and summarization on the dataset uploaded by the user,
    with the maximum number of topics defined in the input in the topic modelling page of the app.

    The dataframe `user_messages` is so called because there is a callback in the app that filters the original
    dataframe to just rows where `role=='USER'`. This is not ideal long term.

    This function:
    - embeds the documents
    - fits a BERTopic model to identify topics,
    - reduces the noise cluster
    - uses a llm to generate names and descriptions for the topics
    - creates a datafrme ready for visualisation, with 2D UMAP projections of the embeddings

    Args:
        df (pd.DataFrame): DataFrame containing user text data.
        text_col (str): Name of the column in `user_messages` that contains the text data.
        num_topics (int, optional): Desired number of topics for the model to extract. Defaults to 10.
        model (str, optional): Name of the model to use for naming columns in the output.
        llm_chain (Runnable, optional): LLM chain for generating topic names and descriptions. Defaults to a pre-defined chain.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - `df_vis`: DataFrame containing 2D UMAP projections, topic assignments, topic names, and merged original data. One row
                per document (document = e.g. a user message or a line from a transcript).
            - `topic_lookup`: DataFrame containing topic metadata, including topic number, name, and LLM-generated descriptions. One row per topic.
    """
    # Drop rows where the text column is not a string or is missing
    df = df[df[text_col].apply(lambda x: isinstance(x, str))]

    # Convert all values to string just to be extra safe (in case of mixed types)
    df[text_col] = df[text_col].astype(str)

    docs = df[text_col].tolist()

    docs, embeddings = embed_docs(docs, save=False)

    topic_model, vectorizer_model, representation_model = init_topic_model(
        stop_words="english",
        min_cluster_size=10,
        hdbscan_selection_method="leaf",
        embedding_model="all-MiniLM-L6-v2",
        seed=42,
        empty_reduction=False,
        nr_topics=num_topics,
    )

    topics, _probs = topic_model.fit_transform(docs, embeddings)

    new_topics = topic_model.reduce_outliers(docs, topics, strategy="embeddings")

    topic_model.update_topics(
        docs,
        topics=new_topics,
        top_n_words=10,
        n_gram_range=(1, 3),
        vectorizer_model=vectorizer_model,
        ctfidf_model=None,
        representation_model=representation_model,
    )

    summary_info = topic_model.get_topic_info()

    results = name_topics(
        summary_info,
        llm_chain,
        input_variable_dict={"docs": "Representative_Docs", "keywords": "Representation"},
        topic_label_col="Topic",
    )

    topic_info = format_output_df(
        topic_info=summary_info, results=results, output_fields=["name", "description"], model_name=model
    )

    umap_2d = UMAP(random_state=42, n_components=2)
    embeddings_2d = umap_2d.fit_transform(embeddings)

    topic_lookup = topic_info[["Topic", "Name", "Representation", f"{model}_name", f"{model}_description"]]

    df_vis = pd.DataFrame(embeddings_2d, columns=["x", "y"])
    df_vis["topic"] = new_topics
    df_vis = df_vis.merge(topic_lookup, left_on="topic", right_on="Topic", how="left")
    df_vis["doc"] = docs

    df_vis = pd.merge(
        df,
        df_vis,
        left_on=text_col,
        right_on="doc",
        how="outer",
    )

    return df_vis, topic_lookup

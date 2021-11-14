import logging
from functools import partial
from typing import Optional

import pandas as pd
import typer
from bokeh.plotting import output_file as bokeh_output_file
from bokeh.plotting import save
from embedding_lenses.data import uploaded_file_to_dataframe
from embedding_lenses.dimensionality_reduction import (
    get_tsne_embeddings,
    get_umap_embeddings,
)
from embedding_lenses.embedding import load_model

from perplexity_lenses.data import (
    documents_df_to_sentences_df,
    hub_dataset_to_dataframe,
)
from perplexity_lenses.engine import (
    DIMENSIONALITY_REDUCTION_ALGORITHMS,
    DOCUMENT_TYPES,
    EMBEDDING_MODELS,
    LANGUAGES,
    SEED,
    generate_plot,
)
from perplexity_lenses.perplexity import KenlmModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = typer.Typer()


@app.command()
def main(
    dataset: str = typer.Option(
        "mc4", help="The name of the hub dataset or local csv/tsv file."
    ),
    dataset_config: Optional[str] = typer.Option(
        "es",
        help="The configuration of the hub dataset, if any. Does not apply to local csv/tsv files.",
    ),
    dataset_split: Optional[str] = typer.Option(
        "train", help="The dataset split. Does not apply to local csv/tsv files."
    ),
    text_column: str = typer.Option("text", help="The text field name."),
    language: str = typer.Option(
        "es", help=f"The language of the text. Options: {LANGUAGES}"
    ),
    doc_type: str = typer.Option(
        "sentence",
        help=f"Whether to embed at the sentence or document level. Options: {DOCUMENT_TYPES}.",
    ),
    sample: int = typer.Option(1000, help="Maximum number of examples to use."),
    dimensionality_reduction: str = typer.Option(
        DIMENSIONALITY_REDUCTION_ALGORITHMS[0],
        help=f"Whether to use UMAP or t-SNE for dimensionality reduction. Options: {DIMENSIONALITY_REDUCTION_ALGORITHMS}.",
    ),
    model_name: str = typer.Option(
        EMBEDDING_MODELS[0],
        help=f"The sentence embedding model to use. Options: {EMBEDDING_MODELS}",
    ),
    output_file: str = typer.Option(
        "perplexity.html", help="The name of the output visualization HTML file."
    ),
):
    """
    Perplexity Lenses: Visualize text embeddings in 2D using colors to represent perplexity values.
    """
    logger.info("Loading embedding model...")
    model = load_model(model_name)
    dimensionality_reduction_function = (
        partial(get_umap_embeddings, random_state=SEED)
        if dimensionality_reduction.lower() == "umap"
        else partial(get_tsne_embeddings, random_state=SEED)
    )
    logger.info("Loading KenLM model...")
    kenlm_model = KenlmModel.from_pretrained(language)
    logger.info("Loading dataset...")
    if dataset.endswith(".csv") or dataset.endswith(".tsv"):
        df = pd.read_csv(dataset, sep="\t" if dataset.endswith(".tsv") else ",")
        if doc_type.lower() == "sentence":
            df = documents_df_to_sentences_df(df, text_column, sample, seed=SEED)
        df["perplexity"] = df[text_column].map(kenlm_model.get_perplexity)
    else:
        df = hub_dataset_to_dataframe(
            dataset,
            dataset_config,
            dataset_split,
            sample,
            text_column,
            kenlm_model,
            seed=SEED,
            doc_type=doc_type,
        )
    # Round perplexity
    df["perplexity"] = df["perplexity"].round().astype(int)
    logger.info(
        f"Perplexity range: {df['perplexity'].min()} - {df['perplexity'].max()}"
    )
    plot = generate_plot(
        df,
        text_column,
        "perplexity",
        None,
        dimensionality_reduction_function,
        model,
        seed=SEED,
    )
    logger.info("Saving plot")
    bokeh_output_file(output_file)
    save(plot)
    logger.info("Done")


if __name__ == "__main__":
    app()

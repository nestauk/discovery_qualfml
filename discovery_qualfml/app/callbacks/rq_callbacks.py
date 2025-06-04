import os

import dash_bootstrap_components as dbc
import pandas as pd

from dash import ALL
from dash import Input
from dash import Output
from dash import State
from dash import ctx
from dash import dcc
from dash import html
from dash.exceptions import PreventUpdate

from discovery_qualfml.utils.dash_utils import get_or_create_output_dir
from discovery_qualfml.utils.llm_question_answering import *
from discovery_qualfml.utils.llm_summarize import *


def register_rq_callbacks(app):
    @app.callback(
        Output("analysis-results", "children"),
        Output("stored-output-paths", "data"),
        Output("stored-rqs", "data"),
        Output("output-dir", "data"),
        Output("download-btn-container", "children"),
        Input("run-analysis", "n_clicks"),
        State("session-id", "data"),
        State("column-store", "data"),
        State("rq-textarea", "value"),
        State("test-mode-toggle", "value"),
        prevent_initial_call=True,
    )
    def run_analysis(n_clicks, session_id, colinfo, rq_text, test_mode):
        if not (n_clicks and session_id and colinfo and rq_text):
            raise PreventUpdate

        conversation_text_dict = format_transcripts(session_id, colinfo["conv_id"], text_col=colinfo["text"])

        outdir = get_or_create_output_dir(session_id)

        output_paths, rq_dict = run_batch_check_for_all_rqs(
            rq_text=rq_text,
            conversation_text_dict=conversation_text_dict,
            output_dir=outdir,
        )

        batch_check_all_rqs = create_batch_check_outputs_all_rqs(conversation_text_dict, outdir, rq_dict)

        summarize_and_quote_output = generate_summaries_and_quotes(rq_dict, batch_check_all_rqs)

        summarise_output_df = create_final_output_df(rq_dict, conversation_text_dict, summarize_and_quote_output)

        summarise_output_df.reset_index().to_csv(os.path.join(outdir, "summarise_output_df.csv"), index=False)

        create_output_excel(summarise_output_df, outdir)

        btn = dbc.Button("Download Results", id="trigger-download", className="nesta-button")
        alert = dbc.Alert(
            "Test mode: mock outputs" if test_mode else "LLM processing complete!",
            color="info" if test_mode else "success",
        )
        return alert, output_paths, rq_dict, outdir, btn

    @app.callback(
        Output("download-results", "data"),
        Input("trigger-download", "n_clicks"),
        State("output-dir", "data"),
        prevent_initial_call=True,
    )
    def download_excel(n_clicks, outdir):
        path = os.path.join(outdir, "full_summary.xlsx")
        if not (n_clicks and os.path.exists(path)):
            raise PreventUpdate
        return dcc.send_file(path)

    @app.callback(
        Output("analysis-results", "children", allow_duplicate=True),
        Input("output-dir", "data"),
        State("stored-rqs", "data"),
        State("session-id", "data"),
        State("column-store", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def display_results(outdir, rq_dict, session_id, colinfo):
        if not (outdir and rq_dict):
            return ""
        full_summary = pd.read_csv(os.path.join(outdir, "summarise_output_df.csv"))

        # conversation_text_dict = format_transcripts(session_id, colinfo["conv_id"], text_col=colinfo["text"])

        # uuid_col = colinfo["uuid"]
        children = []
        for _, q in rq_dict.items():
            temp = full_summary[full_summary["question"] == q]
            quote_elems = []
            for _, row in temp.iterrows():
                quote_elems.append(
                    html.Div(
                        f"{row['quote']}",
                        id={"type": "quote", "index": row["index"]},
                        className="quote-block",
                        style={
                            "backgroundColor": "#0F294A",
                            "color": "white",
                            "padding": "10px",
                            "fontStyle": "italic",
                            "borderRadius": "5px",
                            "marginBottom": "0.5rem",
                        },
                    ),
                )
            children.append(html.H4(f"RQ: {q}", style={"marginTop": "1rem"}))
            children.append(html.H6("Summary", style={"color": "grey"}))
            children.append(html.P(temp["answer"].iloc[0]))
            children.append(html.H6("Illustrative quotes", style={"color": "grey"}))
            children.append(html.Div(quote_elems))
        return (html.Div(children),)

    @app.callback(
        Output("quote-modal", "is_open"),
        Output("modal-body", "children"),
        Input({"type": "quote", "index": ALL}, "n_clicks"),
        Input("output-dir", "data"),
        State("session-id", "data"),
        State("column-store", "data"),
    )
    def display_conversation(n_list, outdir, session_id, colinfo):
        if not any(n_list):
            raise PreventUpdate
        triggered = ctx.triggered_id
        uid = triggered["index"]

        full_summary = pd.read_csv(os.path.join(outdir, "summarise_output_df.csv"))

        conversation_text_dict = format_transcripts(session_id, colinfo["conv_id"], text_col=colinfo["text"])

        temp_df = full_summary[full_summary["index"] == uid]

        doc_id = temp_df["source"].iloc[0]
        quote = temp_df["quote"].iloc[0]

        def insert_linebreaks(text):
            """Split text by newlines and insert <br> tags."""
            lines = text.split("\n")
            result = []
            for i, line in enumerate(lines):
                result.append(html.Span(line))
                if i < len(lines) - 1:
                    result.append(html.Br())
            return result

        def highlight_quote(transcript_dict, doc_id, highlight_quote):
            full_text = transcript_dict.get(doc_id, "")

            # Find the start index of the quote
            start = full_text.find(highlight_quote)

            if start == -1:
                # Quote not found — return full text unhighlighted
                return [html.Span(full_text)]

            end = start + len(highlight_quote)

            before = full_text[:start]
            after = full_text[end:]

            return insert_linebreaks(before) + [html.Mark(highlight_quote)] + insert_linebreaks(after)

        body = html.Div(
            children=highlight_quote(transcript_dict=conversation_text_dict, doc_id=doc_id, highlight_quote=quote)
        )
        return True, html.Div(body)

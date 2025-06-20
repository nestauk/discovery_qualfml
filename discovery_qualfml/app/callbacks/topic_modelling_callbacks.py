"""Callbacks for topic modelling tab"""

from dash import Dash
from dash import Input
from dash import Output
from dash import State
from dash import dcc
from dash import html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from typing import Any, Dict, List, Tuple, Optional

from discovery_qualfml.utils.dash_utils import get_or_create_output_dir
from discovery_qualfml.utils.topic_modelling import MODEL
from discovery_qualfml.utils.topic_modelling import get_topics_and_summaries
from discovery_qualfml.app.style import NESTA_COLOURS


def register_topic_callbacks(app: Dash) -> None:
    """
    Register all topic modelling-related callbacks to the given Dash app.

    Args:
        app (Dash): The Dash app to register callbacks to.
    """

    # Topic modelling callback
    @app.callback(
        Output("topic-model-status", "children"),
        Output("stored-topic-viz", "data"),
        Output("topic-lookup-table", "data"),
        Output("topic-lookup-table", "columns"),
        Output("topic-results", "style"),
        Input("run-topic-model-btn", "n_clicks"),
        State("num-topics-input", "value"),
        State("column-store", "data"),
        State("session-id", "data"),
        prevent_initial_call=True,
    )
    def run_topic_model(
        n_clicks: int,
        num_topics: int,
        colinfo: Optional[Dict[str, str]],
        session_id: str,
    ) -> Tuple[html.Div, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, str]], Dict[str, str]]:
        """
        Run the topic model and return the status message, visualisation data,
        topic lookup table data, and columns.
        If the model has not been run yet, return an empty state.
        If the model has been run, return the results and a success message.

        Args:
            n_clicks (int): Number of times the button has been clicked.
            num_topics (int): Desired number of topics.
            colinfo (dict): Dictionary of column mappings.
            session_id (str): Unique session identifier.

        Returns:
            Tuple of alert message, topic scatter data, topic lookup table data,
            table column config, and a style dict to display the results.
        """
        if not n_clicks or not num_topics or not session_id:
            raise PreventUpdate
        status_msg = f"Running topic model with {num_topics} topics..."  # noqa

        output_dir = get_or_create_output_dir(session_id)

        # Run topic model
        if colinfo:
            transcripts = pd.read_csv(os.path.join(output_dir, "topic_modelling_data.csv"))
            df_vis, topic_lookup = get_topics_and_summaries(transcripts, colinfo["text"], num_topics)
        else:
            transcripts = pd.read_csv(os.path.join(output_dir, "topic_modelling_data.csv"))
            print(transcripts.head())
            df_vis, topic_lookup = get_topics_and_summaries(transcripts, "text", num_topics)

        # Save lookup
        topic_lookup.to_csv(os.path.join(output_dir, "topic_lookup.csv"), index=False)

        # Prepare table data
        topic_lookup = topic_lookup.rename(
            columns={
                f"{MODEL}_name": "Topic name",
                f"{MODEL}_description": "Description",
                "Representation": "Keywords",
            }
        )[["Topic", "Topic name", "Description", "Keywords"]]

        # **Convert each list of keywords into a single string**:
        topic_lookup["Keywords"] = topic_lookup["Keywords"].apply(
            lambda kws: ", ".join(kws) if isinstance(kws, (list, tuple)) else str(kws)
        )

        table_data = topic_lookup.to_dict("records")
        table_cols = [{"name": c, "id": c} for c in topic_lookup.columns]
        # Show results
        return (
            dbc.Alert(f"Topic model completed with up to {num_topics} topics", color="success"),
            df_vis.to_dict("records"),
            table_data,
            table_cols,
            {"display": "block"},
        )

    # Download CSV callback
    @app.callback(
        Output("download-topic-csv", "data"),
        Input("download-topic-csv-btn", "n_clicks"),
        State("session-id", "data"),
        prevent_initial_call=True,
    )
    def download_topic_csv(n_clicks: int, session_id: str) -> Optional[dcc.send_file]:
        """
        Download the topic lookup CSV file when the button is clicked.

        Args:
            n_clicks (int): Number of times the button has been clicked.
            session_id (str): Unique session identifier.

        Returns:
            Optional[dcc.send_file]: The file to be downloaded, or None if conditions are not met.
        """
        if not n_clicks or not session_id:
            raise PreventUpdate
        path = os.path.join(get_or_create_output_dir(session_id), "topic_lookup.csv")
        if not os.path.exists(path):
            raise PreventUpdate
        return dcc.send_file(path)

    @app.callback(
        Output("scatter-plot", "figure"),
        Input("stored-topic-viz", "data"),
        State("column-store", "data"),
        prevent_initial_call=True,
    )
    def update_scatter_plot(
        data: List[Dict[str, Any]],
        column_info: Dict[str, str],
    ) -> go.Figure:
        """
        Update the scatter plot based on the stored topic visualisation data.

        Args:
            data (List[Dict[str, Any]]): List of dictionaries containing the topic visualisation data.
                                        Dash can't handle dataframes, which is why the data is passed around as a json.
            column_info (Dict[str, str]): Dictionary containing column information for the data.

        Returns:
            go.Figure: The updated scatter plot figure.
        """

        if not data:
            raise PreventUpdate

        if column_info:
            conv_id, role_col, text_col, uuid_col = (
                column_info["conv_id"],
                column_info["role"],
                column_info["text"],
                column_info["uuid"],
            )
        else:
            conv_id = "filename"
            role_col = "role"
            text_col = "text"
            uuid_col = "uuid"

        df = pd.DataFrame(data)

        fig = px.scatter(
            df,
            x="x",
            y="y",
            color=f"{MODEL}_name",
            hover_data=[conv_id, text_col],
            custom_data=[conv_id, text_col, uuid_col],
            color_discrete_sequence=NESTA_COLOURS,
        )

        # Update hovertemplate to show only the text
        fig.update_traces(hovertemplate="<b>%{customdata[1]}</b><extra></extra>")

        fig.update_layout(
            uirevision="scatter-plot",  # Ensure that the zoom level is preserved after you've clicked a point
            xaxis=dict(showticklabels=False, title_text=""),  # Hide x-axis ticks and title
            yaxis=dict(showticklabels=False, title_text=""),  # Hide y-axis ticks and title
            legend_title_text="",  # Hide legend title
            legend=dict(bgcolor="rgba(255,255,255,0.7)", bordercolor="#ccc", borderwidth=1),
            margin=dict(l=10, r=10, t=20, b=10),
            font=dict(family="Century Gothic", size=12),
        )

        return fig

    @app.callback(
        [
            Output("name-display", "children"),
            Output("description-display", "children"),
            Output("conversation-display", "children"),
            Output("text-clean-display", "children"),
        ],
        Input("scatter-plot", "clickData"),
        Input("stored-topic-viz", "data"),
        State("column-store", "data"),
    )
    def update_point_info(
        clickData: Dict[str, Any],
        data: List[Dict[str, Any]],
        column_info: Dict[str, str],
    ) -> Tuple[str, str, str, str]:
        """
        When the user clicks a point on the scatterplot, show information
        about this point in the left panel.

        Args:
            clickData (dict): Click event data from the scatter plot.
            data (list): Full topic model data.
            column_info (dict): Column mappings.

        Returns:
            Tuple of strings: topic name, description, conversation ID, and text content.
        """
        if not data:
            raise PreventUpdate

        if column_info:
            conv_id, role_col, text_col, uuid_col = (
                column_info["conv_id"],
                column_info["role"],
                column_info["text"],
                column_info["uuid"],
            )
        else:
            conv_id = "filename"
            role_col = "role"
            text_col = "text"
            uuid_col = "uuid"

        if clickData:
            df = pd.DataFrame(data)

            selected_uuid = clickData["points"][0]["customdata"][2]
            conversation_id = clickData["points"][0]["customdata"][0]

            selected_point = df[df[uuid_col] == selected_uuid].iloc[0]
            name = f"Topic name: {selected_point[f'{MODEL}_name']}"
            description = f"Topic description: {selected_point.get(f'{MODEL}_description', 'N/A')}"
            conversation = f"Conversation ID: {conversation_id}"
            text_clean = f"User response: {selected_point[text_col]}"

            return name, description, conversation, text_clean

        return "Topic name: N/A", "Topic description: N/A", "Conversation ID: N/A", "User response: N/A"

    @app.callback(
        Output("conversation-view", "children"),
        Input("scatter-plot", "clickData"),
        State("session-id", "data"),
        State("column-store", "data"),
    )
    def display_conversation(
        clickData: Dict[str, Any],
        session_id: str,
        column_info: Dict[str, str],
    ) -> List[html.Div]:
        """
        Display the full conversation that the clicked point occurred in,
        with the clicked point text highlighted yellow.

        Args:
            clickData (dict): Click event data from the scatter plot.
            session_id (str): Current session identifier.
            column_info (dict): Column mappings.

        Returns:
            List of HTML divs representing the conversation.
        """
        if not session_id or not clickData:
            raise PreventUpdate

        output_dir = get_or_create_output_dir(session_id)

        if column_info:
            conv_id = column_info["conv_id"]
            text_col = column_info["text"]
            uuid_col = column_info["uuid"]
            role_col = column_info["role"]

            transcripts = pd.read_csv(os.path.join(output_dir, "topic_modelling_data.csv"))

        else:
            conv_id = "filename"
            role_col = "role"
            text_col = "text"
            uuid_col = "uuid"

            transcripts = pd.read_csv(os.path.join(output_dir, "topic_modelling_data.csv"))

        # Get selected point info
        selected_uuid = clickData["points"][0]["customdata"][2]
        selected_conversation = clickData["points"][0]["customdata"][0]
        print(f"Selected UUID: {selected_uuid}, Conversation ID: {selected_conversation}")

        # Get all rows in that conversation
        conv_rows = transcripts[transcripts[conv_id] == selected_conversation]
        print(conv_rows.columns)
        print(conv_rows.head())

        # Format display with highlight on selected uuid
        conversation_display = []
        for i, row in conv_rows.iterrows():
            text = row[text_col]
            role = row[role_col]
            is_selected = row[uuid_col] == selected_uuid
            content = html.Mark(text) if is_selected else text
            conversation_display.append(html.Div([html.Strong(f"{role}: "), html.Span(content)]))

        return conversation_display

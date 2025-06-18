# discovery_qualfml

This repo contains the code for the [QualFML](https://qualfml.dap-tools.uk/) app, a Plotly Dash application for generating insights from qualitative (e.g. interview, focus group) data.

## Setup

### Dependency management with `uv`

This project uses [`uv`](https://docs.astral.sh/uv/) for virtual environment management. If you are new to `uv`, you can find the [quickstart guide here](https://docs.astral.sh/uv/getting-started/).

We also utilise `direnv` via the `.envrc` file to automatically:

- Import your environment variables from `.env`
- Activate your virtual environment (_only if you comment out the relevant lines in `.envrc`_)

After installing `direnv` and `uv` on your system (we recommend doing this via [`brew`](https://brew.sh/) on macOS), you **must** run the following commands in your terminal to set up the project:

```bash
direnv allow
uv sync
uv run pre-commit install --install-hooks
```

### Secrets

You will need to create a `.env` file in the root of the project directory with the following variables:

```
VALID_USERNAME = # username for the app
VALID_PASSWORD = # password for the app
S3_BUCKET = # name of the s3 bucket to store outputs in (NOT CURRENTLY USED FOR THE APP)
LLM_SERVICE=Azure
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_OPENAI_API_VERSION=
```

### Running the app locally

To run the app locally, assuming you have your `uv` environment activated and the `.env` file set up, you can use the following command:

```
python discovery_qualfml/app/app.py
```

## Repository structure

```
discovery_qualfml/
├── automation/
│   ├── cleanup_outputs.sh      <-- script to clean up outputs once a day
│   └── cleanup.log
├── data/           <-- not strictly necessary but you can store test data here
├── discovery_qualfml/
│   ├── __init__.py
│   ├── __pycache__/
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── notebooks/          <-- scrappy work
│   ├── app/
│   │   ├── __pycache__/
│   │   ├── app.py              <-- the main app file
│   │   ├── assets/
│   │   │   └── style.css         <-- custom css styles for the app
│   │   ├── callbacks/          <-- scripts that manage reactivity; one per tab
│   │   │   ├── __pycache__/
│   │   │   ├── rq_callbacks.py
│   │   │   ├── topic_modelling_callbacks.py
│   │   │   └── upload_callbacks.py
│   │   ├── layout/     <-- scripts that manage layout; one per tab
│   │   │   ├── __pycache__/
│   │   │   ├── rq_tab.py
│   │   │   ├── topic_mapping.py
│   │   │   └── upload.py
│   │   └── style.py        <-- other style-related things that are done in python, not css
│   ├── config/
│   │   ├── base.yaml
│   │   └── logging.yaml
│   ├── docs/
│   │   ├── deploying_the_app.md
│   │   └── top_down_approach.md
│   └── utils/
│       ├── __init__.py
│       ├── __pycache__/
│       ├── dash_utils.py
│       ├── file_processing.py
│       ├── llm_question_answering.py
│       ├── llm_summarize.py
│       ├── topic_modelling.py
│       ├── topic_modelling_llm_utils.py
│       └── prompts/
│           ├── llm_check_system_a.txt
│           └── topic_model_prompt.txt
├── discovery_qualfml.egg-info/
│   ├── dependency_links.txt
│   ├── PKG-INFO
│   ├── requires.txt
│   ├── SOURCES.txt
│   └── top_level.txt
├── LICENSE
├── README.md       <-- this doc
├── errors.log
├── info.log
├── outputs/        <-- outputs from the app get saved here, and cleaned out once daily
├── pyproject.toml
└── uv.lock

```

## Contributor guidelines

[Technical and working style guidelines](https://github.com/nestauk/ds-cookiecutter/blob/master/GUIDELINES.md)

---

<small><p>Project based on <a target="_blank" href="https://github.com/nestauk/ds-cookiecutter">Nesta's data science project template</a>
(<a href="http://nestauk.github.io/ds-cookiecutter">Read the docs here</a>).
</small>

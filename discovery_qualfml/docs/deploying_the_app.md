# Deploying the app on EC2

You will first need to obtain the pem key (ask Karlis) and ssh into [this EC2 instance](https://eu-west-2.console.aws.amazon.com/ec2/home?region=eu-west-2#InstanceDetails:instanceId=i-0658ce4544eb70b09)

Clone the repo:

```
git clone https://github.com/nestauk/discovery_qualfml.git # clone the repo
cd discovery_qualfml/ # navigate into repo directory
git checkout refactor # checkout the current branch
```

Install uv and then set up the virtual environment:

- Install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh`
- `uv venv`
- `source .venv/bin/activate`
- `uv pip install -e .`

NB you may have issues with `llmvmlite` similar to that described [here](https://github.com/MaartenGr/BERTopic/issues/2141). I got round this by running `uv pip install bertopic` and then running `uv pip install -e .` again.

You will need to create a secrets file with `touch .env`
... and populate it with:

```
VALID_USERNAME =
VALID_PASSWORD =
S3_BUCKET =
LLM_SERVICE=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT_NAME=
AZURE_OPENAI_API_VERSION=
```

You should now be able to run the app with

```
nohup python discovery_qualfml/app/app.py &
```

Make a note of the PID (e.g. `1111`). Should you ever need to, you can stop the app running with e.g. `kill 1111`.

Add a cron job to clean up app data once a day:

- Edit crontab with `crontab -e`
- Add a line like this to the end of the file: `0 2 * * * discovery_qualfml/automation/cleanup_outputs.sh`
- Press ctrl+o then enter, then ctrl+x, to exit the editor
- Make sure it is executable: `chmod +x cleanup.sh`
- Test it manually: `bash automation/cleanup_outputs.sh`

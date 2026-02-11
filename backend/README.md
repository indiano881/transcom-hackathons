# Running the Project

This project deploys user-uploaded frontend code to **Google Cloud Run**. Deploying requires the **Google Cloud CLI** and **Terraform**, and using Cloud Run requires a Google Cloud account with a linked credit card.

> If your goal is **not** to deploy user code but only to develop and test detection plugins, you can skip the sections related to Google Cloud CLI and Terraform.

---

## Installing Google Cloud CLI (Optional)

Deploying user-uploaded code to Cloud Run requires the Google Cloud CLI.

* **Homebrew users** can follow the official guide: [https://docs.cloud.google.com/sdk/docs/downloads-homebrew](https://docs.cloud.google.com/sdk/docs/downloads-homebrew)
* **Non-Homebrew users** can follow: [https://docs.cloud.google.com/sdk/docs/install-sdk](https://docs.cloud.google.com/sdk/docs/install-sdk)

After installation, you can check if it’s successful with:

```bash
gcloud version
```

---

## Initializing Google Cloud CLI (Optional)

Run the following command to initialize the CLI:

```bash
gcloud init
```

You will be prompted to open a link in your browser for authorization. After successful authorization, the page will redirect to the Google Cloud tutorial. You can explore the Cloud Run tutorial if needed.

---

## Installing Terraform (Optional)

Follow the official guide to install Terraform: [https://developer.hashicorp.com/terraform/install](https://developer.hashicorp.com/terraform/install)

---

## Installing Python

This project has been tested with **Python 3.12**. Other recent Python versions may also work, but older versions might not.

---

## Installing Dependencies

Create a virtual environment and install dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Project Configuration

This project uses **pydantic-settings** for configuration management.

* The system first attempts to load configuration from a `.env` file in the current working directory.
* If a variable is missing in `.env`, it will fall back to environment variables.

Default configuration can be found in `app/config.py`. By default, **Anthropic API** and deployment features are disabled.

If you don't need Google Cloud Run and Anthropic right now, then you don't need to add or modify any configuration.

---

## Running the Server

Start the backend server with:

```bash
python run.py
```

---

# Backend API Development

Using Python’s built-in PDB debugger in the terminal is not very convenient. We recommend using an IDE like **PyCharm** for debugging.

* API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
* API testing: [http://localhost:8000/docs](http://localhost:8000/docs)

---

# Tech Stack

* [Python 3.12](https://www.python.org/downloads/)
* [uvicorn 0.40.0](https://pypi.org/project/uvicorn/)
* [fastapi 0.128.7](https://pypi.org/project/fastapi/)
* [python-multipart 0.0.22](https://pypi.org/project/python-multipart/)
* [pydantic 2.12.5](https://pypi.org/project/pydantic/)
* [pydantic-settings 2.12.0](https://pypi.org/project/pydantic-settings/)
* [aiosqlite 0.22.1](https://pypi.org/project/aiosqlite/)


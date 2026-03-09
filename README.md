# SERTS-model

A small script to compare the levelized cost of heat (LCOH) for a heat pump vs a gas boiler.

## Prerequisites

This project requires Python. Install Python 3.8 or newer from the official downloads page:

https://www.python.org/downloads/

On macOS you can also install Python via Homebrew:

```bash
brew install python
```

## Requirements

Install the project's Python dependencies (recommended inside a virtual environment):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

There are two modes of operation:

1. **Command line calculator** – the original `src/main.py` script:

    ```bash
    python src/main.py
    ```

    This will print LCOH results to the console and open a bar chart comparison using matplotlib.

2. **Interactive dashboard** – the new Streamlit application. Start it from the repo root:

    ```bash
    source .venv/bin/activate           # activate virtualenv if you use one
    streamlit run streamlit_app.py
    ```

    After the server starts you can view the dashboard in your browser at `http://localhost:8501`.

    ### Network access

    - To make the dashboard available to other devices on your local network, run:

      ```bash
      streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
      ```

      Then open `http://<your‑machine‑ip>:8501` (your IP appears in the Streamlit logs).

    - For public/external access you need to deploy the app to a hosting service (see "Deployment" section below).

## Deployment

The dashboard can be hosted on any service that supports Python applications. A few options:

* **Streamlit Cloud** – free for small projects and integrates directly with GitHub. Simply push this repository to a public GitHub repo and connect it in Streamlit Cloud. The service will install the packages listed in `requirements.txt` and run the app automatically.
* **Heroku / Railway / ...** – create a `Procfile` with the following content and deploy normally:

    ```procfile
    web: streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
    ```

  Make sure your `requirements.txt` includes all the dependencies (see below).

* **Docker** – you can also build a container using the Streamlit [Docker image](https://docs.streamlit.io/library/deploy/docker).

> ⚠️ When exposing the app publicly, take care not to publish any sensitive data or credentials in the repository.


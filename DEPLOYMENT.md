# Deployment Guide

## Recommended split

- `Streamlit Community Cloud`: deploy the frontend from `frontend/app.py`
- `Hugging Face Spaces (Docker)`: deploy the FastAPI backend with the root `Dockerfile`

This matches the current project structure better than trying to run both processes on Streamlit Community Cloud.

## GitHub

- Repository: `https://github.com/PKQHA/cs-workflow.git`
- Branch to deploy from: `main`

## Streamlit Community Cloud

### App settings

- Repository: this GitHub repo
- Branch: `main`
- Main file path: `frontend/app.py`

### Dependencies

- The repo root now includes `requirements.txt`
- It installs `frontend/requirements.txt`

### Secrets

Set the following in the Streamlit Community Cloud secrets console:

```toml
BACKEND_BASE_URL = "https://<your-space-subdomain>.hf.space"
```

The frontend reads `BACKEND_BASE_URL` from environment variables, and root-level Streamlit secrets are exposed as environment variables.

## Hugging Face Spaces

### Space type

- SDK: `Docker`
- App port: `7860`

### Recommended YAML block for the Space README

```yaml
---
title: Hotel Customer Service Backend
emoji: "\U0001F3E8"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---
```

### Runtime variables

Set these in the Space settings as Variables or Secrets as appropriate:

```text
BACKEND_HOST=0.0.0.0
BACKEND_PORT=7860
EXCEL_WORK_DIR=/app/data
MODEL_PROVIDER=mock
```

If you switch away from `mock`, also configure:

```text
MODEL_NAME=...
MODEL_BASE_URL=...
MODEL_API_KEY=...
```

Use a Secret for `MODEL_API_KEY`.

### Important limitation

The current Hugging Face Spaces documentation says persistent storage for Spaces is no longer available in this configuration, so uploaded Excel workspace files should be treated as temporary. If the Space rebuilds or resets, the uploaded workspaces may be lost.

If you need durable Excel workspace storage after deployment, move the backend to a platform with persistent disk or external object storage.

## Deployment order

1. Push this repo to GitHub.
2. Create the Hugging Face Docker Space and connect it to this repo.
3. Wait for the backend Space build to succeed and note the public URL.
4. Create the Streamlit Community Cloud app from this repo.
5. Set `BACKEND_BASE_URL` in Streamlit secrets to the Hugging Face Space URL.
6. Redeploy or restart the Streamlit app.

## Quick validation after deployment

1. Open the Streamlit app.
2. Upload an Excel file.
3. Confirm `workspace_id` appears and survives a page refresh.
4. Create a form and download `data.xlsx`.
5. Confirm the frontend is calling the Hugging Face backend successfully.

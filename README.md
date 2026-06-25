# SME Companion AI

SME Companion AI is a Streamlit app for Thai small-business owners. It provides an interactive demo experience with sample stores, business diagnosis, content suggestions, chat guidance, and guarded LLM assistance.

## Local Setup

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Create a local environment file from the example:

```bash
cp .env.example .env
```

3. Add provider keys to `.env` as needed:

```bash
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
OPENAI_MODEL=gpt-4.1-mini
```

The app can still run without provider keys by using deterministic fallback responses.

## Run Locally

```bash
streamlit run app.py
```

## Streamlit Cloud Secrets

Add these secrets in Streamlit Cloud before public demo testing:

```toml
DEEPSEEK_API_KEY = "..."
OPENAI_API_KEY = "..."
```

Optional model overrides:

```toml
DEEPSEEK_MODEL = "deepseek-v4-flash"
OPENAI_MODEL = "gpt-4.1-mini"
```

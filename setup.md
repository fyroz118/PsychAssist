# Setup

## 1. Minimum install (works right away)
    pip install -r requirements.txt
    streamlit run PsychAssist_streamlit.py

No secrets needed. SQLite, no auth, no encryption. Perfect for testing.

## 2. Turn on auth (#23)
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`,
fill in `[auth]`, restart. Users map:
    [auth.users]
    alice = "alice-pass"
    bob   = "bob-pass"

## 3. Turn on encryption (#25)
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Paste the key into `[encryption] key` in secrets.toml. New notes are
encrypted at rest; existing plaintext notes still load.

## 4. Turn on Postgres / Supabase (#17)
Create a project on supabase.com, copy the "Connection string (URI)" into
`[database] url`. Restart. Tables are auto-created on first run.

## 5. GitHub Actions (#33)
Push the `.github/workflows/ci.yml` file. Tests run automatically.

## 6. Pre-commit (#35)
    pip install pre-commit
    pre-commit install
Now black + ruff run on every commit.

## 7. Streamlit Cloud
Point Main file path at `PsychAssist_streamlit.py`, add the same
`secrets.toml` content via the app's "Secrets" section, deploy.
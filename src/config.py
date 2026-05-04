from dotenv import load_dotenv, find_dotenv
import os
from functools import lru_cache

# Load local defaults only outside Render.
# Render injects environment variables at runtime, and we should not
# accidentally fall back to localhost values there.
if not os.getenv("RENDER"):
    load_dotenv(dotenv_path="default.env", override=False)

# Then override with .env if available
load_dotenv(dotenv_path=find_dotenv(".env"), override=True)


def _normalized_db_url() -> str | None:
    # Prefer explicit project variable, then platform default name.
    url = os.getenv("POSTGRES_URI") or os.getenv("DATABASE_URL")
    if not url:
        return None

    # SQLAlchemy 2 + psycopg driver URL normalization.
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


class Settings:
    API_KEY: str | None = os.getenv("API_KEY")
    POSTGRES_URI: str | None = _normalized_db_url()

    def __init__(self):
        if not self.API_KEY:
            raise ValueError("API_KEY is missing in the environment variables.")
        if not self.POSTGRES_URI:
            raise ValueError("POSTGRES_URI is missing in the environment variables.")


@lru_cache()
def get_settings():
    return Settings()

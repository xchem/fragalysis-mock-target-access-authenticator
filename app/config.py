"""Configuration (environment) variables."""
import os


class Config:
    """Simple config module where all environment variables can be found."""

    QUERY_KEY: str | None = os.getenv("TAA_QUERY_KEY")

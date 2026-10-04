"""Connection strings as hosting dashboards hand them out."""

import pytest

from src.models.database import normalize_url


@pytest.mark.parametrize("given, expected", [
    ("postgresql://u:p@ep-x.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
     "postgresql+psycopg://u:p@ep-x.aws.neon.tech/neondb?sslmode=require&channel_binding=require"),
    ('"postgresql://u:p@host/db?sslmode=require"', "postgresql+psycopg://u:p@host/db?sslmode=require"),
    ("  postgres://u:p@host:5432/db \n", "postgresql+psycopg://u:p@host:5432/db"),
    ("postgresql+psycopg://u:p@db:5432/forbidden_lib", "postgresql+psycopg://u:p@db:5432/forbidden_lib"),
])
def test_normalize_url(given, expected):
    assert normalize_url(given) == expected

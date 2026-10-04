"""Connection strings as hosting dashboards hand them out."""

import pytest

from src.models.database import normalize_url


@pytest.mark.parametrize("given, expected", [
    ("postgresql://u:p@ep-x.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
     "postgresql+psycopg://u:p@ep-x.aws.neon.tech/neondb?sslmode=require&channel_binding=require"),
    ('"postgresql://u:p@host/db?sslmode=require"', "postgresql+psycopg://u:p@host/db?sslmode=require"),
    ("  postgres://u:p@host:5432/db \n", "postgresql+psycopg://u:p@host:5432/db"),
    ("postgresql+psycopg://u:p@db:5432/forbidden_lib", "postgresql+psycopg://u:p@db:5432/forbidden_lib"),
    # A whole .env line pasted into a dashboard's value field
    ('DATABASE_URL_UNPOOLED="postgresql://u:p@host/db?sslmode=require"',
     "postgresql+psycopg://u:p@host/db?sslmode=require"),
])
def test_normalize_url(given, expected):
    assert normalize_url(given) == expected


@pytest.mark.parametrize("given", ["DATABASE_URL_UNPOOLED", "", "   ", "neondb_owner:secret@host/db"])
def test_not_a_url_is_explained_without_the_password(given):
    with pytest.raises(RuntimeError) as e:
        normalize_url(given)
    assert "DATABASE_URL must be a connection string" in str(e.value)
    assert "secret" not in str(e.value)

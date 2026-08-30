"""add MCP OAuth persistence

Revision ID: 007
Revises: 006
Create Date: 2026-08-30 21:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("client_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_oauth_clients_client_id", "oauth_clients", ["client_id"], unique=True
    )

    op.create_table(
        "oauth_authorization_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("redirect_uri_provided_explicitly", sa.Boolean(), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_oauth_authorization_codes_code_hash",
        "oauth_authorization_codes",
        ["code_hash"],
        unique=True,
    )
    op.create_index(
        "ix_oauth_authorization_codes_user_id", "oauth_authorization_codes", ["user_id"]
    )
    op.create_index(
        "ix_oauth_authorization_codes_client_id",
        "oauth_authorization_codes",
        ["client_id"],
    )
    op.create_index(
        "ix_oauth_authorization_codes_expires_at",
        "oauth_authorization_codes",
        ["expires_at"],
    )

    op.create_table(
        "oauth_token_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("access_token_hash", sa.String(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("resource", sa.Text(), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refresh_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_oauth_token_grants_access_token_hash",
        "oauth_token_grants",
        ["access_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_oauth_token_grants_refresh_token_hash",
        "oauth_token_grants",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index("ix_oauth_token_grants_user_id", "oauth_token_grants", ["user_id"])
    op.create_index(
        "ix_oauth_token_grants_client_id", "oauth_token_grants", ["client_id"]
    )
    op.create_index(
        "ix_oauth_token_grants_access_expires_at",
        "oauth_token_grants",
        ["access_expires_at"],
    )
    op.create_index(
        "ix_oauth_token_grants_refresh_expires_at",
        "oauth_token_grants",
        ["refresh_expires_at"],
    )


def downgrade() -> None:
    op.drop_table("oauth_token_grants")
    op.drop_table("oauth_authorization_codes")
    op.drop_table("oauth_clients")

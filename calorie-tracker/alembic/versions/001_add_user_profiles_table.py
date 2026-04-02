"""add user_profiles table

Revision ID: 001
Revises: 
Create Date: 2025-10-27 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(), nullable=True),
        sa.Column('activity_level', sa.String(), nullable=True),
        sa.Column('goal', sa.String(), nullable=True),
        sa.Column('dietary_preference', sa.String(), nullable=True),
        sa.Column('custom_calories', sa.Integer(), nullable=True),
        sa.Column('custom_protein_g', sa.Integer(), nullable=True),
        sa.Column('custom_carbs_g', sa.Integer(), nullable=True),
        sa.Column('custom_fats_g', sa.Integer(), nullable=True),
        sa.Column('custom_fiber_g', sa.Integer(), nullable=True),
        sa.Column('bmr', sa.Float(), nullable=True),
        sa.Column('tdee', sa.Float(), nullable=True),
        sa.Column('target_calories', sa.Integer(), nullable=True),
        sa.Column('target_protein_g', sa.Integer(), nullable=True),
        sa.Column('target_carbs_g', sa.Integer(), nullable=True),
        sa.Column('target_fats_g', sa.Integer(), nullable=True),
        sa.Column('target_fiber_g', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_profiles_id'), 'user_profiles', ['id'], unique=False)


def downgrade() -> None:
    # Drop user_profiles table
    op.drop_index(op.f('ix_user_profiles_id'), table_name='user_profiles')
    op.drop_table('user_profiles')
"""change comment_id and user_id to varchar

迁移 ID: 240bd34f2d2e
父迁移: c0f7241d2442
创建时间: 2026-07-09 17:08:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '240bd34f2d2e'
down_revision: str | Sequence[str] | None = 'c0f7241d2442'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    with op.batch_alter_table('aihelper_comments', schema=None) as batch_op:
        batch_op.alter_column('comment_id',
                              existing_type=sa.Integer(),
                              type_=sa.String(64),
                              existing_nullable=False)

    with op.batch_alter_table('aihelper_settings', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.Integer(),
                              type_=sa.String(64),
                              existing_nullable=False)


def downgrade(name: str = "") -> None:
    if name:
        return
    with op.batch_alter_table('aihelper_comments', schema=None) as batch_op:
        batch_op.alter_column('comment_id',
                              existing_type=sa.String(64),
                              type_=sa.Integer(),
                              existing_nullable=False)

    with op.batch_alter_table('aihelper_settings', schema=None) as batch_op:
        batch_op.alter_column('user_id',
                              existing_type=sa.String(64),
                              type_=sa.Integer(),
                              existing_nullable=False)

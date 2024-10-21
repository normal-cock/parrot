"""empty message

Revision ID: ae1137c496d9
Revises: 43debeda99c4
Create Date: 2024-10-20 22:29:42.126794

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae1137c496d9'
down_revision = '43debeda99c4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('meaning', sa.Column(
        'use_case_voice', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('meaning', 'use_case_voice')
    # ### end Alembic commands ###

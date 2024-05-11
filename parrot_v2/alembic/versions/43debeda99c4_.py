"""empty message

Revision ID: 43debeda99c4
Revises: 5d9547a5be02
Create Date: 2024-05-11 17:50:41.906554

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '43debeda99c4'
down_revision = '5d9547a5be02'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('player_item',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('item_id', sa.String(
                        length=256), nullable=False),
                    sa.Column('item_name', sa.String(
                        length=256), nullable=False),
                    sa.Column('item_type', sa.Enum(
                        'MP3', 'MP4', name='itemtype'), nullable=True),
                    sa.Column('subtitle_adjustment',
                              sa.Float(), nullable=True),
                    sa.Column('created_time', sa.DateTime(), nullable=True),
                    sa.Column('changed_time', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('item_id')
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('player_item')
    # ### end Alembic commands ###

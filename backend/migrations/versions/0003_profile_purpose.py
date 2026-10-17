"""Explicit account purpose. Existing identities are classified by the local audit script."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
branch_labels=None
depends_on=None
def upgrade():
 # 0001 bootstraps current metadata on an empty database.
 if 'is_test' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('players')}:
  op.add_column('players',sa.Column('is_test',sa.Boolean(),nullable=False,server_default=sa.false()))
 if 'ix_players_is_test' not in {i['name'] for i in sa.inspect(op.get_bind()).get_indexes('players')}:
  op.create_index('ix_players_is_test','players',['is_test'])
def downgrade():
 op.drop_index('ix_players_is_test',table_name='players');op.drop_column('players','is_test')

"""Managed player wallets and persistent registered item instances. Preserves all v1 data."""
from alembic import op
from backend.app.models import ManagedWallet,ItemInstance,RelicEquipment,ItemOperation,ItemEvent,WorkerState
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
TABLES=[ManagedWallet.__table__,ItemInstance.__table__,RelicEquipment.__table__,ItemOperation.__table__,ItemEvent.__table__,WorkerState.__table__]
def upgrade():
 for table in TABLES:table.create(op.get_bind(),checkfirst=True)
def downgrade():
 for table in reversed(TABLES):table.drop(op.get_bind(),checkfirst=True)

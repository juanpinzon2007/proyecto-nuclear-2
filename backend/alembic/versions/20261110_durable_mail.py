"""Despacho durable cifrado por notificación. Sin backfill de códigos."""
from alembic import op
import sqlalchemy as sa

revision = '20261110_durable_mail'
down_revision = '20261108_voluntary_partial'
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != 'postgresql':
        raise RuntimeError('Despacho de correo requiere PostgreSQL.')
    op.create_table('despacho_correo',
        sa.Column('id_notificacion', sa.Uuid(), sa.ForeignKey('notificacion.id'), primary_key=True),
        sa.Column('payload_cifrado', sa.LargeBinary(), nullable=False),
        sa.Column('estado', sa.String(30), nullable=False, server_default='PENDIENTE'),
        sa.Column('intentos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ultimo_error', sa.String(60)),
        sa.Column('ultimo_intento_en', sa.DateTime(timezone=True)),
        sa.Column('aceptado_en', sa.DateTime(timezone=True)),
        sa.CheckConstraint("estado IN ('PENDIENTE','REINTENTAR','ACEPTADO_PROVEEDOR','CANCELADO')", name='ck_despacho_correo_estado'),
        sa.CheckConstraint('intentos>=0', name='ck_despacho_correo_intentos'),
        sa.CheckConstraint('length(payload_cifrado)>0', name='ck_despacho_correo_payload'),
        sa.CheckConstraint("(estado='ACEPTADO_PROVEEDOR') = (aceptado_en IS NOT NULL)", name='ck_despacho_correo_aceptacion'))
    op.create_index('ix_despacho_correo_estado', 'despacho_correo', ['estado'])


def downgrade():
    op.execute('LOCK TABLE despacho_correo IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().scalar(sa.text('SELECT 1 FROM despacho_correo LIMIT 1')):
        raise RuntimeError('No eliminar el historial de despacho existente.')
    op.drop_index('ix_despacho_correo_estado', table_name='despacho_correo')
    op.drop_table('despacho_correo')

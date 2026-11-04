"""RF-18: asignaciones técnicas explícitas de docentes a espacios, inicialmente vacías."""
from alembic import op
import sqlalchemy as sa

revision = "20261104_teacher_spaces"
down_revision = "20261102_immutable_answers"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != 'postgresql':
        raise RuntimeError('Revisión RF-18 reservada a PostgreSQL.')
    op.create_table('docente_espacio_academico',
        sa.Column('id_docente',sa.Integer(),nullable=False),
        sa.Column('espacio_academico_id',sa.Uuid(),nullable=False),
        sa.PrimaryKeyConstraint('id_docente','espacio_academico_id'),
        sa.ForeignKeyConstraint(['id_docente'],['usuario.id_usuario']),
        sa.ForeignKeyConstraint(['espacio_academico_id'],['espacio_academico.id']))


def downgrade():
    if op.get_bind().dialect.name != 'postgresql':
        raise RuntimeError('Downgrade RF-18 reservado a PostgreSQL.')
    op.execute('LOCK TABLE public.docente_espacio_academico IN ACCESS EXCLUSIVE MODE')
    if op.get_bind().scalar(sa.text('SELECT 1 FROM public.docente_espacio_academico LIMIT 1')) is not None:
        raise RuntimeError('No eliminar asignaciones explícitas existentes: exportar/conciliar antes del downgrade.')
    op.drop_table('docente_espacio_academico')

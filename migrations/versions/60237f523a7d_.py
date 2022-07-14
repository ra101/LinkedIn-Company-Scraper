"""empty message

Revision ID: 60237f523a7d
Revises: 720a013e8e7c
Create Date: 2022-07-14 21:42:17.095753

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60237f523a7d'
down_revision = '720a013e8e7c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('linkedin_employment_records',
    sa.Column('company_id', sa.BigInteger(), nullable=True),
    sa.Column('employee_id', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['linkedin_companies_base_details.internal_id'], ),
    sa.ForeignKeyConstraint(['employee_id'], ['linkedin_employees_details.public_id'], )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('linkedin_employment_records')
    # ### end Alembic commands ###
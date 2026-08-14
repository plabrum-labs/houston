"""Document model — file uploads (PDFs, Word docs, etc.) with threads."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.base.models import BaseDBModel
from app.platform.base.threadable_mixin import ThreadableMixin
from app.platform.documents.enums import DocumentStates
from app.platform.state_machine.models import StateMachineMixin

# TODO: apply the source app scope (org/owner) once domain is decided.


class Document(
    ThreadableMixin,
    StateMachineMixin(state_enum=DocumentStates, initial_state=DocumentStates.PENDING),
    BaseDBModel,
):
    """Threadable file upload — PDFs, Word, Excel, etc."""

    __tablename__ = "documents"

    file_key: Mapped[str] = mapped_column(sa.Text, nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    file_type: Mapped[str] = mapped_column(sa.Text, nullable=False)  # 'pdf', 'docx', etc.
    file_size: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(sa.Text, nullable=False)

    thumbnail_key: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

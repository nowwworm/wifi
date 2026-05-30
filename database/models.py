from datetime import datetime
from sqlalchemy import String, Integer, DateTime, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Edit(Base):
    __tablename__ = "edits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    client_username: Mapped[str] = mapped_column(String, nullable=True)
    text_content: Mapped[str] = mapped_column(String, nullable=True)
    image_path: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, approved, rejected, archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

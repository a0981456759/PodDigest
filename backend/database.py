import os
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./podcast_digest.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Show(Base):
    __tablename__ = "shows"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String)
    description = Column(Text)
    rss_url = Column(String, unique=True, nullable=False)
    artwork_url = Column(String)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    episodes = relationship("Episode", back_populates="show", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"
    id = Column(Integer, primary_key=True, index=True)
    show_id = Column(Integer, ForeignKey("shows.id"), nullable=False)
    guid = Column(String, unique=True, nullable=False)
    title = Column(String)
    description = Column(Text)
    pub_date = Column(DateTime)
    duration_sec = Column(Integer)
    audio_url = Column(String)
    audio_local_path = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # JSON string
    transcript_failed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    show = relationship("Show", back_populates="episodes")


class DigestJob(Base):
    __tablename__ = "digest_jobs"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="pending")  # pending/running/done/failed
    triggered_by = Column(String, default="manual")  # manual/schedule
    episode_ids = Column(Text, default="[]")  # JSON array
    progress_pct = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    digest = relationship("Digest", back_populates="job", uselist=False)


class Digest(Base):
    __tablename__ = "digests"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("digest_jobs.id"), nullable=False)
    title = Column(String, nullable=False)
    script = Column(Text, nullable=False)
    audio_path = Column(String, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    episode_ids = Column(Text, default="[]")  # JSON array, copied from job
    published_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    job = relationship("DigestJob", back_populates="digest")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, default=1)
    topic_tags = Column(Text, default="[]")  # JSON array
    interest_description = Column(Text, default="")
    output_language = Column(String, default="en")
    schedule_type = Column(String, default="weekly")  # new_episode/weekly/biweekly
    schedule_day = Column(Integer, default=0)  # 0=Mon
    schedule_hour = Column(Integer, default=8)
    feed_token = Column(String, default=lambda: str(uuid.uuid4()))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure UserPreference row exists
    db = SessionLocal()
    try:
        if not db.query(UserPreference).filter_by(id=1).first():
            db.add(UserPreference(id=1))
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

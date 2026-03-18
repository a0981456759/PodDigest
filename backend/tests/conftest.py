import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Show, Episode, DigestJob, Digest, UserPreference

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    if not session.query(UserPreference).filter_by(id=1).first():
        session.add(UserPreference(id=1))
        session.commit()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

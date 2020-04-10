#!/usr/bin/env python3

import sys

import datetime
import pathlib

import sqlalchemy # PyPI: SQLAlchemy
import sqlalchemy.ext.declarative # PyPI: SQLAlchemy

def migrate(wiki_root, engine):
    """Migrate a flask-wiki wiki from the file system backend to the database backend"""

    Base = sqlalchemy.ext.declarative.declarative_base()

    class Namespace(Base):
        __tablename__ = 'wiki_namespaces'

        name = sqlalchemy.Column(sqlalchemy.String(), primary_key=True)

    class Revision(Base):
        __tablename__ = 'wiki'

        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        namespace = sqlalchemy.Column(sqlalchemy.String(), nullable=False)
        title = sqlalchemy.Column(sqlalchemy.String(), nullable=False)
        text = sqlalchemy.Column(sqlalchemy.String(), nullable=False)
        author = sqlalchemy.Column(sqlalchemy.BigInteger)
        timestamp = sqlalchemy.Column(sqlalchemy.TIMESTAMP(timezone=True), nullable=False)
        summary = sqlalchemy.Column(sqlalchemy.String())

    Base.metadata.create_all(engine)
    session = sqlalchemy.orm.sessionmaker(bind=engine)()

    for namespace_dir in wiki_root.iterdir():
        session.add(Namespace(name=namespace_dir.name))
        for article_path in namespace_dir.iterdir():
            with article_path.open() as article_f:
                text = article_f.read()
            session.add(Revision(
                namespace=namespace_dir.name,
                title=article_path.stem,
                text=text,
                timestamp=datetime.datetime.fromtimestamp(article_path.stat().st_mtime, datetime.timezone.utc),
                summary='automatically migrated'
            ))
    session.commit()

if __name__ == '__main__':
    try:
        wiki_root = pathlib.Path(sys.argv[1])
        engine = sqlalchemy.create_engine(sys.argv[2], echo=True)
    except IndexError:
        sys.exit('Usage: migrate-flask-wiki <wiki-root> <db-url>')
    migrate(wiki_root, engine)

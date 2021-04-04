from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from database import models


class Database:
    def __init__(self, db_url: str):
        engine = create_engine(db_url)
        models.Base.metadata.create_all(bind=engine)
        self.session_m = sessionmaker(bind=engine)

    @staticmethod
    def _get_or_create(session, model, data):
        db_model = session.query(model).filter(model.url == data['url']).first()
        if not db_model:
            db_model = model(**data)
        return db_model

    def create_post(self, data):
        session = self.session_m()
        writer = self._get_or_create(session, models.Writer, data.pop('writer'))
        post = self._get_or_create(session, models.Post, data.pop('post'))
        post.writer = writer

        for tag_data in data['tags']:
            tag = self._get_or_create(session, models.Tag, tag_data)
            post.tags.append(tag)

        for comment_data in data['comments']:
            comment = models.Comments(**comment_data)
            post.comments.append(comment)

        session.add(post)

        try:
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
        finally:
            session.close()
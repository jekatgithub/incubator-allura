from datetime import datetime
from time import sleep

from pylons import c
import re
import markdown

import pymongo
from pymongo.errors import OperationFailure

from ming import schema as S
from ming import Field

from pyforge.model import Artifact, Message, User

wikiwords = [
    (r'\b([A-Z]\w+[A-Z]+\w+)', r'<a href="../\1/">\1</a>'),
    (r'([^\\])\[(.*)\]', r'\1<a href="../\2/">\2</a>'),
    (r'\\\[(.*)\]', r'[\1]'),
    (r'^\[(.*)\]', r'<a href="../\1/">\1</a>'),
    ]
wikiwords = [
    (re.compile(pattern), replacement)
    for pattern, replacement in wikiwords ]

class Page(Artifact):
    class __mongometa__:
        name='page'

    title=Field(str)
    version=Field(int, if_missing=0)
    author_id=Field(S.ObjectId, if_missing=lambda:c.user and c.user._id)
    timestamp=Field(S.DateTime, if_missing=datetime.utcnow)
    text=Field(S.String, if_missing='')

    def url(self):
        return c.app.script_name + '/' + self.title + '/'

    def index(self):
        result = Artifact.index(self)
        author = self.author
        result.update(
            title_s=self.title,
            author_user_name_t=author.username,
            author_display_name_t=author.display_name,
            timestamp_dt=self.timestamp,
            version_i=self.version,
            type_s='WikiPage',
            text=self.text)
        return result

    @classmethod
    def upsert(cls, title, version=None):
        q = dict(
            project_id=c.project._id,
            title=title)
        if version is not None:
            q['version'] = version
        versions = cls.m.find(q)
        if not versions.count():
            return cls.make(dict(
                    project_id=c.project._id,
                    title=title,
                    text='',
                    version=0))
        latest = max(versions, key=lambda v:v.version)
        new_obj=dict(latest, version=latest.version + 1)
        del new_obj['_id']
        del new_obj['author_id']
        del new_obj['timestamp']
        return cls.make(new_obj)

    @classmethod
    def history(cls, title):
        history = cls.m.find(
            dict(project_id=c.project._id, title=title))
        history = history.sort('version', pymongo.DESCENDING)
        return history

    @property
    def html_text(self):
        md = markdown.Markdown(
            extensions=['codehilite'],
            output_format='html4'
        )
        content = md.convert(self.text)
        for pattern, replacement in wikiwords:
            content = pattern.sub(replacement, content)
        return content

    @property
    def author(self):
        return User.m.get(_id=self.author_id)

    def reply(self):
        while True:
            try:
                c = Comment.make(dict(page_title=self.title))
                c.m.insert()
                return c
            except OperationFailure:
                sleep(0.1)
                continue

    def root_comments(self):
        return Comment.m.find(dict(page_title=self.title, parent_id=None))

class Comment(Message):
    class __mongometa__:
        name='comment'
    page_title=Field(str)

    def index(self):
        result = Message.index(self)
        author = self.author()
        result.update(
            title_s='Comment on page %s by %s' % (
                self.page_title, author.display_name),
            type_s='Comment on WikiPage',
            page_title_t=self.page_title)
        return result

    @property
    def page(self):
        versions = Page.m.find(dict(title=self.page_title)).all()
        pg = max(versions, key=lambda p:p.version)
        return pg

    def url(self):
        return self.page.url() + '#comment-' + self._id

    

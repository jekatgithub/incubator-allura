# -*- coding: utf-8 -*-
"""
Nosetest modules
"""
from nose.tools import *
import os
"""
Model tests for artifact
"""
from datetime import datetime
from time import sleep

from pylons import c, g
import re
import markdown
import mock

import pymongo
from pymongo.errors import OperationFailure

from ming import schema as S
from ming import Field

from pyforge.model import Artifact, Message, AppConfig
from pyforge.lib.app_globals import Globals

PROJECT = mock.Mock()
PROJECT.name = 'Test Project'
PROJECT.shortname = 'tp'
PROJECT._id = 'testproject/'
PROJECT.database = 'nosetest:project'
APP_CONFIG = mock.Mock()
APP_CONFIG._id = None
APP_CONFIG.project_id = 'testproject/'
APP_CONFIG.plugin_name = 'plugin'
APP_CONFIG.options.mount_point = 'foo'
APP = mock.Mock()
APP.config = APP_CONFIG

class Checkmessage(Message):
    class __mongometa__:
        name='checkmessage'
    page_title=Field(str)
    project=PROJECT
    app_config=APP_CONFIG
    def url(self):
        return ''
    def index(self):
        return dict()
    def shorthand_id(self):
        return ''

def setUp():
    g._push_object(Globals())
    c._push_object(mock.Mock())
    c.app = APP
    c.user._id = None
    c.project = PROJECT
    print 'Push config'
    
def test_artifact():
    class Checkartifact(Artifact):
        class __mongometa__:
            name='checkartifact'
        title=Field(str)
        version=Field(int, if_missing=0)
        author_id=Field(S.ObjectId, if_missing=lambda:c.user._id)
        timestamp=Field(S.DateTime, if_missing=datetime.utcnow)
        text=Field(S.String, if_missing='')

    assert_true('PyForge has available model::Artifact class')

def test_message_author():
    m = Checkmessage.make(dict(page_title='test_title'))
    m.author()
    assert_true('PyForge message has author')

def test_message_reply():
    m = Checkmessage.make(dict(page_title='test_title'))
    m.reply()
    assert_true('PyForge message has reply')

def test_message_descendants():
    m = Checkmessage.make(dict(page_title='test_title'))
    m.descendants()
    assert_true('PyForge message has descendants')

def test_message_replies():
    m = Checkmessage.make(dict(page_title='test_title'))
    m.replies()
    assert_true('PyForge message has replies')


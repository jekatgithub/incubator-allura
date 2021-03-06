#       Licensed to the Apache Software Foundation (ASF) under one
#       or more contributor license agreements.  See the NOTICE file
#       distributed with this work for additional information
#       regarding copyright ownership.  The ASF licenses this file
#       to you under the Apache License, Version 2.0 (the
#       "License"); you may not use this file except in compliance
#       with the License.  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing,
#       software distributed under the License is distributed on an
#       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#       KIND, either express or implied.  See the License for the
#       specific language governing permissions and limitations
#       under the License.

import datetime
import tempfile
import json
import operator

from nose.tools import assert_equal
from pylons import tmpl_context as c

from allura import model as M
from allura.tests import decorators as td
from alluratest.controller import setup_basic_test, setup_global_objects
from forgewiki import model as WM


class TestBulkExport(object):

    def setUp(self):
        setup_basic_test()
        setup_global_objects()
        self.setup_with_tools()

    @td.with_wiki
    def setup_with_tools(self):
        self.project = M.Project.query.get(shortname='test')
        self.wiki = self.project.app_instance('wiki')
        page = WM.Page.upsert('A New Hope')
        page.text = 'Star Wars Episode IV: A New Hope'
        page.mod_date = datetime.datetime(2013, 7, 5)
        page.labels = ['star wars', 'movies']
        page.commit()
        page.discussion_thread.add_post(text='Embrace the Dark Side')
        page.discussion_thread.add_post(text='Nope')
        page = WM.Page.upsert('The Empire Strikes Back')
        page.text = 'Star Wars Episode V: The Empire Strikes Back'
        page.commit()
        page = WM.Page.upsert('Return of the Jedi')
        page.text = 'Star Wars Episode VI: Return of the Jedi'
        page.commit()
        page = WM.Page.query.get(app_config_id=self.wiki.config._id, title='Home')
        page.deleted = True
        page.commit()

    def test_bulk_export(self):
        # Clear out some context vars, to properly simulate how this is run from the export task
        # Besides, it's better not to need c context vars
        c.app = c.project = None

        f = tempfile.TemporaryFile()
        self.wiki.bulk_export(f)
        f.seek(0)
        wiki = json.loads(f.read())
        pages = sorted(wiki['pages'], key=operator.itemgetter('title'))
        assert_equal(len(pages), 3)
        assert_equal(pages[0]['title'], 'A New Hope')
        assert_equal(pages[0]['text'], 'Star Wars Episode IV: A New Hope')
        assert_equal(pages[0]['mod_date'], '2013-07-05 00:00:00')
        assert_equal(pages[0]['labels'], ['star wars', 'movies'])
        assert_equal(len(pages[0]['discussion_thread']['posts']), 2)

        assert_equal(pages[1]['title'], 'Return of the Jedi')
        assert_equal(pages[1]['text'], 'Star Wars Episode VI: Return of the Jedi')
        assert_equal(len(pages[1]['discussion_thread']['posts']), 0)

        assert_equal(pages[2]['title'], 'The Empire Strikes Back')
        assert_equal(pages[2]['text'], 'Star Wars Episode V: The Empire Strikes Back')
        assert_equal(len(pages[2]['discussion_thread']['posts']), 0)

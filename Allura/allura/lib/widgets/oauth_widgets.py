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

from pylons import tmpl_context as c

import ew as ew_core
import ew.jinja2_ew as ew

from allura.lib import validators as V
from allura import model as M

from .form_fields import AutoResizeTextarea
from .forms import ForgeForm

class OAuthApplicationForm(ForgeForm):
    submit_text='Register new application'
    style='wide'
    class fields(ew_core.NameList):
        application_name =ew.TextField(label='Application Name',
                                       validator=V.UniqueOAuthApplicationName())
        application_description = AutoResizeTextarea(label='Application Description')

class OAuthRevocationForm(ForgeForm):
    submit_text='Revoke Access'
    fields = []
    class fields(ew_core.NameList):
        _id=ew.HiddenField()


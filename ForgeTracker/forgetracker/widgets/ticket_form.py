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

import shlex

from pylons import tmpl_context as c
from formencode import validators as fev

import ew as ew_core
import ew.jinja2_ew as ew

from allura import model as M
from allura.lib.widgets import form_fields as ffw
from allura.lib import helpers as h

class TicketCustomFields(ew.CompoundField):
    template='jinja:forgetracker:templates/tracker_widgets/ticket_custom_fields.html'

    def __init__(self, *args, **kwargs):
        super(TicketCustomFields, self).__init__(*args, **kwargs)
        self._fields = None
        self._custom_fields_values = {}

    def context_for(self, field):
        response = super(TicketCustomFields, self).context_for(field)
        response['value'] = self._custom_fields_values.get(field.name)
        return response

    @property
    def fields(self):
        # milestone is kind of special because of the layout
        # add it to the main form rather than handle with the other customs
        if self._fields is None:
            self._fields = []
            for cf in c.app.globals.custom_fields:
                if cf.name != '_milestone':
                    self._fields.append(TicketCustomField.make(cf))
        return self._fields

class GenericTicketForm(ew.SimpleForm):
    defaults=dict(
        ew.SimpleForm.defaults,
        name="ticket_form",
        submit_text='Save',
        ticket=None,
        show_comment=False)

    def display_field_by_name(self, idx, ignore_errors=False):
        field = self.fields[idx]
        ctx = self.context_for(field)
        if idx == 'assigned_to':
            self._add_current_value_to_user_field(field, ctx.get('value'))
        elif idx == 'custom_fields':
            field._custom_fields_values = ctx.get('value') or {}
            for cf in c.app.globals.custom_fields:
                if cf and cf.type == 'user':
                    val = ctx.get('value')
                    user = val.get(cf.name) if val else None
                    for f in field.fields:
                        if f.name == cf.name:
                            self._add_current_value_to_user_field(f, user)

        display = field.display(**ctx)
        if ctx['errors'] and field.show_errors and not ignore_errors:
            display = "%s<div class='error'>%s</div>" % (display, ctx['errors'])
        return display

    def _add_current_value_to_user_field(self, field, user):
        """Adds current field's value to `ProjectUserCombo` options.

        This is done to be able to select default value when widget loads,
        since normally `ProjectUserCombo` shows without any options, and loads
        them asynchronously (via ajax).
        """
        if isinstance(user, basestring):
            user = M.User.by_username(user)
        if user and user != M.User.anonymous():
            field.options = [
                ew.Option(
                    py_value=user.username,
                    label='%s (%s)' % (user.display_name, user.username))
            ]

    @property
    def fields(self):
        fields = [
            ew.TextField(name='summary', label='Title',
                attrs={'style':'width: 425px','placeholder':'Title'},
                validator=fev.UnicodeString(not_empty=True, messages={'empty':"You must provide a Title"})),
            ffw.MarkdownEdit(label='Description',name='description',
                    attrs={'style':'width: 95%'}),
            ew.SingleSelectField(name='status', label='Status',
                options=lambda: c.app.globals.all_status_names.split()),
            ffw.ProjectUserCombo(name='assigned_to', label='Owner'),
            ffw.LabelEdit(label='Labels',name='labels', className='ticket_form_tags'),
            ew.Checkbox(name='private', label='Mark as Private', attrs={'class':'unlabeled'}),
            ew.InputField(name='attachment', label='Attachment', field_type='file', validator=fev.FieldStorageUploadConverter(if_missing=None)),
            ffw.MarkdownEdit(name='comment', label='Comment',
                        attrs={'style':'min-height:7em; width:97%'}),
            ew.SubmitButton(label=self.submit_text,name='submit',
                attrs={'class':"ui-button ui-widget ui-state-default ui-button-text-only"}),
            ew.HiddenField(name='ticket_num', validator=fev.Int(if_missing=None)),
        ]
        # milestone is kind of special because of the layout
        # add it to the main form rather than handle with the other customs
        if c.app.globals.custom_fields:
            for cf in c.app.globals.custom_fields:
                if cf.name == '_milestone':
                    fields.append(TicketCustomField.make(cf))
                    break
        return ew_core.NameList(fields)

class TicketForm(GenericTicketForm):
    template='jinja:forgetracker:templates/tracker_widgets/ticket_form.html'
    @property
    def fields(self):
        fields = ew_core.NameList(super(TicketForm, self).fields)
        if c.app.globals.custom_fields:
            fields.append(TicketCustomFields(name="custom_fields"))
        return fields

    def resources(self):
        for r in super(TicketForm, self).resources(): yield r
        yield ew.JSScript('''
        $(function(){
            $('#show_attach input').click(function(){
                $('#view_attach').show();
                $('#show_attach').hide();
            });
            $('form').submit(function() {
                var value = $('div.tagsinput div input').val();
                var exists = $('input.label_edit').tagExist(value);
                var default_value =$('div.tagsinput div input').attr('data-default');
                if ((value != default_value) && (!exists) && value != ''){
                    $('input.label_edit').addTag(value);
                }
                $('input[type=submit]', this).attr('disabled', 'disabled');
            });
            $('div.reply.discussion-post a.markdown_preview').click(function(){
                var arrow = $(this).closest('.discussion-post').find('span.arw');
                arrow.hide();
            });
            $('div.reply.discussion-post a.markdown_edit').click(function(){
                var arrow = $(this).closest('.discussion-post').find('span.arw');
                arrow.show();
            });
        });''')

class TicketCustomField(object):

    def _select(field):
        options = []
        field_options = h.really_unicode(field.options)
        try:
            # shlex have problems with parsing unicode,
            # it's better to pass properly encoded byte-string
            field_options = shlex.split(field_options.encode('utf-8'))
            # convert splitted string back to unicode
            field_options = map(h.really_unicode, field_options)
        except ValueError:
            field_options = field_options.split()
            # After regular split field_options might contain a " characters,
            # which would break html when rendered inside tag's value attr.
            # Escaping doesn't help here, 'cause it breaks EasyWidgets' validation,
            # so we're getting rid of those.
            field_options = [o.replace('"', '') for o in field_options]
        for opt in field_options:
            selected = False
            if opt.startswith('*'):
                opt = opt[1:]
                selected = True
            options.append(ew.Option(label=opt,html_value=opt,py_value=opt,selected=selected))
        return ew.SingleSelectField(label=field.label, name=str(field.name), options=options)

    def _milestone(field):
        options = []
        for m in field.milestones:
            options.append(ew.Option(
                label=m.name,
                py_value=m.name,
                complete=bool(m.complete)))

        ssf = MilestoneField(
            label=field.label, name=str(field.name),
            options=options)
        return ssf

    def _boolean(field):
        return ew.Checkbox(label=field.label, name=str(field.name), suppress_label=True)

    def _number(field):
        return ew.NumberField(label=field.label, name=str(field.name))

    def _user(field):
        return ffw.ProjectUserCombo(label=field.label, name=str(field.name))

    @staticmethod
    def _default(field):
        return ew.TextField(label=field.label, name=str(field.name))

    SELECTOR = dict(
        select=_select,
        milestone=_milestone,
        boolean=_boolean,
        number=_number,
        user=_user)

    @classmethod
    def make(cls, field):
        factory = cls.SELECTOR.get(field.get('type'), cls._default)
        return factory(field)

class MilestoneField(ew.SingleSelectField):
    template=ew.Snippet('''<select {{widget.j2_attrs({
               'id':id,
               'name':rendered_name,
               'multiple':multiple,
               'class':css_class},
               attrs)}}>
            {% for o in open_milestones %}
            <option{% if o.selected%} selected{% endif %} value="{{o.html_value}}">{{o.label|e}}</option>
            {% endfor %}
            {% if closed_milestones %}
            <optgroup label="Closed">
                {% for o in closed_milestones %}
                <option{% if o.selected%} selected{% endif %} value="{{o.html_value}}">{{o.label|e}}</option>
                {% endfor %}
            </optgroup>
            {% endif %}
        </select>''', 'jinja2')

    def prepare_context(self, context):
        context = super(MilestoneField, self).prepare_context(context)

        # group open / closed milestones
        context['open_milestones'] = [opt for opt in self.options if not opt.complete]
        context['closed_milestones'] = [opt for opt in self.options if opt.complete]

        # filter closed milestones entirely
        #value = context['value']
        #context['options'] = [opt for opt in self.options if not opt.complete or value == opt.py_value]

        return context

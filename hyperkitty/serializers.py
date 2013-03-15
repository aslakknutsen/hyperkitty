#-*- coding: utf-8 -*-
# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
#
# This file is part of HyperKitty.
#
# HyperKitty is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# HyperKitty is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# HyperKitty.  If not, see <http://www.gnu.org/licenses/>.
#

from rest_framework import serializers
from rest_framework.fields import Field
from rest_framework import pagination
from rest_framework.reverse import reverse


class CustomLink(Field):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def field_to_native(self, obj, field):
        resolved_args = {}
        for k in self.args:
            v = self.args.get(k)

            # Support sub expressions (parent.child.child)
            tmp_obj = obj
            for component in v.split('.'):
                value = getattr(tmp_obj, component)
                if value is None:
                    return None
                tmp_obj = value

            resolved_args[k] = value

        request = self.context['request']
        url = reverse(self.name, kwargs=resolved_args, request=request)

        if "format" in request.GET and request.GET["format"] == "api":
            url = url + "?format=api"
        return url


class CustomTemplateLink(Field):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def field_to_native(self, obj, field):
        request = self.context['request']
        url = reverse(self.name, kwargs=self.args, request=request)
        for k in self.args:
            v = self.args[k]
            url = url.replace(v, "{" + k + "}")
        return url


class CustomLinks(serializers.Serializer):
    def __init__(self, args):
        self.args = args
        super(serializers.Serializer, self).__init__(source="*")

    def get_fields(self):
        return self.args


class ListLinkSerializer(serializers.Serializer):
    name = serializers.EmailField(source="list_name")
    links = CustomLinks(
        {
            "self": CustomLink(
                "api_list",
                {
                    "mlist_fqdn": "list_name"
                })
        })


class ThreadSummarySerializer(serializers.Serializer):
    subject = serializers.CharField()
    last_active = serializers.DateTimeField(source="date_active")
    list = ListLinkSerializer(source="*")
    links = CustomLinks(
        {
            "self": CustomLink(
                "api_thread",
                {
                    "mlist_fqdn": "list_name",
                    "threadid": "thread_id"
                })
        })


class ListStatsSerializer(serializers.Serializer):
    message_activitty = serializers.CharField(source="dates")


class ListSummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()

    links = CustomLinks(
        {
            "self": CustomLink(
                "api_list",
                {
                    "mlist_fqdn": "name"
                }),
            "stat": CustomLink(
                "api_list_stat",
                {
                    "mlist_fqdn": "name"
                }),
            "templates": CustomLinks(
                {
                    "search": CustomTemplateLink(
                        "api_search",
                        {
                            "mlist_fqdn": "x@exmple.org",
                            "field": "Subject",
                            "keyword": "XX"
                        }),
                    "archive_by_month": CustomTemplateLink(
                        "api_threads_with_month",
                        {
                            "mlist_fqdn": "x@exmple.org",
                            "year": "2013",
                            "month": "01"
                        }),
                    "archive_by_day": CustomTemplateLink(
                        "api_threads_with_day",
                        {
                            "mlist_fqdn": "x@exmple.org",
                            "year": "9999",
                            "month": "99",
                            "day": "99"
                        })
                })
        })


class ListSerializer(ListSummarySerializer):
    top_threads = ThreadSummarySerializer(many=True)
    active_threads = ThreadSummarySerializer(many=True)


class AttachmentSerializer(serializers.Serializer):
    name = serializers.CharField()
    content_type = serializers.CharField()
    encoding = serializers.CharField()
    size = serializers.IntegerField()
    links = CustomLinks(
        {
            "raw": CustomLink(
                "api_message_attachment",
                {
                    "mlist_fqdn": "list_name",
                    "message_id_hash": "email.message_id_hash",
                    "counter": "counter"
                })
        })


class AuthorSerializer(serializers.Serializer):
    name = serializers.CharField(source="sender_name")
    email = serializers.CharField(source="sender_email")


class MessageSerializer(serializers.Serializer):
    author = AuthorSerializer(source="*")
    subject = serializers.CharField()
    date = serializers.DateTimeField()
    timezone = serializers.CharField()
    thread_order = serializers.IntegerField()
    thread_depth = serializers.IntegerField()
    content = serializers.CharField()
    attachments = AttachmentSerializer()
    list = ListLinkSerializer(source="*")
    links = CustomLinks(
        {
            "self": CustomLink(
                "api_message",
                {
                    "mlist_fqdn": "list_name",
                    "message_id_hash": "message_id_hash"
                }),
            "in_reply_to": CustomLink(
                "api_message",
                {
                    "mlist_fqdn": "list_name",
                    "message_id_hash": "reply_to.message_id_hash"
                }),
            "raw": CustomLink(
                "api_message_raw",
                {
                    "mlist_fqdn": "list_name",
                    "message_id_hash": "message_id_hash"
                }),
            "thread": CustomLink(
                "api_thread",
                {
                    "mlist_fqdn": "list_name",
                    "threadid": "thread_id"
                })
        })


class MessageLinkSerializer(serializers.Serializer):
    author = AuthorSerializer(source="*")
    date = serializers.DateTimeField()
    timezone = serializers.CharField()
    links = CustomLinks(
        {
            "self": CustomLink(
                "api_message",
                {
                    "mlist_fqdn": "list_name",
                    "message_id_hash": "message_id_hash"
                }),
            "raw": CustomLink(
                "api_message_raw",
                {
                    "mlist_fqdn": "list_name",
                    "message_id_hash": "message_id_hash"
                }),
            "thread": CustomLink(
                "api_thread",
                {
                    "mlist_fqdn": "list_name",
                    "threadid": "thread_id"
                })
        })


class ThreadSerializer(serializers.Serializer):
    subject = serializers.CharField()
    last_active = serializers.DateTimeField(source="date_active")
    first_post = MessageLinkSerializer(source="starting_email")
    list = ListLinkSerializer(source="*")
    participants = serializers.CharField()
    messages = MessageLinkSerializer(source="emails_by_reply")


class PaginatedHKSerializer(pagination.PaginationSerializer):
    page_number = serializers.IntegerField(source="number")
    number_of_pages = serializers.IntegerField(source="paginator.num_pages")
    start_index = serializers.IntegerField()
    end_index = serializers.IntegerField()


class PaginatedThreadSerializer(PaginatedHKSerializer):
    """
    Serializes page objects of threads.
    """
    class Meta:
        object_serializer_class = ThreadSummarySerializer


class PaginatedMessageLinkSerializer(PaginatedHKSerializer):
    """
    Serializes page objects of messages.
    """
    class Meta:
        object_serializer_class = MessageLinkSerializer

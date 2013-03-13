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

import datetime
from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ParseError

from django.http import HttpResponse, HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework.reverse import reverse

from hyperkitty.lib import get_store, get_display_dates, daterange
from hyperkitty.serializers import *


class ListsResource(APIView):
    """
    Resource used to retrieve lists from the archives using the REST API.

    :status 404: If no lists are found
    """

    def get(self, request):
        store = get_store(request)
        lists = store.get_lists()
        if not lists:
            return Response(status=404)
        else:
            return Response(ListSummarySerializer(lists, many=True, context={'request': request}).data)


class ListResource(APIView):
    """
    Resource used to retrieve a list from the archives using the REST API.

    :param mlist_fqdn: Fully qualified List name

    :status 404: If no list is found
    """

    def get(self, request, mlist_fqdn):
        store = get_store(request)
        lists = store.get_list(mlist_fqdn)

        if not lists:
            return Response(status=404)

        # Get stats for last 30 days
        today = datetime.datetime.utcnow()
        # the upper boundary is excluded in the search, add one day
        end_date = today + datetime.timedelta(days=1)
        begin_date = end_date - datetime.timedelta(days=32)

        threads = store.get_threads(list_name=lists.name, start=begin_date, end=end_date)

        # top threads are the one with the most answers
        top_threads = sorted(threads, key=lambda t: len(t), reverse=True)[:5]

        # active threads are the ones that have the most recent posting
        active_threads = sorted(threads, key=lambda t: t.date_active, reverse=True)[:5]

        lists.top_threads = top_threads
        lists.active_threads = active_threads

        return Response(ListSerializer(lists, context={'request': request}).data)


class ListStatResource(APIView):
    """
    Resource used to retrieve statistics for a list using the REST API.

    Shows the last 30 days message activity grouped by day.

    :param mlist_fqdn: Fully qualified List name

    :status 404: If no list is found
    """

    def get(self, request, mlist_fqdn):
        store = get_store(request)
        mlist = store.get_list(mlist_fqdn)

        if not mlist:
            return Response(status=404)

        # Get stats for last 30 days
        today = datetime.datetime.utcnow()
        # the upper boundary is excluded in the search, add one day
        end_date = today + datetime.timedelta(days=1)
        begin_date = end_date - datetime.timedelta(days=32)

        # List activity
        # Use get_messages and not get_threads to count the emails, because
        # recently active threads include messages from before the start date
        emails_in_month = store.get_messages(list_name=mlist.name,
                                             start=begin_date, end=end_date)
        dates = defaultdict(lambda: 0)  # no activity by default
        # populate with all days before adding data.
        for single_date in daterange(begin_date, end_date):
            dates[single_date.strftime("%Y-%m-%d")] = 0

        for email in emails_in_month:
            date_str = email.date.strftime("%Y-%m-%d")
            dates[date_str] = dates[date_str] + 1

        stats = {"dates": dates}

        return Response(ListStatsSerializer(stats, context={'request': request}).data)


class AttachmentRawResource(APIView):
    """
    Resource used to retrieve RAW attachments using the REST API.

    :param mlist_fqdn: Fully qualified List name
    :param messageid: Fully qualified Message id
    :param counter: The counter within the message for this attachment

    :status 404: If no attchment is found
    """

    def get(self, request, mlist_fqdn, messageid, counter):
        store = get_store(request)
        attachment = store.get_attachment_by_counter(mlist_fqdn, messageid, int(counter))

        if not attachment:
            return Response(status=404)
        else:
            return HttpResponse(attachment.content, mimetype=attachment.content_type)


class EmailResource(APIView):
    """
    Resource used to retrieve emails from the archives using the REST API.

    :param mlist_fqdn: Fully qualified List name
    :param messageid: Fully qualified Message id

    :status 404: If no Email is found
    """

    def get(self, request, mlist_fqdn, messageid):
        store = get_store(request)
        email = store.get_message_by_id_from_list(mlist_fqdn, messageid)

        if not email:
            return Response(status=404)
        else:
            return Response(EmailSerializer(email, context={'request': request}).data)


class EmailRawResource(APIView):
    """
    Resource used to retrieve RAW plain/text message using the REST API.

    :param mlist_fqdn: Fully qualified List name
    :param messageid: Fully qualified Message id

    :status 404: If no Raw email is found
    """

    def get(self, request, mlist_fqdn, messageid):
        store = get_store(request)
        email = store.get_message_by_id_from_list(mlist_fqdn, messageid)
        if not email:
            return Response(status=404)
        else:
            return HttpResponse(email.full, mimetype="text/plain")


class ThreadsResource(APIView):
    """
    Resource used to retrieve threads from the archives using the REST API.

    The Resource is Paginated with a size of 20.

    :param mlist_fqdn: Fully qualified List name
    :param year: Limit the result by year
    :param month: Limit the result by month
    :param day: Limit the result by day

    :status 404: If no threads are found
    """

    def get(self, request, mlist_fqdn, year=None, month=None, day=None):
        store = get_store(request)

        begin_date, end_date = get_display_dates(year, month, day)
        threads = store.get_threads(mlist_fqdn, begin_date, end_date)

        paginator = Paginator(threads, 20)
        page_num = request.GET.get('page')
        try:
            threads = paginator.page(page_num)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            threads = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            threads = paginator.page(paginator.num_pages)

        if not threads:
            return Response(status=404)
        else:
            return Response(
                PaginatedThreadSerializer(
                    instance=threads, context={'request': request}).data)


class ThreadResource(APIView):
    """
    Resource used to retrieve threads from the archives using the REST API.

    :param mlist_fqdn: Fully qualified List name
    :param threadid: Fully qualified Thread id

    :status 404: If no thread is found
    """

    def get(self, request, mlist_fqdn, threadid):
        store = get_store(request)
        thread = store.get_thread(mlist_fqdn, threadid)
        if not thread:
            return Response(status=404)
        else:
            return Response(ThreadSerializer(thread, context={'request': request}).data)


class SearchResource(APIView):
    """
    Resource used to search the archives using the REST API.

    :param mlist_fqdn: Fully qualified List name
    :param field: Field to search. Allowed values are:
                    Subject:
                        The Email Subject line
                    Content:
                        The Email Body
                    SubjectContent:
                        The Email Subject line and Body
                    From:
                        The Senders Email or Name

    :status 404: If no emails are found
    """

    def get(self, request, mlist_fqdn, field, keyword):
        fields = ['Subject', 'Content', 'SubjectContent', 'From']
        if field not in fields:
            raise ParseError(detail="Unknown field: " + field + ". Supported fields are " + ", ".join(fields))

        store = get_store(request)
        threads = None
        if field == 'Subject':
            threads = store.search_list_for_subject(mlist_fqdn, keyword)
        elif field == 'Content':
            threads = store.search_list_for_content(mlist_fqdn, keyword)
        elif field == 'SubjectContent':
            threads = store.search_list_for_content_subject(mlist_fqdn, keyword)
        elif field == 'From':
            threads = store.search_list_for_sender(mlist_fqdn, keyword)

        threads = list(threads)

        paginator = Paginator(threads, 20)
        page_num = request.GET.get('page')
        try:
            threads = paginator.page(page_num)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            threads = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            threads = paginator.page(paginator.num_pages)

        if not threads:
            return Response(status=404)
        else:
            return Response(
                PaginatedEmailLinkSerializer(
                    instance=threads, context={'request': request}).data)


# Compatibility Resources with old REST APIView

class CompatEmailResource(APIView):
    """
    Compatibility Resource for old EmailResource API.

    See EmailResource.

    Redirects to new URL.
    """

    def get(self, request, mlist_fqdn, messageid):
        args = {
            "mlist_fqdn": mlist_fqdn,
            "messageid": messageid
        }
        return HttpResponseRedirect(reverse("api_email", kwargs=args, request=request))


class CompatThreadResource(APIView):
    """
    Compatibility Resource for old ThreadResource API.

    See ThreadResource.

    Redirects to new URL.
    """

    def get(self, request, mlist_fqdn, threadid):
        args = {
            "mlist_fqdn": mlist_fqdn,
            "threadid": threadid
        }
        return HttpResponseRedirect(reverse("api_thread", kwargs=args, request=request))


class CompatSearchResource(APIView):
    """
    Compatibility Resource for old SearchResource API.

    See SearchResource.

    Redirects to new URL.
    """

    def get(self, request, mlist_fqdn, field, keyword):
        args = {
            "mlist_fqdn": mlist_fqdn,
            "field": field,
            "keyword": keyword
        }
        return HttpResponseRedirect(reverse("api_search", kwargs=args, request=request))

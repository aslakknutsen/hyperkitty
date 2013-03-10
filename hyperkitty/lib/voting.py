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
# Author: Aurelien Bompard <abompard@fedoraproject.org>
#


from hyperkitty.models import Rating


def _count_votes(votes, user=None):
    """Group all given votes"""
    likes = dislikes = 0
    myvote = 0
    for vote in votes:
        if vote.vote == 1:
            likes += 1
        elif vote.vote == -1:
            dislikes += 1
        if user is not None and user.is_authenticated() and vote.user == user:
            myvote = vote.vote
    return likes, dislikes, myvote


def _fetch_votes_for_message(message_id_hash):
    """Extract all the votes for this message"""

    try:
        votes = Rating.objects.filter(messageid=message_id_hash)
    except Rating.DoesNotExist:
        votes = {}
    return votes


def _fetch_votes_for_thread(threadid):
    """Extract all the votes for this thread"""

    try:
        votes = Rating.objects.filter(threadid=threadid)
    except Rating.DoesNotExist:
        votes = {}
    return votes


def _set_count_votes(message, votes, user=None):
    """ Group all the votes for this message """

    message.likes, message.dislikes, message.myvote = \
        _count_votes(votes, user)

    message.likestatus = "neutral"
    if message.likes - message.dislikes >= 10:
        message.likestatus = "likealot"
    elif message.likes - message.dislikes > 0:
        message.likestatus = "like"
    #elif message.likes - message.dislikes < 0:
    #    message.likestatus = "dislike"


def get_votes(message_id_hash, user=None):
    """Extract all the votes for this message"""

    return _count_votes(_fetch_votes_for_message(message_id_hash), user)


def get_votes_for_thread(threadid, user=None):
    """Extract all the votes for this message"""

    return _count_votes(_fetch_votes_for_thread(threadid), user)


def set_votes(thread, votes, user=None):
    """Extract all the votes for this thread"""

    _set_count_votes(
        thread,
        votes,
        user)


def set_thread_votes(thread, user=None):
    """Extract all the votes for this thread"""

    _set_count_votes(
        thread,
        _fetch_votes_for_thread(thread.thread_id),
        user)


def set_message_votes(message, user=None):
    """Extract all the votes for this message"""

    _set_count_votes(
        message,
        _fetch_votes_for_message(message.message_id_hash),
        user)


def set_messages_votes(messages, threadid, user=None):
    """Extract all the votes pr message in thread"""

    votes = _fetch_votes_for_thread(threadid)
    for message in messages:
        _set_count_votes(
            message,
            [i for i in votes if unicode(i.messageid) == message.message_id_hash],
            user)

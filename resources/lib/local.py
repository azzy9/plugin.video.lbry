# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmcaddon
import xbmcvfs
import xbmcgui

from resources.lib.general import *

ADDON = xbmcaddon.Addon()

def get_profile_path(rpath):

    """ Gets Profile Path """

    return translate_path( ADDON.getAddonInfo('profile') + rpath )

def get_stream_headers():

    """ Gets stream headers - placeholder """

    return ''

def load_channel_subs():
    channels = []
    try:
        f = xbmcvfs.File(get_profile_path('channel_subs'), 'r')
        lines = f.readBytes()
        f.close()
    except Exception:
        pass
    lines = lines.decode('utf-8')
    for line in lines.split('\n'):
        items = line.split('#')
        if len(items) < 2:
            continue
        channels.append((items[0],items[1]))
    return channels

def save_channel_subs(channels):
    try:
        with xbmcvfs.File(get_profile_path('channel_subs'), 'w') as f:
            for (name, claim_id) in channels:
                f.write(bytearray(name.encode('utf-8')))
                f.write('#')
                f.write(bytearray(claim_id.encode('utf-8')))
                f.write('\n')
    except Exception as err:
        xbmcgui.Dialog().notification(get_string(30104), str(err), xbmcgui.NOTIFICATION_ERROR)

def load_playlist(name):
    items = []
    try:
        with xbmcvfs.File(get_profile_path(name + '.list'), 'r') as f:
            lines = f.readBytes()
    except Exception:
        pass
    lines = lines.decode('utf-8')
    for line in lines.split('\n'):
        if line != '':
            items.append(line)
    return items

def save_playlist(name, items):
    try:
        with xbmcvfs.File(get_profile_path(name + '.list'), 'w') as f:
            for item in items:
                f.write(bytearray(item.encode('utf-8')))
                f.write('\n')
    except Exception as err:
        xbmcgui.Dialog().notification(get_string(30104), str(err), xbmcgui.NOTIFICATION_ERROR)

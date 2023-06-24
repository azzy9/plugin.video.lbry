# -*- coding: utf-8 -*-
from __future__ import absolute_import

import xbmc
import xbmcaddon
from xbmcgui import ListItem, Dialog
from xbmcplugin import addDirectoryItem, addDirectoryItems, endOfDirectory, setContent, setResolvedUrl

import routing
import time

from urllib.parse import quote, unquote, quote_plus, unquote_plus

from resources.lib.exception import *
from resources.lib.comments import CommentWindow, using_lbry_proxy

ADDON = xbmcaddon.Addon()

if ADDON.getSetting( 'odysee_enable' ) == 'true':
    from resources.lib.external import *
else:
    from resources.lib.local import *
from resources.lib.general import *

if get_api_url() == '':
    raise Exception('Lbry API URL is undefined.')

# assure profile directory exists
profile_path = ADDON.getAddonInfo('profile')
if not xbmcvfs.exists(profile_path):
    xbmcvfs.mkdir(profile_path)

items_per_page = ADDON.getSettingInt('items_per_page')
nsfw = ADDON.getSettingBool('nsfw')

plugin = routing.Plugin()
ph = plugin.handle
setContent(ph, 'videos')
dialog = Dialog()

def to_video_listitem(item, playlist='', channel='', repost=None):

    line_item = ListItem(item['value']['title'] if 'title' in item['value'] else item['file_name'] if 'file_name' in item else '')
    line_item.setProperty('IsPlayable', 'true')
    if 'thumbnail' in item['value'] and 'url' in item['value']['thumbnail']:
        line_item.setArt({
            'thumb': item['value']['thumbnail']['url'],
            'poster': item['value']['thumbnail']['url'],
            'fanart': item['value']['thumbnail']['url']
        })

    info_labels = {}
    menu = []
    plot = ''
    if 'description' in item['value']:
        plot = item['value']['description']
    if 'author' in item['value']:
        info_labels['writer'] = item['value']['author']
    elif 'channel_name' in item:
        info_labels['writer'] = item['channel_name']
    if 'timestamp' in item:
        timestamp = time.localtime(item['timestamp'])
        info_labels['year'] = timestamp.tm_year
        info_labels['premiered'] = time.strftime('%Y-%m-%d',timestamp)
    if 'video' in item['value'] and 'duration' in item['value']['video']:
        info_labels['duration'] = str(item['value']['video']['duration'])

    if playlist == '':
        if 'signing_channel' in item and 'name' in item['signing_channel']:
            comment_uri = item['signing_channel']['name'] + '#' + item['signing_channel']['claim_id'] + '#' + item['claim_id']
            menu.append((
                get_string(30238), 'RunPlugin(%s)' % plugin.url_for(plugin_comment_show, uri=serialize_uri(comment_uri))
            ))

        menu.append((
            get_string(30212) % get_string(30211), 'RunPlugin(%s)' % plugin.url_for(plugin_playlist_add, name=quote(get_string(30211)), uri=serialize_uri(item))
        ))
    else:
        menu.append((
            get_string(30213) % get_string(30211), 'RunPlugin(%s)' % plugin.url_for(plugin_playlist_del, name=quote(get_string(30211)), uri=serialize_uri(item))
        ))

    menu.append((
        get_string(30208), 'RunPlugin(%s)' % plugin.url_for(claim_download, uri=serialize_uri(item))
    ))

    if 'signing_channel' in item and 'name' in item['signing_channel']:
        ch_name = item['signing_channel']['name']
        #ch_claim = item['signing_channel']['claim_id']
        ch_title = ''
        if 'value' in item['signing_channel'] and 'title' in item['signing_channel']['value']:
            ch_title = item['signing_channel']['value']['title']

        plot = '[B]' + (ch_title if ch_title.strip() != '' else ch_name) + '[/B]\n' + plot

        info_labels['studio'] = ch_name

        if channel == '':
            menu.append((
                get_string(30207) % ch_name, 'Container.Update(%s)' % plugin.url_for(lbry_channel, uri=serialize_uri(item['signing_channel']),page=1)
            ))
        menu.append((
            get_string(30205) % ch_name, 'RunPlugin(%s)' % plugin.url_for(plugin_follow, uri=serialize_uri(item['signing_channel']))
        ))

    if repost is not None:
        if 'signing_channel' in repost and 'name' in repost['signing_channel']:
            plot = (('[COLOR yellow]%s[/COLOR]\n' % get_string(30217)) % repost['signing_channel']['name']) + plot
        else:
            plot = ('[COLOR yellow]%s[/COLOR]\n' % get_string(30216)) + plot

    info_labels['plot'] = plot
    item_set_info( line_item, info_labels )
    line_item.addContextMenuItems(menu)

    return line_item

def result_to_itemlist(result, playlist='', channel=''):

    items = []

    for item in result:
        if not 'value_type' in item:
            xbmc.log(str(item))
            continue
        if item['value_type'] == 'stream' and 'stream_type' in item['value'] and item['value']['stream_type'] == 'video':
            # nsfw?
            if 'tags' in item['value']:
                if 'mature' in item['value']['tags'] and not nsfw:
                    continue

            line_item = to_video_listitem(item, playlist, channel)
            url = plugin.url_for(claim_play, uri=serialize_uri(item))

            items.append((url, line_item))
        elif item['value_type'] == 'repost' and 'reposted_claim' in item and item['reposted_claim']['value_type'] == 'stream' and item['reposted_claim']['value']['stream_type'] == 'video':
            stream_item = item['reposted_claim']
            # nsfw?
            if 'tags' in stream_item['value']:
                if 'mature' in stream_item['value']['tags'] and not nsfw:
                    continue

            line_item = to_video_listitem(stream_item, playlist, channel, repost=item)
            url = plugin.url_for(claim_play, uri=serialize_uri(stream_item))

            items.append((url, line_item))
        elif item['value_type'] == 'channel':
            line_item = ListItem('[B]%s[/B] [I]#%s[/I]' % (item['name'], item['claim_id'][0:4]))
            line_item.setProperty('IsFolder','true')
            if 'thumbnail' in item['value'] and 'url' in item['value']['thumbnail']:
                line_item.setArt({
                    'thumb': item['value']['thumbnail']['url'],
                    'poster': item['value']['thumbnail']['url'],
                    'fanart': item['value']['thumbnail']['url']
                })
            url = plugin.url_for(lbry_channel, uri=serialize_uri(item),page=1)

            menu = []
            ch_name = item['name']
            menu.append((
                get_string(30205) % ch_name, 'RunPlugin(%s)' % plugin.url_for(plugin_follow, uri=serialize_uri(item))
            ))
            line_item.addContextMenuItems(menu)

            items.append((url, line_item, True))
        else:
            xbmc.log('ignored item, value_type=' + item['value_type'])
            xbmc.log('item name=' + item['name'])

    return items

def set_user_channel(channel_name, channel_id):
    ADDON.setSettingString('user_channel', "%s#%s" % (channel_name, channel_id))
    ADDON.setSettingString('user_channel_vis', "%s#%s" % (channel_name, channel_id[:5]))

@plugin.route('/clear_user_channel')
def clear_user_channel():
    ADDON.setSettingString('user_channel', '')
    ADDON.setSettingString('user_channel_vis', '')

@plugin.route('/select_user_channel')
def select_user_channel():

    progress_dialog = xbmcgui.DialogProgress()
    progress_dialog.create(get_string(30231))

    page = 1
    total_pages = 1
    items = []
    while page <= total_pages:
        if progress_dialog.iscanceled():
            break

        try:
            params = {'page' : page}
            result = call_rpc('channel_list', params, errdialog=not using_lbry_proxy)
            total_pages = max(result['total_pages'], 1) # Total pages returns 0 if empty
            if 'items' in result:
                items += result['items']
            else:
                break
        except Exception:
            pass

        page = page + 1
        progress_dialog.update(
            int(100.0*page/total_pages), get_string(30220) + ' %s/%s' % (page, total_pages)
        )

    selected_item = None

    if len(items) == 0:
        progress_dialog.update(100, get_string(30232)) # No owned channels found
        xbmc.sleep(1000)
        progress_dialog.close()
        return

    if len(items) == 1:
        progress_dialog.update(100, get_string(30233)) # Found single user
        xbmc.sleep(1000)
        progress_dialog.close()

        selected_item = items[0]
    else:
        progress_dialog.update(100, get_string(30234)) # Multiple users found
        xbmc.sleep(1000)
        progress_dialog.close()

        names = []
        for item in items:
            names.append(item['name'])

        selected_name_index = dialog.select(get_string(30239), names) # Post As

        if selected_name_index >= 0: # If not cancelled
            selected_item = items[selected_name_index]

    if selected_item:
        set_user_channel(selected_item['name'], selected_item['claim_id'])

@plugin.route('/')
def lbry_root():
    addDirectoryItem(ph, plugin.url_for(plugin_recent, page=1), ListItem(get_string(30218)), True)
    addDirectoryItem(ph, plugin.url_for(plugin_follows), ListItem(get_string(30200)), True)
    #addDirectoryItem(ph, plugin.url_for(plugin_playlists), ListItem(get_string(30210)), True)
    addDirectoryItem(ph, plugin.url_for(plugin_playlist, name=quote_plus(get_string(30211))), ListItem(get_string(30211)), True)
    #addDirectoryItem(ph, plugin.url_for(lbry_new, page=1), ListItem(get_string(30202)), True)
    addDirectoryItem(ph, plugin.url_for(lbry_search), ListItem(get_string(137)), True)

    wallet_balance = get_wallet_balance()

    if wallet_balance is not False:
        addDirectoryItem(ph, '', ListItem('Wallet: ' + wallet_balance), True)

    addDirectoryItem(ph, plugin.url_for(settings), ListItem(get_string(5)), True)
    endOfDirectory(ph)

#@plugin.route('/playlists')
#def plugin_playlists():
#    addDirectoryItem(ph, plugin.url_for(plugin_playlist, name=quote_plus(get_string(30211))), ListItem(get_string(30211)), True)
#    endOfDirectory(ph)

@plugin.route('/playlist/list/<name>')
def plugin_playlist(name):
    name = unquote_plus(name)
    uris = load_playlist(name)
    claim_info = call_rpc('resolve', {'urls': uris})
    items = []
    for uri in uris:
        items.append(claim_info[uri])
    items = result_to_itemlist(items, playlist=name)
    addDirectoryItems(ph, items, items_per_page)
    endOfDirectory(ph)

@plugin.route('/playlist/add/<name>/<uri>')
def plugin_playlist_add(name,uri):
    name = unquote_plus(name)
    uri = deserialize_uri(uri)
    items = load_playlist(name)
    if not uri in items:
        items.append(uri)
    save_playlist(name, items)

@plugin.route('/playlist/del/<name>/<uri>')
def plugin_playlist_del(name,uri):
    name = unquote_plus(name)
    uri = deserialize_uri(uri)
    items = load_playlist(name)
    items.remove(uri)
    save_playlist(name, items)
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/follows')
def plugin_follows():
    channels = load_channel_subs()
    resolve_uris = []
    for (name,claim_id) in channels:
        resolve_uris.append(name+'#'+claim_id)
    channel_infos = call_rpc('resolve', {'urls': resolve_uris})

    for (name,claim_id) in channels:
        uri = name+'#'+claim_id
        channel_info = channel_infos[uri]
        li = ListItem(name)
        if not 'error' in channel_info:
            plot = ''
            if 'title' in channel_info['value'] and channel_info['value']['title'].strip() != '':
                plot = '[B]%s[/B]\n' % channel_info['value']['title']
            else:
                plot = '[B]%s[/B]\n' % channel_info['name']
            if 'description' in channel_info['value']:
                plot = plot + channel_info['value']['description']
            infoLabels = { 'plot': plot }
            item_set_info( li, infoLabels )

            thumbnail_url = channel_info.get('value', {}).get('thumbnail',{}).get('url', '')
            cover_url = channel_info.get('value', {}).get('cover',{}).get('url', thumbnail_url)

            li.setArt({
                'thumb': thumbnail_url,
                'poster': thumbnail_url,
                'fanart': cover_url,
            })
        menu = []
        menu.append((
            get_string(30206) % name, 'RunPlugin(%s)' % plugin.url_for(plugin_unfollow, uri=serialize_uri(uri))
        ))
        li.addContextMenuItems(menu)
        addDirectoryItem(ph, plugin.url_for(lbry_channel, uri=serialize_uri(uri), page=1), li, True)
    endOfDirectory(ph)

@plugin.route('/recent/<page>')
def plugin_recent(page):
    page = int(page)
    channels = load_channel_subs()
    channel_ids = []
    for (name,claim_id) in channels:
        channel_ids.append(claim_id)
    query = {'page': page, 'page_size': items_per_page, 'order_by': 'release_time', 'channel_ids': channel_ids}
    if not ADDON.getSettingBool('server_filter_disable'):
        query['stream_types'] = ['video']
    result = call_rpc('claim_search', query)
    items = result_to_itemlist(result['items'])
    addDirectoryItems(ph, items, result['page_size'])
    total_pages = int(result['total_pages'])
    if total_pages > 1 and page < total_pages:
        addDirectoryItem(ph, plugin.url_for(plugin_recent, page=page+1), ListItem(get_string(30203)), True)
    endOfDirectory(ph)

@plugin.route('/comments/show/<uri>')
def plugin_comment_show(uri):
    params = deserialize_uri(uri).split('#')
    win = CommentWindow(
        'addon-lbry-comments.xml',
        xbmcaddon.Addon().getAddonInfo('path'),
        'Default',
        channel_name=params[0],
        channel_id=params[1],
        claim_id=params[2]
    )
    win.doModal()
    del win

@plugin.route('/follows/add/<uri>')
def plugin_follow(uri):
    add_channel_sub(uri)

@plugin.route('/follows/del/<uri>')
def plugin_unfollow(uri):
    remove_channel_sub(uri)
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/new/<page>')
def lbry_new(page):
    page = int(page)
    query = {'page': page, 'page_size': items_per_page, 'order_by': 'release_time'}
    if not ADDON.getSettingBool('server_filter_disable'):
        query['stream_types'] = ['video']
    result = call_rpc('claim_search', query)
    items = result_to_itemlist(result['items'])
    addDirectoryItems(ph, items, result['page_size'])
    total_pages = int(result['total_pages'])
    if total_pages > 1 and page < total_pages:
        addDirectoryItem(ph, plugin.url_for(lbry_new, page=page+1), ListItem(get_string(30203)), True)
    endOfDirectory(ph)

@plugin.route('/channel/<uri>')
def lbry_channel_landing(uri):
    lbry_channel(uri,1)

@plugin.route('/channel/<uri>/<page>')
def lbry_channel(uri,page):
    uri = deserialize_uri(uri)
    page = int(page)
    query = {'page': page, 'page_size': items_per_page, 'order_by': 'release_time', 'channel': uri}
    if not ADDON.getSettingBool('server_filter_disable'):
        query['stream_types'] = ['video']
    result = call_rpc('claim_search', query)
    items = result_to_itemlist(result['items'], channel=uri)
    addDirectoryItems(ph, items, result['page_size'])
    total_pages = int(result['total_pages'])
    if total_pages > 1 and page < total_pages:
        addDirectoryItem(ph, plugin.url_for(lbry_channel, uri=serialize_uri(uri), page=page+1), ListItem(get_string(30203)), True)
    endOfDirectory(ph)

@plugin.route('/search')
def lbry_search():
    query = dialog.input(get_string(30209))
    lbry_search_pager(quote_plus(query), 1)

@plugin.route('/search/<query>/<page>')
def lbry_search_pager(query, page):
    query = unquote_plus(query)
    page = int(page)
    if query != '':
        params = {
            'text': query,
            'page': page,
            'page_size': items_per_page,
            'order_by': 'release_time'
        }
        #always times out on server :(
        #if not ADDON.getSettingBool('server_filter_disable'):
        #    params['stream_types'] = ['video']
        result = call_rpc('claim_search', params)
        items = result_to_itemlist(result['items'])
        addDirectoryItems(ph, items, result['page_size'])
        total_pages = int(result['total_pages'])
        if total_pages > 1 and page < total_pages:
            addDirectoryItem(ph, plugin.url_for(lbry_search_pager, query=quote_plus(query), page=page+1), ListItem(get_string(30203)), True)
        endOfDirectory(ph)
    else:
        endOfDirectory(ph, False)

def user_payment_confirmed(claim_info):
    # paid for claim already?
    purchase_info = call_rpc('purchase_list', {'claim_id': claim_info['claim_id']})
    if len(purchase_info['items']) > 0:
        return True

    account_list = call_rpc('account_list')
    for account in account_list['items']:
        if account['is_default']:
            balance = float(str(account['satoshis'])[:-6]) / float(100)
    dtext = get_string(30214) % (float(claim_info['value']['fee']['amount']), str(claim_info['value']['fee']['currency']))
    dtext = dtext + '\n\n' + get_string(30215) % (balance, str(claim_info['value']['fee']['currency']))
    return dialog.yesno(get_string(30204), dtext)

@plugin.route('/play/<uri>')
def claim_play(uri):
    uri = deserialize_uri(uri)

    claim_info = call_rpc('resolve', {'urls': uri})[uri]
    if 'error' in claim_info:
        dialog.notification(get_string(30102), claim_info['error']['name'], xbmcgui.NOTIFICATION_ERROR)
        return

    if 'fee' in claim_info['value']:
        if claim_info['value']['fee']['currency'] != 'LBC':
            dialog.notification(get_string(30204), get_string(30103), xbmcgui.NOTIFICATION_ERROR)
            return

        if not user_payment_confirmed(claim_info):
            return

    result = call_rpc('get', {'uri': uri, 'save_file': False})
    stream_url = result['streaming_url'].replace('0.0.0.0','127.0.0.1')

    # Use HTTP
    if ADDON.getSetting('useHTTP') == 'true':
        stream_url = stream_url.replace('https://', 'http://', 1) + get_stream_headers()

    (url,li) = result_to_itemlist([claim_info])[0]
    li.setPath(stream_url)
    setResolvedUrl(ph, True, li)

@plugin.route('/download/<uri>')
def claim_download(uri):
    uri = deserialize_uri(uri)

    claim_info = call_rpc('resolve', {'urls': uri})[uri]
    if 'error' in claim_info:
        dialog.notification(get_string(30102), claim_info['error']['name'], xbmcgui.NOTIFICATION_ERROR)
        return

    if 'fee' in claim_info['value']:
        if claim_info['value']['fee']['currency'] != 'LBC':
            dialog.notification(get_string(30204), get_string(30103), xbmcgui.NOTIFICATION_ERROR)
            return

        if not user_payment_confirmed(claim_info):
            return

    call_rpc('get', {'uri': uri, 'save_file': True})

@plugin.route('/settings')
def settings():
    ADDON.openSettings()

def run():
    try:
        plugin.run()
    except PluginException as err:
        xbmc.log("PluginException: " + str( err ))

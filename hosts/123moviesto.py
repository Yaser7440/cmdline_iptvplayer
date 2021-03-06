# -*- coding: utf-8 -*-
###################################################
# LOCAL import
###################################################
from Plugins.Extensions.IPTVPlayer.dToolsSet.iptvplayerinit import TranslateTXT as _, SetIPTVPlayerLastHostError
from Plugins.Extensions.IPTVPlayer.components.ihost import CHostBase, CBaseHostClass, CDisplayListItem, RetHost, CUrlItem, ArticleContent
from Plugins.Extensions.IPTVPlayer.dToolsSet.iptvtools import printDBG, printExc, CSearchHistoryHelper, remove_html_markup, GetLogoDir, GetCookieDir, byteify
from Plugins.Extensions.IPTVPlayer.libs.pCommon import common, CParsingHelper
import Plugins.Extensions.IPTVPlayer.libs.urlparser as urlparser
from Plugins.Extensions.IPTVPlayer.libs.youtube_dl.utils import clean_html
from Plugins.Extensions.IPTVPlayer.tools.iptvtypes import strwithmeta
###################################################

###################################################
# FOREIGN import
###################################################
import time
import re
import urllib
import string
import random
import base64
from hashlib import md5
try:    import json
except Exception: import simplejson as json
from Components.config import config, ConfigSelection, ConfigYesNo, ConfigText, getConfigListEntry
###################################################


###################################################
# E2 GUI COMMPONENTS 
###################################################
from Plugins.Extensions.IPTVPlayer.components.asynccall import MainSessionWrapper
###################################################

###################################################
# Config options for HOST
###################################################

def GetConfigList():
    optionList = []
    return optionList
###################################################


def gettytul():
    return 'http://123movies.to/'

class T123MoviesTO(CBaseHostClass):
 
    def __init__(self):
        CBaseHostClass.__init__(self, {'history':'T123MoviesTO.tv', 'cookie':'123moviesto.cookie', 'cookie_type':'MozillaCookieJar'})
        self.defaultParams = {'use_cookie': True, 'load_cookie': True, 'save_cookie': True, 'cookiefile': self.COOKIE_FILE}
        
        self.HEADER = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html'}
        self.AJAX_HEADER = dict(self.HEADER)
        self.AJAX_HEADER.update( {'X-Requested-With': 'XMLHttpRequest'} )
        
        self.MAIN_URL = 'http://123movies.to/'
        self.SEARCH_URL = self.MAIN_URL + 'movie/search'
        self.DEFAULT_ICON_URL = self.MAIN_URL + 'assets/images/logo-light.png'
        
        self.MAIN_CAT_TAB = [{'category':'list_filter_genre', 'title': 'Movies',    'url':self.MAIN_URL+'movie/filter/movie',  'icon':self.DEFAULT_ICON_URL},
                             {'category':'list_filter_genre', 'title': 'TV-Series', 'url':self.MAIN_URL+'movie/filter/series', 'icon':self.DEFAULT_ICON_URL},
                             {'category':'search',          'title': _('Search'), 'search_item':True,                     'icon':self.DEFAULT_ICON_URL},
                             {'category':'search_history',  'title': _('Search history'),                                 'icon':self.DEFAULT_ICON_URL} 
                            ]
         
        self.cacheFilters = {}
        self.cacheLinks = {}
    
    def fillCacheFilters(self):
        self.cacheFilters = {}
        
        sts, data = self.cm.getPage(self.getFullUrl('movie/filter/all'), self.defaultParams)
        if not sts: return
        
        # get sort by
        self.cacheFilters['sort_by'] = []
        tmp = self.cm.ph.getDataBeetwenMarkers(data, 'Sort by</span>', '</ul>', False)[1]
        tmp = self.cm.ph.getAllItemsBeetwenMarkers(tmp, '<li', '</li>', withMarkers=True, caseSensitive=False)
        for item in tmp:
            value = self.cm.ph.getSearchGroups(item, 'href="[^"]+?/filter/all/([^"^/]+?)/')[0]
            self.cacheFilters['sort_by'].append({'sort_by':value, 'title':self.cleanHtmlStr(item)})
            
        for filter in [{'key':'quality', 'marker':'Quality</span>'},
                       {'key':'genre',   'marker':'Genre</span>'  },
                       {'key':'country', 'marker':'Country</span>'},
                       {'key':'year',    'marker':'Release</span>'}]:
            self.cacheFilters[filter['key']] = []
            tmp = self.cm.ph.getDataBeetwenMarkers(data, filter['marker'], '</ul>', False)[1]
            tmp = self.cm.ph.getAllItemsBeetwenMarkers(tmp, '<li', '</li>', withMarkers=True, caseSensitive=False)
            allItemAdded = False
            for item in tmp:
                value = self.cm.ph.getSearchGroups(item, 'value="([^"]+?)"')[0]
                self.cacheFilters[filter['key']].append({filter['key']:value, 'title':self.cleanHtmlStr(item)})
                if value == 'all': allItemAdded = True
            if not allItemAdded:
                self.cacheFilters[filter['key']].insert(0, {filter['key']:'all', 'title':'All'})
        
        printDBG(self.cacheFilters)
        
    def listFilters(self, cItem, filter, nextCategory):
        printDBG("T123MoviesTO.listFilters")
        if {} == self.cacheFilters:
            self.fillCacheFilters()
        
        cItem = dict(cItem)
        cItem['category'] = nextCategory
        self.listsTab(self.cacheFilters.get(filter, []), cItem)
        
    def listItems(self, cItem, nextCategory=None):
        printDBG("T123MoviesTO.listItems")
        url = cItem['url']
        page = cItem.get('page', 1)
        if '/search' not in url:
            # var url = 'http://123movies.to/movie/filter/' + type + '/' + 'view' + '/' + genres + '/' + countries + '/' + year + '/' + 'all' + '/' + quality;
            url += '/{0}/{1}/{2}/{3}/all/{4}'.format(cItem['sort_by'], cItem['genre'], cItem['country'], cItem['year'], cItem['quality'])
        
        if page > 1: url = url + '/{0}'.format(page)
        sts, data = self.cm.getPage(url)
        if not sts: return
        
        nextPage = self.cm.ph.getDataBeetwenMarkers(data, '<ul class="pagination">', '</ul>', False)[1]
        if '>Next &rarr;<' in nextPage:
            nextPage = True
        else: nextPage = False
        
        data = self.cm.ph.getAllItemsBeetwenMarkers(data, '<div data-movie-id=', '</a>', withMarkers=True)
        for item in data:
            url  = self.getFullUrl( self.cm.ph.getSearchGroups(item, 'href="([^"]+?)"')[0] )
            icon = self.getFullUrl( self.cm.ph.getSearchGroups(item, 'data-original="([^"]+?)"')[0] )
            movieId = self.cm.ph.getSearchGroups(item, 'data-movie-id="([^"]+?)"')[0]
            if icon == '': icon = cItem.get('icon', '')
            desc = self.cleanHtmlStr( item )
            title = self.cleanHtmlStr( self.cm.ph.getDataBeetwenMarkers(item, '<h2', '</h2>')[1] )
            if title == '': title  = self.cleanHtmlStr( self.cm.ph.getSearchGroups(item, 'title="([^"]+?)"')[0] )
            if title == '': title  = self.cleanHtmlStr( self.cm.ph.getSearchGroups(item, 'alt="([^"]+?)"')[0] )
            if url.startswith('http'):
                params = {'good_for_fav': True, 'title':title, 'url':url, 'movie_id':movieId, 'desc':desc, 'info_url':url, 'icon':icon}
                if '-season-' not in url and 'class="mli-eps"' not in item: #and '/series' not in cItem['url']
                    self.addVideo(params)
                else:
                    params['category'] = nextCategory
                    params2 = dict(cItem)
                    params2.update(params)
                    self.addDir(params2)
        
        if nextPage and len(self.currList) > 0:
            params = dict(cItem)
            params.update({'title':_("Next page"), 'page':page+1})
            self.addDir(params)
    
    def listEpisodes(self, cItem):
        printDBG("T123MoviesTO.listEpisodes")
        
        tab = self.getLinksForVideo(cItem, True)
        episodeKeys = []
        episodeLinks = {}
        
        for item in tab:
            title = item['title']
            if title not in episodeKeys:
                episodeLinks[title] = []
                episodeKeys.append(title)
            item['name'] = item['server_title']
            episodeLinks[title].append(item)
        
        seasonNum = self.cm.ph.getSearchGroups(cItem['url']+'|', '''-season-([0-9]+?)[^0-9]''', 1, True)[0]
        for item in episodeKeys:
            episodeNum = self.cm.ph.getSearchGroups(item + '|', '''Episode\s+?([0-9]+?)[^0-9]''', 1, True)[0]
            if '' != episodeNum and '' != seasonNum:
                title = 's%se%s'% (seasonNum.zfill(2), episodeNum.zfill(2)) + ' ' + item.replace('Episode %s' % episodeNum, '')
            else: title = item
            baseTitle = re.sub('Season\s[0-9]+?[^0-9]', '', cItem['title'] + ' ')
            params = dict(cItem)
            params.update({'good_for_fav':False, 'title':self.cleanHtmlStr(baseTitle + ' ' + title), 'urls':episodeLinks[item]})
            self.addVideo(params)

    def listSearchResult(self, cItem, searchPattern, searchType):
        printDBG("T123MoviesTO.listSearchResult cItem[%s], searchPattern[%s] searchType[%s]" % (cItem, searchPattern, searchType))
        cItem = dict(cItem)
        cItem['url'] = self.SEARCH_URL + '/' + urllib.quote_plus(searchPattern)
        self.listItems(cItem, 'list_episodes')
    
    def getLinksForVideo(self, cItem, forEpisodes=False):
        printDBG("T123MoviesTO.getLinksForVideo [%s]" % cItem)
        
        if 'urls' in cItem:
            return cItem['urls']
        
        urlTab = self.cacheLinks.get(cItem['url'],  [])
        if len(urlTab): return urlTab
        self.cacheLinks = {}
        
        sts, data = self.cm.getPage(cItem['url'])
        if not sts: return []
        
        # get trailer
        trailer = self.cm.ph.getDataBeetwenMarkers(data, '''$('#pop-trailer')''', '</script>', False)[1]
        trailer = self.cm.ph.getSearchGroups(trailer, '''['"](http[^"^']+?)['"]''')[0]
        
        movieId = cItem.get('movie_id', '')
        if '' == movieId:
            try: movieId = str(int(cItem['url'].split('-')[-1]))
            except Exception:
                printExc()
        
        if '' == movieId: return []
        url = 'ajax/v2_get_episodes/' + movieId
        url = self.getFullUrl( url )
        
        params = dict(self.defaultParams)
        params['header'] = self.AJAX_HEADER
        sts, data = self.cm.getPage(url, params)
        if not sts: return []
        
        data = self.cm.ph.getAllItemsBeetwenMarkers(data, '<div id="server', '<div class="clearfix">', withMarkers=True)
        for item in data:
            serverTitle = self.cleanHtmlStr( self.cm.ph.getDataBeetwenMarkers(item, '<div id="server', '</div>', withMarkers=True)[1] )
            tmp = self.cm.ph.getAllItemsBeetwenMarkers(item, '<a', '</a>', withMarkers=True)
            for eItem in tmp:
                tmp = self.cm.ph.getDataBeetwenMarkers(eItem, 'loadEpisode(', ')', False)[1].split(',')
                if len(tmp) != 2: continue
                serverId = tmp[0].strip()
                episodeId = tmp[1].strip()
                title = self.cleanHtmlStr( eItem )
                if not forEpisodes:
                    name = serverTitle + ': ' + title
                else:
                    name = ''
                urlTab.append({'name':name, 'title':title, 'server_title':serverTitle, 'url':serverId + '|' + episodeId, 'server_id':serverId, 'episode_id':episodeId, 'need_resolve':1})
            
        if len(urlTab) and trailer.startswith('http'):
            urlTab.insert(0, {'name':'Trailer', 'title':'Trailer', 'server_title':'Trailer', 'url':trailer, 'need_resolve':1})
        
        self.cacheLinks[cItem['url']] = urlTab
        return urlTab
        
    def getVideoLinks(self, videoUrl):
        printDBG("T123MoviesTO.getVideoLinks [%s]" % videoUrl)
        urlTab = []
        
        if videoUrl.startswith('http'):
            return self.up.getVideoLinkExt(videoUrl)
        
        tmp = videoUrl.split('|')
        if len(tmp) != 2: return []
        serverId = tmp[0]
        episodeId = tmp[1]
        
        if serverId in ['12', '13', '14', '15']:
            url = 'ajax/load_embed/' + episodeId
            url = self.getFullUrl( url )
            sts, data = self.cm.getPage(url)
            if not sts: return []
            try:
                data = byteify(json.loads(data))
                if data['status']:
                    urlTab = self.up.getVideoLinkExt(data['embed_url'])
            except Exception:
                printExc()
                return []
        else:
            cookieValue = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
            #cookieName  = 'bgr63m6d1ln3rech' + episodeId + 'd7ltv9lmvytcq2zf'
            #url = 'ajax/v3_load_episode/' + episodeId + '/' + md5(episodeId + cookieValue + "f7sg3mfrrs5qako9nhvvqlfr7wc9la63").hexdigest()
            #cookieName  = 'n1sqcua67bcq9826' + episodeId + 'i6m49vd7shxkn985'
            #url = 'ajax/v4_load_episode/' + episodeId + '/' + md5(episodeId + cookieValue + "rbi6m49vd7shxkn985mhodk06twz87ww").hexdigest()
            magic = 'n1sqcua67bcq9826avrbi6m49vd7shxkn985mhodk06twz87wwxtp3dqiicks2dfyud213k6ygiomq01s94e4tr9v0k887bkyud213k6ygiomq01s94e4tr9v0k887bkqocxzw39esdyfhvtkpzq9n4e7at4kc6k8sxom08bl4dukp16h09oplu7zov4m5f8'
            #cookieName  = '826avrbi6m49vd7shxkn985m' + episodeId + 'k06twz87wwxtp3dqiicks2df'
            #url = 'ajax/get_sources/' + episodeId + '/' + md5(episodeId + cookieValue + magic[12:36]).hexdigest()
            
            cookieName  = 'i6m49vd7shxkn985mhodk' + episodeId + 'twz87wwxtp3dqiicks2dfyud213k6yg'
            url = 'ajax/get_sources/' + episodeId + '/' + md5(episodeId + cookieValue + '7bcq9826avrbi6m4').hexdigest() + '/2'
            
            url = self.getFullUrl( url )

            params = {}
            params['header'] = dict(self.AJAX_HEADER)
            params['header']['Cookie'] = '%s=%s;' % (cookieName, cookieValue)
            sts, data = self.cm.getPage(url, params)
            if not sts: return []
            
            subTracks = []
            if False:
                tmp = self.cm.ph.getAllItemsBeetwenMarkers(data, '<jwplayer', '>', withMarkers=True)
                for item in tmp:
                    url  = self.cm.ph.getSearchGroups(item, 'file="(http[^"]+?)"')[0].replace('&amp;', '&')
                    name = self.cm.ph.getSearchGroups(item, 'label="([^"]+?)"')[0]
                    if 'type="mp4"' in item:
                        urlTab.append({'name':name, 'url':url})
                    elif 'kind="captions"' in item:
                        format = url[-3:]
                        if format in ['srt', 'vtt']:
                            subTracks.append({'title':name, 'url':url, 'lang':name, 'format':format})
            else:
                try:
                    tmp = byteify(json.loads(data))
                    for item in tmp['playlist'][0]['sources']:
                        if "mp4" == item['type']:
                            urlTab.append({'name':item['label'], 'url':item['file']})
                    for item in tmp['playlist'][0]['tracks']:
                        format = item['file'][-3:]
                        if format in ['srt', 'vtt'] and "captions" == item['kind']:
                            subTracks.append({'title':item['label'], 'url':item['file'], 'lang':item['label'], 'format':format})
                except Exception:
                    printExc()
            printDBG(subTracks)
            if len(subTracks):
                for idx in range(len(urlTab)):
                    urlTab[idx]['url'] = strwithmeta(urlTab[idx]['url'], {'external_sub_tracks':subTracks})
        
        return urlTab
        
    def getArticleContent(self, cItem):
        printDBG("T123MoviesTO.getArticleContent [%s]" % cItem)
        retTab = []
        
        sts, data = self.cm.getPage(cItem.get('url', ''))
        if not sts: return retTab
        
        title = self.cleanHtmlStr( self.cm.ph.getSearchGroups(data, '<meta property="og:title"[^>]+?content="([^"]+?)"')[0] )
        desc  = self.cleanHtmlStr( self.cm.ph.getSearchGroups(data, '<meta property="og:description"[^>]+?content="([^"]+?)"')[0] )
        icon  = self.getFullUrl( self.cm.ph.getSearchGroups(data, '<meta property="og:image"[^>]+?content="([^"]+?)"')[0] )
        
        if title == '': title = cItem['title']
        if desc == '':  title = cItem['desc']
        if icon == '':  title = cItem['icon']
        
        descData = self.cm.ph.getDataBeetwenMarkers(data, '<div class="mvic-info">', '<div class="clearfix">', False)[1]
        descData = self.cm.ph.getAllItemsBeetwenMarkers(descData, '<p', '</p>')
        descTabMap = {"Director":     "director",
                      "Actor":        "actors",
                      "Genre":        "genre",
                      "Country":      "country",
                      "Release":      "released",
                      "Duration":     "duration",
                      "Quality":      "quality",
                      "IMDb":         "rated"}
        
        otherInfo = {}
        for item in descData:
            item = item.split('</strong>')
            if len(item) < 2: continue
            key = self.cleanHtmlStr( item[0] ).replace(':', '').strip()
            val = self.cleanHtmlStr( item[1] )
            if key == 'IMDb': val += ' IMDb' 
            if key in descTabMap:
                try: otherInfo[descTabMap[key]] = val
                except Exception: continue
        
        if '' != cItem.get('movie_id', ''):
            rating = ''
            sts, data = self.cm.getPage(self.getFullUrl('ajax/movie_rate_info/' + cItem['movie_id']))
            if sts: rating = self.cleanHtmlStr( self.cm.ph.getDataBeetwenMarkers(data, '<div id="movie-mark"', '</label>', True)[1] )
            if rating != '': otherInfo['rating'] = self.cleanHtmlStr( rating )
        
        return [{'title':self.cleanHtmlStr( title ), 'text': self.cleanHtmlStr( desc ), 'images':[{'title':'', 'url':self.getFullUrl(icon)}], 'other_info':otherInfo}]
    
    def getFavouriteData(self, cItem):
        printDBG('T123MoviesTO.getFavouriteData')
        params = {'type':cItem['type'], 'category':cItem.get('category', ''), 'title':cItem['title'], 'url':cItem['url'], 'movie_id':cItem['movie_id'], 'desc':cItem['desc'], 'info_url':cItem['info_url'], 'icon':cItem['icon']}
        return json.dumps(params) 
        
    def getLinksForFavourite(self, fav_data):
        printDBG('T123MoviesTO.getLinksForFavourite')
        links = []
        try:
            cItem = byteify(json.loads(fav_data))
            links = self.getLinksForVideo(cItem)
        except Exception: printExc()
        return links
        
    def setInitListFromFavouriteItem(self, fav_data):
        printDBG('T123MoviesTO.setInitListFromFavouriteItem')
        try:
            params = byteify(json.loads(fav_data))
        except Exception: 
            params = {}
            printExc()
        self.addDir(params)
        return True
        
    def handleService(self, index, refresh = 0, searchPattern = '', searchType = ''):
        printDBG('handleService start')
        
        CBaseHostClass.handleService(self, index, refresh, searchPattern, searchType)

        name     = self.currItem.get("name", '')
        category = self.currItem.get("category", '')
        mode     = self.currItem.get("mode", '')
        
        printDBG( "handleService: |||||||||||||||||||||||||||||||||||| name[%s], category[%s] " % (name, category) )
        self.currList = []
        
    #MAIN MENU
        if name == None:
            self.fillCacheFilters()
            self.listsTab(self.MAIN_CAT_TAB, {'name':'category'})
        elif category.startswith('list_filter_'):
            filter = category.replace('list_filter_', '')
            if filter == 'genre':     self.listFilters(self.currItem, filter, 'list_filter_country')
            elif filter == 'country': self.listFilters(self.currItem, filter, 'list_filter_year')
            elif filter == 'year':    self.listFilters(self.currItem, filter, 'list_filter_quality')
            elif filter == 'quality': self.listFilters(self.currItem, filter, 'list_filter_sort_by')
            elif filter == 'sort_by': self.listFilters(self.currItem, filter, 'list_items')
        if category == 'list_items':
            self.listItems(self.currItem, 'list_episodes')
        elif category == 'list_episodes':
            self.listEpisodes(self.currItem)
    #SEARCH
        elif category in ["search", "search_next_page"]:
            cItem = dict(self.currItem)
            cItem.update({'search_item':False, 'name':'category'}) 
            self.listSearchResult(cItem, searchPattern, searchType)
    #HISTORIA SEARCH
        elif category == "search_history":
            self.listsHistory({'name':'history', 'category': 'search'}, 'desc', _("Type: "))
        else:
            printExc()
        
        CBaseHostClass.endHandleService(self, index, refresh)
class IPTVHost(CHostBase):

    def __init__(self):
        CHostBase.__init__(self, T123MoviesTO(), True, []) #[CDisplayListItem.TYPE_VIDEO, CDisplayListItem.TYPE_AUDIO]
    
    def getArticleContent(self, Index = 0):
        retCode = RetHost.ERROR
        retlist = []
        if not self.isValidIndex(Index): return RetHost(retCode, value=retlist)
        cItem = self.host.currList[Index]
        
        if cItem['type'] != 'video' and cItem['category'] != 'list_episodes':
            return RetHost(retCode, value=retlist)
        hList = self.host.getArticleContent(cItem)
        for item in hList:
            title      = item.get('title', '')
            text       = item.get('text', '')
            images     = item.get("images", [])
            othersInfo = item.get('other_info', '')
            retlist.append( ArticleContent(title = title, text = text, images =  images, richDescParams = othersInfo) )
        if len(hList): retCode = RetHost.OK
        return RetHost(retCode, value = retlist)
    
    def getLinksForVideo(self, Index = 0, selItem = None):
        retCode = RetHost.ERROR
        retlist = []
        if not self.isValidIndex(Index): return RetHost(retCode, value=retlist)
        
        urlList = self.host.getLinksForVideo(self.host.currList[Index])
        for item in urlList:
            retlist.append(CUrlItem(item["name"], item["url"], item['need_resolve']))

        return RetHost(RetHost.OK, value = retlist)
    # end getLinksForVideo
    
    def getResolvedURL(self, url):
        # resolve url to get direct url to video file
        retlist = []
        urlList = self.host.getVideoLinks(url)
        for item in urlList:
            need_resolve = 0
            retlist.append(CUrlItem(item["name"], item["url"], need_resolve))

        return RetHost(RetHost.OK, value = retlist)
    
    def converItem(self, cItem):
        hostList = []
        searchTypesOptions = [] # ustawione alfabetycznie
        #searchTypesOptions.append((_("Movies"),   "movie"))
        #searchTypesOptions.append((_("TV Shows"), "tv_shows"))
        
        hostLinks = []
        type = CDisplayListItem.TYPE_UNKNOWN
        possibleTypesOfSearch = None

        if 'category' == cItem['type']:
            if cItem.get('search_item', False):
                type = CDisplayListItem.TYPE_SEARCH
                possibleTypesOfSearch = searchTypesOptions
            else:
                type = CDisplayListItem.TYPE_CATEGORY
        elif cItem['type'] == 'video':
            type = CDisplayListItem.TYPE_VIDEO
        elif 'more' == cItem['type']:
            type = CDisplayListItem.TYPE_MORE
        elif 'audio' == cItem['type']:
            type = CDisplayListItem.TYPE_AUDIO
            
        if type in [CDisplayListItem.TYPE_AUDIO, CDisplayListItem.TYPE_VIDEO]:
            url = cItem.get('url', '')
            if '' != url:
                hostLinks.append(CUrlItem("Link", url, 1))
            
        title       =  cItem.get('title', '')
        description =  cItem.get('desc', '')
        icon        =  cItem.get('icon', '')
        isGoodForFavourites = cItem.get('good_for_fav', False)
        
        return CDisplayListItem(name = title,
                                    description = description,
                                    type = type,
                                    urlItems = hostLinks,
                                    urlSeparateRequest = 1,
                                    iconimage = icon,
                                    possibleTypesOfSearch = possibleTypesOfSearch,
                                    isGoodForFavourites = isGoodForFavourites)
    # end converItem


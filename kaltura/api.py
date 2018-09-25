from KalturaClient import *
from KalturaClient.Plugins.Core import *

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import logging

import mediaentry

__client__ = None

def getClient():
    global __client__;
    return __client__;

def startsession(partner_id, user_id, secret):
    """ Use configuration to generate KS
    """
    global __client__
    config = KalturaConfiguration(partner_id)
    config.serviceUrl = "https://www.kaltura.com/"
    client = KalturaClient(config)
    ktype = KalturaSessionType.ADMIN
    expiry = 432000 # 432000 = 5 days
    privileges = "disableentitlement"

    ks = client.session.start(secret, user_id, ktype, partner_id, expiry, privileges)
    client.setKs(ks)
    logging.info("Kaltura/Api: connected to %s with %s partnerId:%s" % (config.serviceUrl, user_id, partner_id))
    __client__ = client
    return None

from KalturaClient import *
from KalturaClient.Plugins.Core import *

class Filter:
    def __init__(self, mediaType=KalturaMediaType.VIDEO):
        self.filter = KalturaMediaEntryFilter()
        self.filter.mediaTypeEqual = mediaType
        self.filter.orderBy = "+createdAt"  # Oldest first

    def entry_id(self, entryid):
        """
        filter on entryid being equal

        NOOP if entryid == None

        :param entryid: kaltura media entry id
        :return: self
        """
        if entryid is not None:
            self.filter.idEqual = entryid
            logging.debug("Filter.id=%s" % self.filter.idEqual)
        else:
            logging.debug("Filter.entryId: NOOP ")
        return self

    def tag(self, tag):
        """
        if tag does not start with '!' match if it (partially) matches kaltura media entry tag

        otherwise reverse matching result

        NOOP if tag == None

        :param tag: kaltura media entry tag
        :return: self
        """
        if (tag != None):
            tagfilter = KalturaMediaEntryMatchAttributeCondition()
            # if tag start with '|' look for non matching entries
            if tag.startswith("!"):
                tagfilter.not_ = True
                tagfilter.value = tag[1:]
            else:
                tagfilter.not_ = False
                tagfilter.value = tag
            tagfilter.attribute = KalturaMediaEntryMatchAttribute.TAGS
            self.filter.advancedSearch = tagfilter
            logging.debug('Filter.category={} {}'.format(tagfilter.not_, tagfilter.value))
        else:
            logging.debug("Filter.tag: NONE" )
        return self

    def category(self, categoryId):
        """
        match if given categoryId is in a media entrys' category id list

        NOOP if categoryId == None

        :param categoryId: kaltura media entry category id
        :return: self
        """
        if (categoryId != None):
            self.filter.categoryAncestorIdIn = categoryId
            logging.debug("Filter.category={}".format(self.filter.categoryAncestorIdIn))
        else:
            logging.debug("Filter.category: NOOP")
        return self

    def undefined_LAST_PLAYED_AT(self):
        if (self.filter.advancedSearch != NotImplemented):
            raise RuntimeError("undefined_LAST_PLAYED_AT: filter.advancedSearch already defined")
        logging.debug("Filter.undefined_LAST_PLAYED_AT" )
        # not played for 20 years
        return self.years_since_played(20)

    def years_since_played(self, years):
        return self._since_played('lastPlayedAtLessThanOrEqual', years)

    def played_within_years(self, years):
        return self._since_played('lastPlayedAtGreaterThanOrEqual', years)

    def _since_played(self, mode, years):
        """
        match if video was was not last played since /within the last years

        NOOP if years == None

        :param mode:  lastPlayedAtLessThanOrEqual or lastPlayedAtGreaterThanOrEqual
        :param years: number of years
        :return: self
        """
        if years is not None:
            # compute unix standard time of now() - years
            d = datetime.now() - relativedelta(years=years)
            timestamp = calendar.timegm(d.utctimetuple())
            if (mode == 'lastPlayedAtLessThanOrEqual'):
                self.filter.lastPlayedAtLessThanOrEqual = timestamp
            elif (mode == 'lastPlayedAtGreaterThanOrEqual'):
                self.filter.lastPlayedAtGreaterThanOrEqual = timestamp
            logging.debug("Filter.{:s} {:%d, %b %Y}".format(mode, d) )
        else:
            logging.debug("Filter.{:s}: NOOP".format(mode))
        return self

    def __iter__(self):
        return FilterIter(self)

    def __str__(self):
        s = "Filter("
        if hasattr(self.filter, 'idEqual'):
            s = s + "idEqual=%s " % self.filter.idEqual
        if hasattr(self.filter, 'categoryAncestorIdIn') and self.filter.categoryAncestorIdIn != NotImplemented:
            s = s + "category=%s " % self.filter.categoryAncestorIdIn
        if hasattr(self.filter, 'advancedSearch') and  self.filter.advancedSearch != NotImplemented:
            adv = self.filter.advancedSearch
            if (isinstance(adv, KalturaMediaEntryMatchAttributeCondition)):
                s = s + ("tag: {}{}".format("!" if adv.not_ else "", adv.value))
        return s + ')'

class FilterIter:
    PAGER_CHUNK = 10

    def __init__(self, filter):
        self.filter = filter
        self.pager = KalturaFilterPager()
        self.pager.pageSize = FilterIter.PAGER_CHUNK
        self.pager.pageIndex = 0
        self.objects = iter([])

    def next(self):
        try:
            n = next(self.objects)
            return n;
        except StopIteration as stp:
            self.pager.setPageIndex(self.pager.getPageIndex() + 1)
            self.objects = iter(getClient().media.list(self.filter.filter, self.pager).objects)
            logging.debug("%s: iter page %d" % (self.filter, self.pager.getPageIndex()))
            return next(self.objects)


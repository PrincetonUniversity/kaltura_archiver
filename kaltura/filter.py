from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
import logging

from KalturaClient.Plugins.Core import *

import api
import mediaentry

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

        not compatible wih undefined_LAST_PLAYED_AT method

        :param tag: kaltura media entry tag
        :return: self
        """
        if (tag != None):
            if (self.filter.advancedSearch != NotImplemented):
                raise RuntimeError("tag: filter.advancedSearch already defined")
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
            logging.debug('Filter.tag={}{}'.format("!" if tagfilter.not_ else "", tagfilter.value))
        else:
            logging.debug("Filter.tag: NONE" )
        return self

    def undefined_LAST_PLAYED_AT(self):
        """
        matches videos that do not have a lastPlayedAt property

        not compatible wih tag method

        :return: self
        """
        if (self.filter.advancedSearch != NotImplemented):
            raise RuntimeError("undefined_LAST_PLAYED_AT: filter.advancedSearch already defined")
        self.filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
        self.filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
        self.filter.advancedSearch.comparison = KalturaSearchConditionComparison.LESS_THAN
        self.filter.advancedSearch.value = Filter._years_ago(20)
        logging.debug("Filter.undefined_LAST_PLAYED_AT last >= {}".format(mediaentry.playedDate(self.filter.advancedSearch.value)) )
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
            since = Filter._years_ago(years)
            if (mode == 'lastPlayedAtLessThanOrEqual'):
                self.filter.lastPlayedAtLessThanOrEqual = since
            elif (mode == 'lastPlayedAtGreaterThanOrEqual'):
                self.filter.lastPlayedAtGreaterThanOrEqual = since
            logging.debug("Filter.{:s} {:%d %b %Y}".format(mode, since) )
        else:
            logging.debug("Filter.{:s}: NOOP".format(mode))
        return self

    @staticmethod
    def _years_ago(years):
        """
        :param years: number of years
        :return: return   unix standard time of now() - years

        """
        d = datetime.now() - relativedelta(years=years)
        return calendar.timegm(d.utctimetuple())

    def __iter__(self):
        return FilterIter(self)

    def __str__(self):
        s = "Filter("
        if self.filter.idEqual != NotImplemented:
            s = s + "idEqual=%s " % self.filter.idEqual

        if self.filter.lastPlayedAtGreaterThanOrEqual != NotImplemented:
            s = s + "lastPlayed >= {} ".format(mediaentry.playedDate(self.filter.lastPlayedAtGreaterThanOrEqual))

        if self.filter.lastPlayedAtLessThanOrEqual != NotImplemented:
            s = s + "lastPlayed <= {} ".format(mediaentry.playedDate(self.filter.lastPlayedAtLessThanOrEqual))

        if hasattr(self.filter, 'categoryAncestorIdIn') and self.filter.categoryAncestorIdIn != NotImplemented:
            s = s + "category={} ".format(self.filter.categoryAncestorIdIn)

        adv = self.filter.advancedSearch
        if  adv != NotImplemented:
            if isinstance(adv, KalturaMediaEntryMatchAttributeCondition) and adv.attribute == KalturaMediaEntryMatchAttribute.TAGS:
                    s = s + "tag: {}{}".format("!" if adv.not_ else "", adv.value)
            elif isinstance(adv,KalturaMediaEntryCompareAttributeCondition)  and adv.attribute == KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT:
                    s = s + "undefPlayedAt-last >= {}".format(mediaentry.playedDate(adv.value))
            else:
                    s = s + "bad advancedSearch"
        return s + ')'

    def __repr__(self):
        return str(self)


class FilterIter:
    PAGER_CHUNK = 200

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
            self.objects = iter(api.getClient().media.list(self.filter.filter, self.pager).objects)
            logging.debug("%s: iter page %d" % (self.filter, self.pager.getPageIndex()))
            return next(self.objects)


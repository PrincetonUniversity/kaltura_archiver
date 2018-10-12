from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

from KalturaClient.Plugins.Core import *

import api

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
            api.logger.debug("Filter.id=%s" % self.filter.idEqual)
        else:
            api.logger.debug("Filter.entryId: NOOP ")
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
            api.logger.debug('Filter.tag={}{}'.format("!" if tagfilter.not_ else "", tagfilter.value))
        else:
            api.logger.debug("Filter.tag: NONE" )
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
        api.logger.debug("Filter.undefined_LAST_PLAYED_AT last >= {}".format(api.dateString(self.filter.advancedSearch.value)) )
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
            api.logger.debug("Filter.category={}".format(self.filter.categoryAncestorIdIn))
        else:
            api.logger.debug("Filter.category: NOOP")
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
            api.logger.debug("Filter.{:s} {:s}".format(mode, api.dateString(since)) )
        else:
            api.logger.debug("Filter.{:s}: NOOP".format(mode))
        return self

    @staticmethod
    def _years_ago(years):
        """
        :param years: number of years
        :return: return   unix standard time of now() - years

        """
        d = datetime.now() - relativedelta(years=years)
        return int(calendar.timegm(d.utctimetuple()))

    def __iter__(self):
        return FilterIter(self)

    def __str__(self):
        vs = vars(self.filter)
        properties = [[k, vs[k]] for k in vs.keys() if k != 'advancedSearch' and vs[k] != NotImplemented]
        if (self.filter.advancedSearch != NotImplemented):
            avs = vars(self.filter.advancedSearch)
            properties.append(['advancedSearch', [[k, avs[k]] for k in avs.keys() if avs[k] != NotImplemented]])
        return "Filter({})".format(properties)

    def __repr__(self):
        return str(self)


class FilterIter:
    PAGER_CHUNK = 500

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
            api.logger.debug("%s: iter page %d" % (self.filter, self.pager.getPageIndex()))
            return next(self.objects)

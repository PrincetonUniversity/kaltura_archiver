from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

from KalturaClient.Plugins.Core import *

try:
    import api
except Exception as e:
    from . import api

import api

class Filter:
    MAX_PAGE_SIZE = 500

    def __init__(self, mediaType=KalturaMediaType.VIDEO):
        self.filter = KalturaMediaEntryFilter()
        self.filter.mediaTypeEqual = mediaType
        self.filter.orderBy = "+createdAt"  # Oldest first
        self.filter.fields = "id,name,plays,createdAt,duration,status,tags,categoriesIds,sourceType"
        self.page  = 1
        self.per_page  = Filter.MAX_PAGE_SIZE
        self.maximum_iter  = -1

    def first_page(self, page):
        self.page = page
        return self

    def page_size(self, size):
        if (size > Filter.MAX_PAGE_SIZE):
            api.logger.error("Filter.page_size: {} exceeds MAX page size of {}".format(size, Filter.MAX_PAGE_SIZE))
            size = Filter.MAX_PAGE_SIZE
        self.per_page = size
        return self

    def max_iter(self, iter):
        self.maximum_iter = iter
        return self

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

    def status(self, status):
        """
        filter on KalturaEntryStatus constant
        :param status:
        :return:
        """
        if self.filter.statusIn == NotImplemented:
            self.filter.statusIn = str(status)
        else:
            self.filter.statusIn += ",{}".format(status)
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

    def get_count(self):
        """
        return number of records macthing the tag, category, and lastPlayed data

        this ignores the first_page, page_sizem, and max_iter settings
        :return: match count
        """
        return iter(self).last_result.totalCount

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
        return "Filter({}:(start=page-{}, chunks={}), max={}".format(properties, self.page, self.per_page, self.maximum_iter)

    def __repr__(self):
        return str(self)


class FilterIter:
    PAGER_CHUNK = 500

    def __init__(self, filter):
        self.filter = filter
        self.pager = KalturaFilterPager()
        self.pager.pageSize = filter.per_page
        self.pager.pageIndex = filter.page -1
        self.max_iter = filter.maximum_iter
        self._next_batch()


    def next(self):
        if (self.max_iter  == 0):
            raise StopIteration()

        try:
            return self._next()
        except StopIteration as stp:
            self._next_batch()
            return self._next()

    def _next_batch(self):
        self.pager.setPageIndex(self.pager.getPageIndex() + 1)
        self.last_result = api.getClient().media.list(self.filter.filter, self.pager)
        if (self.last_result.objects):
            api.logger.debug("%s: iter page %d" % (self.filter, self.pager.getPageIndex()))
            self.object_iter = iter(self.last_result.objects)
        else:
            self.object_iter = iter([])

    def _next(self):
        n = next(self.object_iter)
        self.max_iter  -= 1
        return n;
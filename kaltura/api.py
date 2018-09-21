from KalturaClient import *
from KalturaClient.Plugins.Core import *

import datetime
from dateutil.relativedelta import relativedelta
import calendar
import logging

def startsession(partnerId, userId, secret):
    """ Use configuration to generate KS
    """
    config = KalturaConfiguration(partnerId)
    config.serviceUrl = "https://www.kaltura.com/"
    client = KalturaClient(config)
    ktype = KalturaSessionType.ADMIN
    expiry = 432000 # 432000 = 5 days
    privileges = "disableentitlement"

    ks = client.session.start(secret, userId, ktype, partnerId, expiry, privileges)
    client.setKs(ks)
    logging.debug("Kaltura/Api: connected with %s %s" % (userId, partnerId))
    return client

class Filter:
    def __init__(self, mediaType=KalturaMediaType.VIDEO):
        self.filter = KalturaMediaEntryFilter()
        self.filter.mediaTypeEqual = mediaType
        self.filter.orderBy = "+createdAt"  # Oldest first

    def tag(self, tag):
        if (tag != None):
            self.filter.tagLike = "!" + tag
            logging.debug("Filter.tag=%s" % self.filter.tagLike )
        else:
            logging.warn("Filter.tag: NOOP ")
        return self

    def category(self, categoryId):
        if (categoryId != None):
            self.filter.categoryAncestorIdIn = categoryId
            logging.debug("Filter.tag=%s" % self.filter.categoryAncestorIdIn.to_s )
        else:
            logging.warn("Filter.category: NOOP")
        return self

    def undefined_LAST_PLAYED_AT(self):
        self.filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
        self.filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
        self.filter.advancedSearch.comparison = KalturaSearchConditionComparison.EQUAL
        self.filter.advancedSearch.value = None
        logging.debug("Filter.LAST_PLAYED_AT=None")
        hasattr(f, 't')

    def years_since_played(self, years):
        if years is not None:
            self.filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
            self.filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
            self.filter.advancedSearch.comparison = KalturaSearchConditionComparison.LESS_THAN
            d = datetime.now() - relativedelta(years=years)
            timestamp = calendar.timegm(d.utctimetuple())
            self.filter.advancedSearch.value = timestamp
            logging.debug("Filter.LAST_PLAYED_AT LESS_THAN {:%d, %b %Y}".format(d) )
        else:
            logging.warn("Filter.yearsSincePlayed: NOOP")
        return self

    def _str__(self):
        s = "Filter("
        for a in dir(self.filter):
            if (self.filter.__getattribute__(a) != NotImplemented):
                s = "%s %s=%s" % (s, a, self.filter.__getattribute__(a))
        return s + ")"

    def __str__(self):
        s = "Filter("
        if hasattr(self.filter, 'tagLike'):
            s = s + "tag=%s" % self.filter.tagLike
        if hasattr(self.filter, 'categoryAncestorIdIn') and self.filter.categoryAncestorIdIn != NotImplemented:
            s = s + "category=%s" % self.filter.categoryAncestorIdIn
        if hasattr(self.filter, 'advancedSearch') and  self.filter.advancedSearch != NotImplemented:
                s = s + "search: %s %d %s" % \
                    ( self.filter.advancedSearch.attribute, self.filter.advancedSearch.comparison, str(self.filter.advancedSearch.value) )
        return s + ')'

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


def filterOlderThan(yearssinceplay, tag=None, categoryid=None, mediaType=KalturaMediaType.VIDEO):
    filter = KalturaMediaEntryFilter()
    filter.mediaTypeEqual = mediaType

    filter.orderBy = "+createdAt"  # Oldest first

    if tag is not None:
        filter.tagsLike = "!" + tag

    if yearssinceplay is not None:
        filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
        filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
        filter.advancedSearch.comparison = KalturaSearchConditionComparison.LESS_THAN
        old_date = datetime.now()
        d = old_date - relativedelta(years=yearssinceplay)
        timestamp = calendar.timegm(d.utctimetuple())
        filter.advancedSearch.value = timestamp

    if categoryid is not None:
        filter.categoryAncestorIdIn = categoryid

    return filter


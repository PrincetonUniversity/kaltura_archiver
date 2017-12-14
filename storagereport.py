import logging
import os
from KalturaClient import *
from KalturaClient.Plugins.Core import *
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta

# Flavors should be deleted after the video has not been played for this many years
years2deleteflavors = 0
# The tag that will be applied to videos whose flavors have been deleted
flavorsdeletedtag = "flavors_deleted"
# Source should be moved to S3 after the video has not been played for this many years
years2archive = 3
# The tag that will be applied to videos that have been archived in S3
archivedtag = "archived_to_S3"


# Kaltura KMC connection information, pulled from environment variables
partnerId = os.getenv("KALTURA_PARTNERID")
secret = os.getenv("KALTURA_SECRET")
userId = os.getenv("KALTURA_USERID")
config = KalturaConfiguration(partnerId)
config.serviceUrl = "https://www.kaltura.com/"
client = KalturaClient(config)
ktype = KalturaSessionType.ADMIN
expiry = 432000 # 432000 = 5 days
privileges = "disableentitlement"

# Logging configuration
#logging.basicConfig(filename='./archivevideos.log',level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def getSearchFilter(yearssinceplay, tag, categoryid):
    # Get list
    filter = KalturaMediaEntryFilter()

    # Test scenario, search for only one video
    #filter.idEqual = "1_6cwwzio0"

    # filter.orderBy = "-createdAt" # Newest first
    filter.orderBy = "+createdAt"  # Oldest first
    filter.mediaTypeEqual = KalturaMediaType.VIDEO

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

        # filter.lastPlayedAtLessThanOrEqual = timestamp

    if categoryid is not None:
        filter.categoryAncestorIdIn = categoryid

    return filter



def getStorageTotals(filter):

    sourcesize_total = 0
    flavorsize_total = 0

    pager = KalturaFilterPager()
    pager.pageSize = 500
    pager.pageIndex = 1

    entrylist = client.media.list(filter, pager)

    totalcount = entrylist.totalCount
    print("Search found %s entries" % (entrylist.totalCount))

    # Loop over the videos
    nid = 1
    while nid <= totalcount :

        # If we've already been through the loop once, then get the next page
        if nid > 1:
            entrylist = client.media.list(filter, pager)

        # Print entry_id, date created, date last played
        for entry in entrylist.objects:
#            print("%s of %s" % (nid, totalcount))
            print("Getting storage info for entry: %s" % (entry.id))

            flavorassetswparamslist = client.flavorAsset.getFlavorAssetsWithParams(entry.id)

            for flavorassetwparams in flavorassetswparamslist:
                flavorasset = flavorassetwparams.getFlavorAsset()

                if flavorasset is not None:
                  if flavorasset.getIsOriginal():
                    sourcesize_total += flavorasset.size
                  else:
                    flavorsize_total += flavorasset.size

            nid += 1

        pager.pageIndex += 1

    print("Total size of source flavors: %s KB" % (sourcesize_total))
    print("Total size of other flavors: %s KB" % (flavorsize_total))
    print("Total size of all flavors: %s KB" % (sourcesize_total + flavorsize_total))

    return None


#######
# Main Code
#######

if __name__ == '__main__':

    ks = client.session.start(secret, userId, ktype, partnerId, expiry, privileges)
    client.setKs(ks)


    jmp_top = "13495592"
    jmp_mediaspace = "13469091"

    filter = getSearchFilter(years2archive, None, jmp_top)

    getStorageTotals(filter)

    client.session.end()


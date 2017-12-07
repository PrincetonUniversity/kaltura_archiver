import urllib
import os
import boto3
from KalturaClient import *
from KalturaClient.Plugins.Core import *
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta

# Flavors should be deleted after the video has not been played for this many years
years2deleteflavors = 2
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


def startsession():
	""" Use configuration to generate KS
	"""
	ks = client.session.start(secret, userId, ktype, partnerId, expiry, privileges)
	client.setKs(ks)

def getEntriesWithFlavorsToDelete():
       entrylist = _getEntries(years2deleteflavors, flavorsdeletedtag)
       return entrylist

def getEntriesToArchive():
       entrylist = _getEntries(years2archive, archivedtag)
       return entrylist


def _getEntries(yearssinceplay, tag):
	""" List entries - Returns strings - Requires a KS generated for the client
	"""

	# Get list
	filter = KalturaMediaEntryFilter()
	#filter.orderBy = "-createdAt" # Newest first
	filter.orderBy = "+createdAt" # Oldest first
	filter.mediaTypeEqual = KalturaMediaType.VIDEO
        filter.tagsLike = "!" + tag
        #filter.lastPlayedAtLessThanOrEqual = 
        filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
        filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
        filter.advancedSearch.comparison = KalturaSearchConditionComparison.LESS_THAN
        old_date = datetime.now()
        d = old_date - relativedelta(years=yearssinceplay)
        timestamp=calendar.timegm(d.utctimetuple())
        filter.advancedSearch.value = timestamp
	pager = KalturaFilterPager()
	pager.pageSize = 500
	pager.pageIndex = 1

	entrylist = client.media.list(filter, pager)

        return entrylist

def deleteFlavors(entrylist):

        # Get the total number of videos
	totalcount = entrylist.totalCount

	# Loop over the videos
	nid = 1
	while nid < totalcount :
	#while nid < 3:
          #entrylist = client.media.list(filter, pager)

          # Print entry_id, date created, date last played
          for entry in entrylist.objects:

            if entry.createdAt > 0:
              createdAt_str = datetime.fromtimestamp(entry.createdAt).strftime('%Y-%m-%d %H:%M:%S')
            else:
              createdAt_str = "NULL"

            if entry.lastPlayedAt > 0:
              lastPlayedAt_str = datetime.fromtimestamp(entry.createdAt).strftime('%Y-%m-%d %H:%M:%S')
            else:
              lastPlayedAt_str = "NULL"

            src_id = None
            src_url = None

            flavor_ids = []

            # Find the ID and URL for the original flavor
            print ("Looking up flavors for id = %s" % (entry.id))
            flavorassetswparamslist = client.flavorAsset.getFlavorAssetsWithParams(entry.id)

            for flavorassetwparams in flavorassetswparamslist:
              #print(type(flavorassetwparams).__name__)
              flavorasset = flavorassetwparams.getFlavorAsset()
              if flavorasset == None:
                #print ("This flavorasset is null!")
                x = 0

              elif flavorasset.getIsOriginal():
                #print ("flavorasset id = %s" %(flavorasset.id))
                src_id = flavorasset.id
                src_url = client.flavorAsset.getUrl(src_id)
                #extension = flavorasset.getFileExt()
              else:
                #print ("flavorasset id = %s" %(flavorasset.id))
                flavor_ids.append(flavorasset.id)

            if src_id == None:
              print ("id = %s has no source video!!" % (entry.id))

            print ("Entry tags: %s" % (entry.tags))

#            print ("id = %s, name = %s, createdAt = %s, lastPlayedAt = %s" % (entry.id, entry.name, createdAt_str, lastPlayedAt_str))
#            print ("source flavor id = %s, source flavor url = %s\n\n" % (src_id, src_url))
            nid = nid + 1

          pager.pageIndex = pager.pageIndex + 1

def archiveFlavors(entrylist):
          return true

#          entry_id = "1_i1z6di04"
#          src_id = ""
#          flavor_id = ""
#          flavorassetswparamslist = client.flavorAsset.getFlavorAssetsWithParams(entry_id)
#          print(type(flavorassetswparamslist).__name__)

# TODO:
# Delete flavors EXCEPT for source 
# client.flavorAsset.delete(flavorasset.id)

#          for flavorassetwparams in flavorassetswparamslist:
#            print(type(flavorassetwparams).__name__)
#            flavorasset = flavorassetwparams.getFlavorAsset()
#            if flavorasset.getIsOriginal():
#              print(type(flavorasset).__name__)
#              print(flavorasset.id)            
#              src_id = flavorasset.id
#              break

          #print("\n".join(map(str, flavorassets)))


          # Get the Download URL of the source video
#          src_url = client.flavorAsset.getUrl(src_id)
#          print("ID of src = %s" % src_id)
#          print("URL of src = %s" % src_url)

          # Download the source video
          #urllib.urlretrieve (src_url, "video.mp4")


# Then upload to AWS S3 Glacier
# Then delete

#          s3 = boto3.resource('s3')
#          data = open('video.mp4', 'rb')
#          s3.Bucket('kalturavids').put_object(Key='video.mp4', Body=data)          

#          client.session.end()
 

#######
# Main Code
#######

startsession()

entrylist = getEntriesWithFlavorsToDelete()

deleteFlavors(entrylist)

entrylist = getEntriesToArchive()

archiveFlavors(entrylist)



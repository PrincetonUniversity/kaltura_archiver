import urllib
import os
import math
import boto3
import botocore
from KalturaClient import *
from KalturaClient.Plugins.Core import *
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta

# Flavors should be deleted after the video has not been played for this many years
years2deleteflavors = 10
# The tag that will be applied to videos whose flavors have been deleted
flavorsdeletedtag = "flavors_deleted"
# Source should be moved to S3 after the video has not been played for this many years
years2archive = 3
# The tag that will be applied to videos that have been archived in S3
archivedtag = "archived_to_S3"

# Directory to use for downloading videos from Kaltura
downloaddir = "/tmp"
# Name of S3 Glacier bucket
s3bucketname = "kalturavids"


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


def getEntriesToArchive():
       entrylist = ""
       return entrylist


def _getSearchFilter(yearssinceplay, tag):
	""" List entries - Returns strings - Requires a KS generated for the client
	"""

	# Get list
	filter = KalturaMediaEntryFilter()
# Test scenario, search for only one video
        filter.idEqual = "1_6cwwzio0"
	#filter.orderBy = "-createdAt" # Newest first
	filter.orderBy = "+createdAt" # Oldest first
	filter.mediaTypeEqual = KalturaMediaType.VIDEO
        filter.tagsLike = "!" + tag
        filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
        filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
        filter.advancedSearch.comparison = KalturaSearchConditionComparison.LESS_THAN
        old_date = datetime.now()
        d = old_date - relativedelta(years=yearssinceplay)
        timestamp=calendar.timegm(d.utctimetuple())
        filter.advancedSearch.value = timestamp
        #filter.lastPlayedAtLessThanOrEqual = timestamp

        return filter

def deleteFlavors():

        filter = _getSearchFilter(years2deleteflavors, flavorsdeletedtag)

        pager = KalturaFilterPager()
        pager.pageSize = 500
        pager.pageIndex = 1

        entrylist = client.media.list(filter, pager)

        # Get the total number of videos
	totalcount = entrylist.totalCount
        print ("Search found %s entries whose flavors should be deleted." % (entrylist.totalCount))

	# Loop over all videos
	nid = 1
	while nid <= totalcount :

          # If we've already been through the loop once, then get the next page
          if nid > 1:
            entrylist = client.media.list(filter, pager)

          # Loop over the videos in this "page"
          for entry in entrylist.objects:

            if entry.lastPlayedAt > 0:
              lastPlayedAt_str = datetime.fromtimestamp(entry.createdAt).strftime('%Y-%m-%d %H:%M:%S')
            else:
              lastPlayedAt_str = "NULL"

            sourceflavor = _getSourceFlavor(entry)

            # If there is no source video, then do NOT delete the flavors
            if sourceflavor == None:
              print ("Video %s has no source video!  Flavors not deleted!" % (entry.id))

            # But if there is a source video, then delete all other flavors
            else:
              # Delete the flavors
              _deleteEntryFlavors(entry)
              # Tag the video so that we know that this script deleted the flavors
              _addTag(entry, flavorsdeletedtag)

            nid += 1

          # Increment the pager index
          pager.pageIndex += 1


def _deleteEntryFlavors(entry):
          flavorassetswparamslist = client.flavorAsset.getFlavorAssetsWithParams(entry.id)

          for flavorassetwparams in flavorassetswparamslist:
            flavorasset = flavorassetwparams.getFlavorAsset()
            if (flavorasset != None and not flavorasset.getIsOriginal()):
              print ("Deleting flavor: %s from entry: %s" % (flavorasset.id, entry.id))
              #client.flavorAsset.delete(flavorasset.id)


def _getSourceFlavor(entry):
          flavorassetswparamslist = client.flavorAsset.getFlavorAssetsWithParams(entry.id)

          for flavorassetwparams in flavorassetswparamslist:
            #print(type(flavorassetwparams).__name__)
            flavorasset = flavorassetwparams.getFlavorAsset()

            if ( flavorasset != None and flavorasset.getIsOriginal()):
              return flavorasset

          # If the original wasn't found
          return None

def _addTag(entry, newtag):
        mediaEntry = KalturaMediaEntry()
        mediaEntry.tags = entry.tags + ", " + newtag
        client.media.update(entry.id, mediaEntry)


def archiveFlavors():

        filter = _getSearchFilter(years2archive, archivedtag)

        pager = KalturaFilterPager()
        pager.pageSize = 500
        pager.pageIndex = 1

        entrylist = client.media.list(filter, pager)

        s3resource = boto3.resource('s3')
        s3client = boto3.client('s3')

        # Get the total number of videos
        totalcount = entrylist.totalCount
        print ("Search found %s entries to be archived." % (entrylist.totalCount))

        # Loop over the videos
        nid = 1
        while nid <= totalcount :

          # If we've already been through the loop once, then get the next page
          if nid > 1:
            entrylist = client.media.list(filter, pager)

          # Print entry_id, date created, date last played
          for entry in entrylist.objects:

            if entry.lastPlayedAt > 0:
              lastPlayedAt_str = datetime.fromtimestamp(entry.createdAt).strftime('%Y-%m-%d %H:%M:%S')
            else:
              lastPlayedAt_str = "NULL"

            sourceflavor = _getSourceFlavor(entry)

            # If there is no source video, then do NOT delete the flavors
            if sourceflavor == None:
              print ("Video %s has no source video!  Cannot archive source video!" % (entry.id))

            # But if there is a source video, then delete all other flavors
            else:
              # Look ahead to see if this entry_id is already in S3, if it does then skip
              if _S3ObjectExists(s3resource, s3bucketname, entry.id):
                print ("Entry %s already exists in S3!!!" % (entry.id))
                continue

              videofile = _downloadVideoFile(sourceflavor)

              # Use this method to upload large files
              s3client.upload_file(videofile, s3bucketname, entry.id)

# Catch/handle exceptions???
# Integrity check???

              #_addTag(entry, archivedtag)

# Delete local file
              os.remove(downloaddir + "/tempvideofile")

# Delete source flavor
              #client.flavorAsset.delete(sourceflavor.id)

            nid += 1

          pager.pageIndex += 1


def _downloadVideoFile(sourceflavor):
          #print("\n".join(map(str, flavorassets)))

          # Get the Download URL of the source video
          src_url = client.flavorAsset.getUrl(sourceflavor.id)
          print("ID of src = %s" % sourceflavor.id)
          print("URL of src = %s" % src_url)

          # Download the source video
          filepath = downloaddir + "/tempvideofile"
          urllib.urlretrieve (src_url, filepath)

          return filepath


def _S3ObjectExists(s3, bucketname, filename):
  try:
    s3.Object(bucketname, filename).load()

  except botocore.exceptions.ClientError as e:
    # If we got a 404 error, then it doesn't exist
    if e.response['Error']['Code'] == "404":
      return False
    else:
        # Something else has gone wrong.
      print ("Somethine went wrong: %s" % (e.response.message))
 
  return True

#######
# Main Code
#######

ks = client.session.start(secret, userId, ktype, partnerId, expiry, privileges)
client.setKs(ks)

#deleteFlavors()

archiveFlavors()

client.session.end()


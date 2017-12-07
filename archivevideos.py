import urllib
import os
import math
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

# Directory to use for downloading videos from Kaltura
downloaddir = /tmp
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

            nid = nid + 1

          pager.pageIndex = pager.pageIndex + 1


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
        mediaEntry.tags = entry.tags + ", " + flavorsdeletedtag
        client.media.update(entry.id, mediaEntry)


def archiveFlavors(entrylist):

        s3 = boto3.resource('s3')

        # Get the total number of videos
        totalcount = entrylist.totalCount

        # Loop over the videos
        nid = 1
        while nid < totalcount :
        #while nid < 3:
          #entrylist = client.media.list(filter, pager)

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

              file = _downloadVideoFile(sourceflavor)

              _uploadToGlacier(s3, s3bucketname ,file)

# Integrity check???

              _addTag(entry, archivedtag)

            nid = nid + 1

          pager.pageIndex = pager.pageIndex + 1


def _downloadVideoFile(sourceflavor):
          #print("\n".join(map(str, flavorassets)))

          # Get the Download URL of the source video
          src_url = client.flavorAsset.getUrl(sourceflavor.id)
          print("ID of src = %s" % src_id)
          print("URL of src = %s" % src_url)

          # Download the source video
          filepath = downloaddir + "tempvideofile"
          urllib.urlretrieve (src_url, filepath)

def _uploadToGlacier(s3, bucketname, file_path):

        b = s3.get_bucket(bucketname)

        filename = os.path.basename(file_path)
        k = b.new_key(filename)

        mp = b.initiate_multipart_upload(filename)

        source_size = os.stat(file_path).st_size
        bytes_per_chunk = 2000*1024*1024
        chunks_count = int(math.ceil(source_size / float(bytes_per_chunk)))

        for i in range(chunks_count):
                offset = i * bytes_per_chunk
                remaining_bytes = source_size - offset
                bytes = min([bytes_per_chunk, remaining_bytes])
                part_num = i + 1

                print "uploading part " + str(part_num) + " of " + str(chunks_count)

                with open(file_path, 'r') as fp:
                        fp.seek(offset)
                        mp.upload_part_from_file(fp=fp, part_num=part_num, size=bytes)

        if len(mp.get_all_parts()) == chunks_count:
                mp.complete_upload()
                print "upload_file done"
        else:
                mp.cancel_upload()
                print "upload_file failed"

          # Then upload to AWS S3 Glacier

#          s3 = boto3.resource('s3')
#          data = open(filename, 'rb')
#          s3.Bucket('kalturavids').put_object(Key='video.mp4', Body=data)          

 

#######
# Main Code
#######

startsession()

entrylist = getEntriesWithFlavorsToDelete()

deleteFlavors(entrylist)

#entrylist = getEntriesToArchive()

#archiveFlavors(entrylist)

client.session.end()


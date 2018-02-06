import logging
import urllib
import os
import argparse
import errno
import boto3
import botocore
from KalturaClient import *
from KalturaClient.Plugins.Core import *
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
from time import sleep

# Whether or not to modify any data
dryrun = False

# Flavors should be deleted after the video has not been played for this many years
years2deleteflavors = 0
# The tag that will be applied to videos whose flavors have been deleted
flavorsdeletedtag = "flavors_deleted"
# Source should be moved to S3 after the video has not been played for this many years
years2archive = 1
# The tag that will be applied to videos that have been archived in S3
archivedtag = "archived_to_s3"
# The tag that will be applied to all videos that have been restored from S3
restoredtag = "restored_from_s3"

# Size limit for source video that will be archived (in KB)
#video_size_limit = 15000000
video_size_limit = 10000000
# Directory to use for downloading videos from Kaltura
downloaddir = "/tmp"
# Name of S3 Glacier bucket
s3bucketname="kalturavids"

# File to be uploaded when all flavors are deleted
placeholder_file_path = "./placeholder_video.mp4"

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
logging.basicConfig(filename='./archivevideos.log',level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def checkConfig():
    """Check to make sure that required configuration parameters are properly set.
    Check ability to connect to S3.
    """

    # Check for access to S3 bucket
    try:
        logging.debug("Checking to see if we can connect with S3 ...")
        s3resource = boto3.resource('s3')
        s3resource.meta.client.head_bucket(Bucket=s3bucketname)
    except Exception as e:
        #logging.fatal("Exception type is: %s" % (e.__class__.__name__))
        #logging.fatal("Exception message: %s" % (e.message))
        logging.fatal("Cannot access S3 Bucket: %s" % (s3bucketname))
        logging.fatal("Exception message: %s" % (e.message))
        logging.fatal("Exiting immediately")
        exit(errno.ENOENT)

    # Check for existence of placeholder video
    if not os.path.isfile(placeholder_file_path):
        logging.fatal("Placeholder video does not exist: %s" % (placeholder_file_path))
        logging.fatal("Exiting immediately")
        exit(errno.ENOENT)

def deleteFlavors():
    """ Delete derived flavors, but not the original

    :return:
    """

    # Find all videos not played since years2deleteflavors that do not have the flavorsdeletedtag
    filter = _constructSearchFilter(years2deleteflavors, "!"+flavorsdeletedtag, None, None)

    pager = KalturaFilterPager()
    pager.pageSize = 500
    pager.pageIndex = 1

    entrylist = client.media.list(filter, pager)

    # Get the total number of videos
    totalcount = entrylist.totalCount
    logging.info("Search found %s entries whose flavors should be deleted." % (entrylist.totalCount))

    # Loop over all videos
    nid = 1
    while nid <= totalcount:

        # If we've already been through the loop once, then get the next page
        if nid > 1:
            entrylist = client.media.list(filter, pager)

        # Loop over the videos in this "page"
        for entry in entrylist.objects:

            #print("Thumbnail URL = %s" % (entry.thumbnailUrl))
            #thumbfilter = KalturaThumbAssetFilter()
            #thumbfilter.entryIdEqual = "1_6cwwzio0"

            #thumbslist = client.thumbAsset.list(thumbfilter)
            #for thumb in thumbslist.objects:
            #  print ("Thumb id = %s" % (thumb.id))
            #  print ("Thumb description = %s" % (thumb.description))
            #  thumburl = client.thumbAsset.getUrl(thumb.id)
            #  print ("Thumb URL = %s" % (thumburl))

            #client.thumbAsset.regenerate(thumb.id)

            sourceflavor = _getSourceFlavor(entry)

            # If there is no source video, then do NOT delete the flavors, skip this video
            if sourceflavor == None:
                logging.warning("Video %s has no source video!  Flavors not deleted!" % (entry.id))

            # But if there is a source video, then delete all other flavors
            else:
                # Delete the flavors
                _deleteEntryFlavors(entry.id, False)

                # Tag the video so that we know that this script deleted the flavors
                _addTag(entry, flavorsdeletedtag)

            nid += 1

        # Increment the pager index
        pager.pageIndex += 1


def archiveFlavors():

    filter = _constructSearchFilter(years2archive, "!"+archivedtag, None, None)

    pager = KalturaFilterPager()
    pager.pageSize = 500
    pager.pageIndex = 1

    entrylist = client.media.list(filter, pager)

    s3resource = boto3.resource('s3')
    #s3client = boto3.client('s3')

    # Get the total number of videos
    totalcount = entrylist.totalCount
    logging.info("Search found %s entries to be archived." % (entrylist.totalCount))

    # Loop over the videos
    nid = 1
    while nid <= totalcount :

        # If we've already been through the loop once, then get the next page
        if nid > 1:
            entrylist = client.media.list(filter, pager)

        # Print entry_id, date created, date last played
        for entry in entrylist.objects:

            sourceflavor = _getSourceFlavor(entry)

            # If there is no source video, then do NOT delete the flavors
            if sourceflavor == None:
                logging.warning("Video %s has no source video!  Cannot archive source video!" % entry.id)

            # If the file is too big to download/upload, then skip
            elif sourceflavor.size > video_size_limit:
                logging.warning("Source video size %s exceeds limit %s !  Cannot archive source video! %s" % (sourceflavor.size, video_size_limit, entry.id))

            # But if there is a source video that is not too big, then archive it and delete all flavors
            else:
                # Look ahead to see if this entry_id is already in S3, if it does then delete flavors
                if _S3ObjectExists(s3resource, s3bucketname, entry.id):

                    logging.warning("Source file for entry %s already exists in S3!!!" % (entry.id))

                    if not dryrun:

                        logging.debug("Adding tag %s to Kaltura entry" % (archivedtag))
                        _addTag(entry, archivedtag)

                        # Delete all flavors including source
                        logging.debug("Deleting all flavors ...")
                        _deleteEntryFlavors(entry.id, True)

                        logging.debug("Uploading placeholder video ...")
                        _uploadPlaceholder(entry.id)

                else:
                    logging.info("Archiving entry: %s" % (entry.id))
                    if not dryrun:

                        try:
                            logging.debug("Downloading source video from Kaltura ...")
                            videofile = _downloadVideoFile(sourceflavor)

                            logging.debug("Uploading source video to S3 ...")
                            s3resource.meta.client.upload_file(videofile, s3bucketname, entry.id)

                            # Catch/handle exceptions???
                            # Integrity check???

                            logging.debug("Adding tag %s to Kaltura entry" % (archivedtag))
                            _addTag(entry, archivedtag)

                            # Delete local file
                            os.remove(downloaddir + "/tempvideofile")

                            # Delete all flavors including source
                            logging.debug("Deleting all flavors ...")
                            _deleteEntryFlavors(entry.id, True)

                            logging.debug("Uploading placeholder video ...")
                            _uploadPlaceholder(entry.id)

                        except Exception as e:
                            logging.error("Error encountered: %s" % (str(e)))


            nid += 1

        pager.pageIndex += 1

def restoreVideos():
    """
    Restore all videos that have been played after having been archived
    :return:
    """

    filter = _constructSearchFilter(years2archive, archivedtag, None, None)

    pager = KalturaFilterPager()
    pager.pageSize = 500
    pager.pageIndex = 1

    entrylist = client.media.list(filter, pager)

    # Get the total number of videos
    totalcount = entrylist.totalCount
    logging.info("Search found %s entries to be restored." % entrylist.totalCount)

    # Loop over the videos
    nid = 1
    while nid <= totalcount:

        # If we've already been through the loop once, then get the next page
        if nid > 1:
            entrylist = client.media.list(filter, pager)

        # Print entry_id, date created, date last played
        for entry in entrylist.objects:

            # Restore the video to Kaltura
            was_restored = _restoreVideo(entry.id)

            # If the video was fully restored to Kaltura, rather than just a restore request initiated with Glacier
            if was_restored:

                # Remove both tags previously applied
                _removeTags(entry)

                #TODO:  need to refresh the "entry" object to get the updated tags string before making another update
                # Add tag indicating the video has been restored
                _addTag(entry, restoredtag)

            nid += 1

        pager.pageIndex += 1


def _restoreVideo(entryid):
    """
    Restore a single video
    :param entryid: the id of the video
    :return:
    """

    logging.info("Restoring video with entry_id = %s" % entryid)

    # Retrieve the video from Glacier

    video_available = _restoreFromGlacier(entryid)

    # If the video is available for download from S3, then continue with restore
    if video_available:

        filepath = downloaddir + "/tempS3videofile"

        s3resource = boto3.resource('s3')

        logging.debug("Downloading video from S3")

        if not dryrun:
            s3resource.meta.client.download_file(s3bucketname, entryid, filepath)

            # Delete placeholder video
            _deleteEntryFlavors(entryid, True)

            # Upload original video
            _uploadVideo(entryid, filepath)

            os.remove(filepath)

            return True

    # If the video is not yet available for download from S3, then wait until the next time this script runs
    else:
        logging.info("Video with entry_id %s is not yet available for download from S3" % entryid)

        return False



def _constructSearchFilter(yearssinceplay, tag, categoryid, entryid):
    """ Construct the search filter used to find videos.

    :param yearsinceplay: the number of years since the video has been played
    :param tag: videos with tag, if tag begins with '!' then videos without tag
    :param categoryid: videos in this category
    :param entryid: id of a specific video
    """

    #TODO:  delete this after testing
    entryid = "1_6cwwzio0"

    # Get list
    filter = KalturaMediaEntryFilter()

    # filter.orderBy = "-createdAt" # Newest first
    filter.orderBy = "+createdAt"  # Oldest first
    filter.mediaTypeEqual = KalturaMediaType.VIDEO

    if entryid is not None:
        filter.idEqual = entryid

    # Filter based on existance or lack of existance of a tag
    if tag is not None:
        tagfilter = KalturaMediaEntryMatchAttributeCondition()

        # If the string begins with an exclamation, set the NOT comparison to true and remove the exclamation
        if tag.startswith("!"):
            tagfilter.not_ = True
            tagfilter.value = tag[1:]

        else:
            tagfilter.value = tag

        tagfilter.attribute = KalturaMediaEntryMatchAttribute.TAGS

        filter.advancedSearch = tagfilter

    if yearssinceplay is not None:
        old_date = datetime.now()
        d = old_date - relativedelta(years=yearssinceplay)
        timestamp = calendar.timegm(d.utctimetuple())

        # If looking for videos that have NOT already been deleted/archived
        if tag.startswith("!"):
            filter.lastPlayedAtLessThanOrEqual = timestamp

        # If looking for videos that HAVE already been archived, then we must be looking to restore
        else:
            filter.lastPlayedAtGreaterThanOrEqual = timestamp

    if categoryid is not None:
        filter.categoryAncestorIdIn = categoryid

    return filter

def _deleteEntryFlavors(entryid, deletesource=False):
    """ Delete video flavors
    :param entryid: id of the video
    :param deletesource: If True then delete the source video as well, otherwise delete only derived flavors
    :return:
    """

    # Get the list of flavors
    flavorassetswparamslist = client.flavorAsset.getFlavorAssetsWithParams(entryid)

    for flavorassetwparams in flavorassetswparamslist:
        flavorasset = flavorassetwparams.getFlavorAsset()

        if (flavorasset is not None and flavorasset.getIsOriginal() and deletesource):
            logging.info("Deleting source flavor: %s from entry: %s" % (flavorasset.id, entryid))
            if not dryrun:
                client.flavorAsset.delete(flavorasset.id)

        elif (flavorasset is not None and not flavorasset.getIsOriginal()):
            logging.info("Deleting derived flavor: %s from entry: %s" % (flavorasset.id, entryid))
            if not dryrun:
                client.flavorAsset.delete(flavorasset.id)


def _getSourceFlavor(entry):
          flavorassetswparamslist = client.flavorAsset.getFlavorAssetsWithParams(entry.id)

          for flavorassetwparams in flavorassetswparamslist:
            #print(type(flavorassetwparams).__name__)
            flavorasset = flavorassetwparams.getFlavorAsset()

            if ( flavorasset is not None and flavorasset.getIsOriginal()):
              return flavorasset

          # If the original wasn't found
          return None

def _addTag(entry, newtag):
    """
    Add tag to a video
    :param entry: Kaltura ID of the video
    :param newtag: Text of the tag to be added
    :return:
    """

    logging.info("Adding tag %s from video: %s" % (newtag, entry.id))
    mediaEntry = KalturaMediaEntry()

    tags_new = entry.tags + ", " + newtag
    mediaEntry.tags = tags_new

    if not dryrun:
        client.media.update(entry.id, mediaEntry)

    # Set the tags on this object instance so that any subsequent operations have the latest version
    entry.tags = tags_new

def _removeTags(entry):
    """
    Remove tag from a video
    :param entry: Kaltura ID of the video
    :param tag: Text of the tag to be removed
    :return:
    """

    logging.info("Removing tags from video: %s" % entry.id)
    mediaEntry = KalturaMediaEntry()

    tags_orig = entry.tags

    # Remove the desired tag regardless of it's position
    tags_new = tags_orig.replace(", " + flavorsdeletedtag, "")
    tags_new = tags_new.replace(flavorsdeletedtag + ", ", "")
    tags_new = tags_new.replace(flavorsdeletedtag, "")

    tags_new = tags_new.replace(", " + archivedtag, "")
    tags_new = tags_new.replace(archivedtag + ", ", "")
    tags_new = tags_new.replace(archivedtag, "")

    mediaEntry.tags = tags_new

    if not dryrun:
        client.media.update(entry.id, mediaEntry)

    # Set the tags on this object instance so that any subsequent operations have the latest version
    entry.tags = tags_new

def _downloadVideoFile(sourceflavor):
    #print("\n".join(map(str, flavorassets)))

    #TODO Check to see that we have enough local disk space for download?

    # Get the Download URL of the source video
    src_url = client.flavorAsset.getUrl(sourceflavor.id)
    logging.debug("Downloading source flavor = %s from %s" % (sourceflavor.id, src_url))

    # Download the source video
    filepath = downloaddir + "/tempvideofile"

    if not dryrun:
        # If this fails, try it again?
        try:
            urllib.urlretrieve (src_url, filepath)
        #TODO  Do something with this exception to cause a retry???
        except Exception as e:
            logging.warn("Error when downloading source: %s" % (e.response.message))

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
      logging.error("Somethine went wrong: %s" % (e.response.message))
 
  return True


def _restoreFromGlacier(entry_id):
    """ Restore file from Glacier to standard S3.  Return True if file is available for download. """

    # Check current status
    s3 = boto3.resource('s3')
    obj = s3.Object(s3bucketname, entry_id)

    storage_class = obj.storage_class
    restore = obj.restore

    print ("Storage class: %s" % storage_class)
    print("Restore status: %s" % restore)

    if obj.storage_class == 'GLACIER':

        # If no request has been made to restore, make the request
        if obj.restore is None:
            logging.info("Submitting request to restore %s from Glacier." % entry_id)

            if not dryrun:
                bucket = s3.Bucket(s3bucketname)
                bucket.meta.client.restore_object(
                    Bucket=s3bucketname,
                    Key=entry_id,
                    RestoreRequest={'Days': 2,
                                    'GlacierJobParameters': {'Tier': 'Bulk'}}
                )

            return False

        # If a restore request was already made and completed, then the file should be available for download
        elif obj.restore.startswith('ongoing-request="false"'):
            logging.info("Video %s has been restored from Glacier and is ready for download from S3" % entry_id)
            return True

        #TODO If neither condition applies, should we throw an exception?

    # If the storage class is GLACIER, then the file should be available for download
    else:
        logging.info("Video %s is not a Glacier object and is ready for download from S3" % entry_id)
        return True




def _uploadPlaceholder(entryid):

    logging.debug("Uploading placeholder video for entry: %s" % (entryid))
    _uploadVideo(entryid, placeholder_file_path)


def _uploadVideo(entryid, filepath):

  # Upload the file to Kaltura and re-link it to the media entry

    logging.debug("Uploading video to Kaltura entry: %s" % (entryid))

    if not dryrun:
        uploadToken = KalturaUploadToken()
        uploadToken = client.uploadToken.add(uploadToken)

        ulfile = file(filepath)

        client.uploadToken.upload(uploadToken.id, ulfile)

        uploadedFileTokenResource = KalturaUploadedFileTokenResource()
        uploadedFileTokenResource.token = uploadToken.id

        client.media.addContent(entryid, uploadedFileTokenResource)

        # Set new thumbnail from the 1st second of the new video
        client.media.updateThumbnail(entryid, 1)


#######
# Main Code
#######

if __name__ == '__main__':

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--dryrun", help="Do not make any changes",
                        action="store_true")
    args = parser.parse_args()

    if args.dryrun:
        dryrun = True

    # Check configuration
    checkConfig()

    # Create Kaltura client
    try:
        ks = client.session.start(secret, userId, ktype, partnerId, expiry, privileges)
        client.setKs(ks)
    except KalturaException as e:
        logging.fatal("KalturaException message: %s" % (e.message))
        logging.fatal("Exiting immediately")
        exit(errno.EACCES)

    # Test complete
    #deleteFlavors()

    # Test complete
    #archiveFlavors()

    # Initiate retrieval from Glacier before being able to restore
    # See https://thomassileo.name/blog/2012/10/24/getting-started-with-boto-and-glacier/

    restoreVideos()

    client.session.end()


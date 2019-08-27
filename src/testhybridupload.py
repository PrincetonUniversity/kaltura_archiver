import os
import glob
from datetime import datetime
from KalturaClient import *
from KalturaClient.Plugins.Core import *

### Video file to upload
testvideo_file = "./testvideo.mp4"

### Path to transcoded files
flavors_dir = "/pukaltura/content/kalturau/flavor_assets/"

### HTML file where result will be recorded
results_file = "./kaltura-hybrid-status.html"


partnerId = os.getenv("KALTURA_PARTNERID")
secret = os.getenv("KALTURA_SECRET")
userId = os.getenv("KALTURA_USERID")
config = KalturaConfiguration(partnerId)
config.serviceUrl = "https://www.kaltura.com/"
client = KalturaClient(config)
ktype = KalturaSessionType.ADMIN
expiry = 432000 # 432000 = 5 days
privileges = "disableentitlement"

###
#  Upload and transcode test video
###
def testUpload():

        startsession()

        mediaEntry = KalturaMediaEntry()
        mediaEntry.setName('Upload Test')
        mediaEntry.setMediaType(KalturaMediaType(KalturaMediaType.VIDEO))

        ulFile = file('./video.mp4')
        uploadTokenId = client.media.upload(ulFile)

        mediaEntry = client.media.addFromUploadedFile(mediaEntry, uploadTokenId)

        return mediaEntry.id

###
#  Check to see that flavors were written to on-premises filesystem
###
def testTranscode(entryid):

        today = datetime.today().strftime('%Y%m%d')
        file_path = flavors_dir + today + "/1814/" + entryid + "*"
        #print ("File path = %s" % (file_path))

        files = glob.glob(file_path)

        if len(files) > 0:
          return True

        else:
          return False

###
#  Delete the test video
###
def cleanup(entryid):
        client.media.delete(entryid)

###
# MAIN code
###

if __name__ == '__main__':

        ks = client.session.start(secret, userId, ktype, partnerId, expiry, privileges)
        client.setKs(ks)

        # Upload the test video
        entryid = testUpload()

        # Record the result
        if not testTranscode(entryid):
                resultstring="DOWN\n"
        else:
                resultstring = "UP\n"

        # Write the result to an HTML file so that Nagios can check it
        resultsfile = open(results_file, "w")
        resultsfile.write("<!DOCTYPE html><html><head><title>Kaltura Hybrid Configuration Status</title></head>\n")
        resultsfile.write("<body><p>\n")
        resultsfile.write("Kaltura hybrid configuration status is: " + resultstring)
        resultsfile.write("</p></body></html>")
        resultsfile.close()

        # Delete the test video
        cleanup(entryid)

        client.session.end()
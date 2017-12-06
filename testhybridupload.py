#import urllib
import os
import glob
from KalturaClient import *
from KalturaClient.Plugins.Core import *

### Pat to transcoded files

flavors_dir = "/path/to/dir/containing/flavor_assets/"

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

def testUpload():

        startsession()

        mediaEntry = KalturaMediaEntry()
        mediaEntry.setName('Upload Test')
        mediaEntry.setMediaType(KalturaMediaType(KalturaMediaType.VIDEO))

        ulFile = file('./video.mp4')
        uploadTokenId = client.media.upload(ulFile)

        mediaEntry = client.media.addFromUploadedFile(mediaEntry, uploadTokenId)

        return mediaEntry.id

def testTranscode(entryid):

        today = datetime.datetime.today().strftime('%Y%m%d')
        files = glob.glob(flavors_dir + today + "/1814/" + entryid + "*")

        if len(files) > 0:
          return true

        else:
          return false

def cleanup(entryid):
        client.media.delete(entryid)

###
# MAIN code
###

entryid = testUpload()

if ! testTranscode(entryid):
  print "Test FAILED!!!"

#cleanup(entryid)

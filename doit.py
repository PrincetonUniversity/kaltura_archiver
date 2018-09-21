import kaltura

from KalturaClient import *
from KalturaClient.Plugins.Core import *

def do():
    params = {'category': None, 'noLastPlayed': None, 'awsAccessKey': '', 'loglevel': 20, 'userId': '', 'secret': '', 'tag': None, 'partnerId': '', 'unplayed': None, 'awsAccessSecret': ''}

    kaltura.api.startsession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

    filter = kaltura.api.Filter()

    client = kaltura.api.__client__

    # iterate over filtered videos
    PAGER_CHUNK = 10
    pager = KalturaFilterPager()
    pager.pageSize = PAGER_CHUNK
    pager.pageIndex = 0
    while (True):
        pager.setPageIndex(pager.getPageIndex() + 1)
        print("page %d" % pager.getPageIndex())
        entrylist = client.media.list(filter.filter, pager)
        if (not entrylist.objects):
            break
        for entry in entrylist.objects:
            print(str(kaltura.api.MediaEntry.props(entry)))



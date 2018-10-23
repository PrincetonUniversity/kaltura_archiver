
from kaltura_aws import KalturaArgParser, SAVED_TO_S3, PLACE_HOLDER_VIDEO
import kaltura
import envvars
import traceback
import sys


def setUp():
    params = envvars.to_value(KalturaArgParser.ENV_VARS)
    kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])


def print_summary(n, n_saved, n_pholder):
    print("#{} {}".format('TOTAL', n))
    print("#{} {}".format(SAVED_TO_S3, n_saved))
    print("#{} {}".format(PLACE_HOLDER_VIDEO, n_pholder))

from KalturaClient.Plugins.Core import *


class Direct:
    def __init__(self, client):
        self.filter = KalturaMediaEntryFilter()
        self.filter.mediaTypeEqual = KalturaMediaType.VIDEO
        self.filter.orderBy = "+createdAt"  # Oldest first
        self.filter.advancedSearch = KalturaMediaEntryCompareAttributeCondition()
        self.filter.advancedSearch.attribute = KalturaMediaEntryCompareAttribute.LAST_PLAYED_AT
        self.filter.advancedSearch.comparison = KalturaSearchConditionComparison.LESS_THAN
        self.filter.advancedSearch.value = 909104962  # 20 years ago
        self.client = client

    def count(self):
        self.pager = KalturaFilterPager()
        self.pager.pageSize = 1000
        self.pager.pageIndex = 1

        objects = self.client.media.list(self.filter, self.pager).objects
        n, n_saved, n_pholder = 0, 0, 0
        while (objects):
            try:
                for e in objects:
                    n += 1
                    if (SAVED_TO_S3 in e.getTags()):
                        n_saved += 1
                    if (PLACE_HOLDER_VIDEO in e.getTags()):
                        n_pholder += 1
                    if (0 == n % 250):
                        sys.stdout.write('.');
                        sys.stdout.flush()
                self.pager.pageIndex += 1
                objects = self.client.media.list(self.filter, self.pager).objects

            except Exception as e:
                print(str(e))
                traceback.print_exc()
        print("\n")
        print("--- Direct.undefined_LAST_PLAYED_AT")
        print_summary(n, n_saved, n_pholder)


if __name__ == '__main__':
    setUp()
    #count()
    Direct(kaltura.api.getClient()).count()

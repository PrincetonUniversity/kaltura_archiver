#!/usr/bin/env python
import unittest

from KalturaClient.Base import IKalturaLogger
from  kaltura_aws import KalturaArgParser, _init_loggers
import kaltura
import envvars

from KalturaClient.Plugins.Core import *
import random
import sys

def randomString(prefix = 'testing'):
    return prefix + "_" + str(random.randint(0, 255))

class KalturaLogger(IKalturaLogger):
    def log(self, msg):
        print("API: " + msg)

class TestKaltura(unittest.TestCase):
    # assuming its OK to change stuff in the Test KMC
    # IDs below are assumed to be in the test KMC
    # if test fail follow up tests may start in unexpected scenarios
    TEST_KALTURA_PARTNER_ID = 336061

    TEST_ID_1 = '1_nkc7nbgs'

    # this image should not have an s3 copy when test are started
    TEST_ID_NO_S3_COPY = '1_z9hho4yy'

    # this entry has no ORIGINAL
    TEST_ID_NO_ORIGINAL = '1_cmnbl3za'

    # this TAG=python_test  + other tags
    TEST_TAG_PYTHON_TEST = '1_nkc7nbgs'

    @classmethod
    def setUpClass(cls):
        print("-- setUpClass {}".format(cls))
        if not hasattr(TestKaltura, 'bucket'):
            params = envvars.to_value(KalturaArgParser.ENV_VARS)
            TestKaltura.bucket = params['awsBucket']
            TestKaltura.place_holder_video = params['videoPlaceholder']
            if (int(params['partnerId']) != TestKaltura.TEST_KALTURA_PARTNER_ID):
                print("NOT CONNECTED TO TEST KMC ");
                sys.exit(1)

            kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])
            client = kaltura.api.getClient()
            # uncomment to trace kaltura API calls
            # client.config.logger = KalturaLogger()
            assert(client != None)

    @classmethod
    def tearDownClass(cls):
            print("-- tearDownClass {}".format(cls))

    def setUp(self):
        self.bucket = TestKaltura.bucket
        self.place_holder_video = TestKaltura.place_holder_video

# enable to see debug logging info during test execution
#_init_loggers()
#kaltura.logger.setLevel('DEBUG')

TestKaltura.setUpClass()

if __name__ == '__main__':
    unittest.main()

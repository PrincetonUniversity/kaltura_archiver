#!/usr/bin/env python
import unittest

from  kaltura_aws import KalturaArgParser
import kaltura
import envvars
from KalturaClient.Plugins.Core import *
import random

def randomString(prefix = 'testing'):
    return prefix + "_" + str(random.randint(0, 255))

class KalturaLogger(IKalturaLogger):
    def log(self, msg):
        print("API: " + msg)

class TestKaltura(unittest.TestCase):
    # assuming its OK to change stuff in the Test KMC
    # IDs below are assumed to be in the test KMC
    # if test fail followup tests may start in unexpected scenarios
    TEST_ID_1 = '1_tza6webs'

    def setUp(self):
        params = envvars.to_value(KalturaArgParser.ENV_VARS)
        kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])
        client = kaltura.api.getClient()
        # uncomment to trace kaltura API calls
        # client.config.logger = KalturaLogger()
        assert(client != None)

if __name__ == '__main__':
    unittest.main()

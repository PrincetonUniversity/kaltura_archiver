#!/usr/bin/env python
import unittest

from  kaltura_aws import KalturaArgParser
import kaltura
import envvars

class TestKaltura(unittest.TestCase):
    def setUp(self):
        params = envvars.to_value(KalturaArgParser.ENV_VARS)
        kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])
        client = kaltura.api.getClient()
        assert(client != None)

if __name__ == '__main__':
    unittest.main()

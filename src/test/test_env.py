#!/usr/bin/env python
import unittest
from test_kaltura import TestKaltura

from  kaltura_aws import KalturaArgParser
import kaltura
import envvars

class TestEnv(TestKaltura):
    def test_connect(self):
        client = kaltura.api.getClient()
        assert(client != None)

    def test_env_vars_set(self):
        params = envvars.to_value(KalturaArgParser.ENV_VARS)
        assert(len(params) == len(KalturaArgParser.ENV_VARS))

if __name__ == '__main__':
    unittest.main()

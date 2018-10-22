#!/usr/bin/env python
import unittest
from  kaltura_aws import KalturaArgParser
import envvars

class TestEnvVarsDefined(unittest.TestCase):
    def test_env_vars_set(self):
        params = envvars.to_value(KalturaArgParser.ENV_VARS)
        assert(len(params) == len(KalturaArgParser.ENV_VARS))

if __name__ == '__main__':
    unittest.main()
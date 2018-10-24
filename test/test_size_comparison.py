#!/usr/bin/env python
import unittest
from kaltura_aws import aws_compatible_size

class TestSizeComparison(unittest.TestCase):
    def test_1339130980_1310720(self):
        self.assertTrue(aws_compatible_size(1310720, 1339130980))

    def test_1339130980_1310720(self):
        self.assertTrue(aws_compatible_size(1310720, 1339130980))

    def test_251149730_245760(self):
        self.assertTrue(aws_compatible_size(245760, 251149730))

    def test_220350223_215040(self):
        self.assertTrue(aws_compatible_size(215040, 220350223))

    def test_204800_207(self):
        self.assertFalse(aws_compatible_size(207, 204800))

    def test_204800_206(self):
        self.assertTrue(aws_compatible_size(206, 204800))

    def test_204800_205(self):
        self.assertTrue(aws_compatible_size(205, 204800))


if __name__ == '__main__':
    unittest.main()
#!/usr/bin/env python
import unittest
from test_kaltura import TestKaltura

import kaltura
import kaltura_aws

class TestFilterIter(TestKaltura):

    def test_page_5_size_5_maxentry_7(self):
        filter = kaltura.Filter().first_page(5).page_size(11).max_iter(7)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 7)

    def test_page_1_size_10_maxentry_2(self):
        filter = kaltura.Filter().first_page(1).page_size(10).max_iter(2)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 2)

    def test_same_returns(self):
        filter = kaltura.Filter().first_page(2).max_iter(1)
        e1 = list(filter)
        filter = kaltura.Filter().first_page(2).max_iter(1)
        e2 = list(filter)
        self.assertEqual(e1, e2)

    def test_overlap(self):
        filter = kaltura.Filter().first_page(2).page_size(10).max_iter(1)
        e = next(iter(filter))

        filter = kaltura.Filter().first_page(1).page_size(10).max_iter(11)
        e_ = list(filter)[-1]

        self.assertEqual(e.getId(), e_.getId())

    def test_overlap_SAVED_TO_S3(self):
        filter = kaltura.Filter().first_page(3).page_size(1).max_iter(1).tag(kaltura_aws.SAVED_TO_S3)
        e = next(iter(filter))

        filter = kaltura.Filter().first_page(2).page_size(1).max_iter(2).tag(kaltura_aws.SAVED_TO_S3)
        e_ = list(filter)[-1]

        self.assertEqual(e.getId(), e_.getId())

    def test_get_count(self):
        cnt_s3 = kaltura.Filter().first_page(3).page_size(1).max_iter(1).tag(kaltura_aws.SAVED_TO_S3).get_count()
        self.assertTrue(cnt_s3 > 0)
        cnt_s3_same = kaltura.Filter().first_page(100).page_size(1).tag(kaltura_aws.SAVED_TO_S3).get_count()
        self.assertTrue(cnt_s3 == cnt_s3_same)
        cnt = kaltura.Filter().first_page(3).page_size(1).max_iter(1).get_count()
        self.assertTrue(cnt_s3 <= cnt)

    def _prt_filter(self, filter):
        print('----')
        for e in filter:
            print(e.getId())



if __name__ == '__main__':
    unittest.main()
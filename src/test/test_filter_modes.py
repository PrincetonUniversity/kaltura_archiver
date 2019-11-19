#!/usr/bin/env python
import unittest
from test_kaltura import TestKaltura

try:
    import kaltura
except:
    from .. import kaltura

class TestFilterModes(TestKaltura):

    def test_filter_nothing(self):
        filter = kaltura.Filter().page_size(10).max_iter(7)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 7)

    def test_filter_entry_id(self):
        filter = kaltura.Filter().entry_id(TestKaltura.TEST_ID_1)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 1)

    def test_filter_entry_id_get_count(self):
        filter = kaltura.Filter().entry_id(TestKaltura.TEST_ID_1)
        sfilter = str(filter)
        self.assertEqual(filter.get_count(), 1)

    def test_filter_bad_entry_id(self):
        filter = kaltura.Filter().entry_id(TestKaltura.TEST_ID_1 + "BAD")
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 0)

    def test_filter_bad_entry_id_get_count(self):
        filter = kaltura.Filter().entry_id(TestKaltura.TEST_ID_1 + "BAD")
        sfilter = str(filter)
        self.assertEqual(filter.get_count(), 0)

    def test_filter_played_within(self):
        filter = kaltura.Filter().played_within_years(3).page_size(10).max_iter(10)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 10, "expecting 10 videos played within 3 years")
        #TODO check dates

    def test_filter_unplayed_for(self):
        filter = kaltura.Filter().years_since_played(1).page_size(10).max_iter(10)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 10, "expecting 10 videos unplayed for 1 year")
        #TODO check dates

    def test_filter_played_within_unplayed_for(self):
        filter = kaltura.Filter().played_within_years(3).years_since_played(1).page_size(10).max_iter(10)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertGreater(l, 0, "expecting some video played between 3 and 1 year ago ")

    def test_filter_played_within_unplayed_for_impossible(self):
        filter = kaltura.Filter().played_within_years(1).years_since_played(3).page_size(10).max_iter(10)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 0, "expecting no videos played a year ago but unplayed for 3 years")

    def test_filter_created_within(self):
        filter = kaltura.Filter().created_within_years(3).page_size(10).max_iter(10)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 10, "expecting 10 videos created within 3 years")
        #TODO check dates

    def test_filter_created_before(self):
        filter = kaltura.Filter().years_since_created(1).page_size(10).max_iter(10)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 10, "expecting 10 videos created more than 1 year")
        #TODO check dates

    def test_filter_created_within_created_before(self):
        filter = kaltura.Filter().created_within_years(3).years_since_created(1).page_size(10).max_iter(10)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertGreater(l, 0, "expecting some video created between 3 and 1 year ago ")

    def test_filter_created_within_created_before_impossible(self):
        filter = kaltura.Filter().created_within_years(1).years_since_created(3).page_size(10).max_iter(10)
        sfilter = str(filter)
        l = sum(1 for _ in filter)
        self.assertEqual(l, 0, "expecting no videos created a year ago and created more than 3 years")

    def test_filter_tag(self):
        filter = kaltura.Filter().tag("archived_to_s3")
        sfilter = str(filter)
        for e in  filter:
            self.assertTrue('archived_to_s3' in  e.tags.split(', '))

    def test_filter_not_tag(self):
        filter = kaltura.Filter().tag("!archived_to_s3")
        sfilter = str(filter)
        for e in  filter:
            self.assertFalse('archived_to_s3' in  e.tags.split(', '))

    def test_filter_status(self):
        filter = kaltura.Filter().status("2,7")
        sfilter = str(filter)
        for e in  filter:
            self.assertTrue(e.getStatus().getValue() in ["2", "7"])

    def test_filter_plays_lower_than(self):
        n = 11
        filter = kaltura.Filter().plays_lt(n).page_size(10).max_iter(7)
        sfilter = str(filter)
        for e in  filter:
            self.assertTrue(e.plays < n)


if __name__ == '__main__':
    unittest.main()
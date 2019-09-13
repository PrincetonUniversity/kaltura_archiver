#!/usr/bin/env python
import unittest
from test_kaltura import TestKaltura, randomString

import kaltura

class TestMediaEntry(TestKaltura):
    def test_add_then_get_tag_then_delete(self):
        tag =  randomString("test_add_then_get_tag_then_delete")
        entry = kaltura.api.getClient().media.get(TestKaltura.TEST_ID_1)

        mentry = kaltura.MediaEntry(entry)
        mentry.addTag(tag, doUpdate=True)
        mentry.reload()
        tags = mentry.entry.getTags()
        self.assertIn(tag, tags)

        mentry.delTag(tag, doUpdate=True)
        mentry.reload()
        tags = mentry.entry.getTags()
        self.assertNotIn(tag, tags)


if __name__ == '__main__':
    unittest.main()
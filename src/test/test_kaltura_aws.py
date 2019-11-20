#!/usr/bin/env python
import unittest
import os, sys

from test_kaltura import TestKaltura
import kaltura
import kaltura_aws

from kaltura import aws

# these test rely on alphabetical execution of test cases


class TestKalturaAwsCli(TestKaltura):
    @classmethod
    def setUpClass(cls):
        print("-- setUpClass {}".format(cls))
        TestKalturaAwsCli.no_s3_copy_id = TestKaltura.TEST_ID_NO_S3_COPY
        TestKalturaAwsCli.no_orig_id = TestKaltura.TEST_ID_NO_ORIGINAL
        entry = kaltura.api.getClient().media.get(TestKalturaAwsCli.no_s3_copy_id)
        if (kaltura.MediaEntry(entry).getOriginalFlavor().getSize() < 350):
            print("ABORT: based on size ORIGINAL FLAVOR seems to be replacement video")
            sys.exit(1)
        if entry.getTags():
            print("ABORT: entry {} has tags - probably left over from previous run failures".format(TestKalturaAwsCli.no_s3_copy_id))
            sys.exit(1)
        assert(not aws.s3_exists(TestKalturaAwsCli.no_s3_copy_id, TestKaltura.bucket))

    @classmethod
    def tearDownClass(cls):
        if (True):
            print("-- tearDownClass {}".format(cls))
            #bring back to no s3 file no tags
            aws.s3_delete(TestKaltura.bucket, TestKalturaAwsCli.entry_id, True)
            mentry = kaltura.MediaEntry(kaltura.api.getClient().media.get(TestKalturaAwsCli.entry_id))
            mentry.reload()
            if kaltura_aws.SAVED_TO_S3 in mentry.entry.getTags():
                mentry.delTag(kaltura_aws.SAVED_TO_S3, True)
            if kaltura_aws.PLACE_HOLDER_VIDEO in mentry.entry.getTags():
                mentry.delTag(kaltura_aws.PLACE_HOLDER_VIDEO, True)


    def setUp(self):
        super(TestKalturaAwsCli, self).setUp()
        self.entry_id_not_in_s3 = TestKaltura.TEST_ID_NO_S3_COPY
        self.mentry_not_in_s3 = kaltura.MediaEntry(kaltura.api.getClient().media.get(self.entry_id_not_in_s3))
        self.mentry_not_in_s3.reload()
        self.entry_not_in_s3 =  self.mentry_not_in_s3.entry

    def testa_entry_is_healthy(self):
            argv = ['health', '-i', self.entry_id_not_in_s3]
            rc = kaltura_aws._main(argv)
            self.assertEqual(rc, 0)

    def testa_no_orig_is_unhealthy(self):
            argv = ['health', '-i', TestKalturaAwsCli.TEST_ID_NO_ORIGINAL]
            rc = kaltura_aws._main(argv)
            self.assertNotEqual(rc, 0)

    def testa_list(self):
        argv = ['list', '--max_entries', '3']
        rc = kaltura_aws._main(argv)
        self.assertEqual(rc, 0)

    def testa_list_played_within(self):
        argv = ['list', '--played_within', '5', '--max_entries', '2']
        rc = kaltura_aws._main(argv)
        self.assertEqual(rc, 0)

    def testa_list_unplayed_for(self):
        argv = ['list', '--unplayed_for', '1', '--max_entries', '1']
        rc = kaltura_aws._main(argv)
        self.assertEqual(rc, 0)

    def testa_list_played_within_unplayed_for(self):
        argv = ['list', '--unplayed_for', '1', '--played_within', '3', '--max_entries', '1']
        rc = kaltura_aws._main(argv)
        self.assertEqual(rc, 0)

    def testa_list_tag_is(self):
        argv = ['list', '--tag', 'archived_to_s3', '--max_entries', '1']
        rc = kaltura_aws._main(argv)
        self.assertEqual(rc, 0)

    def testa_list_not_tag_is(self):
        argv = ['list', '--tag', '!archived_to_s3', '--max_entries', '1']
        rc = kaltura_aws._main(argv)
        self.assertEqual(rc, 0)

    def testab_download(self):
        argv = ['download', '-i', self.entry_id_not_in_s3]
        rc = kaltura_aws._main(argv)
        self.assertEqual(rc, 0)
        # check not empty
        self.assertGreater(os.stat(self.entry_id_not_in_s3 + ".mp4").st_size, 0)
        os.remove(self.entry_id_not_in_s3 + ".mp4")

    def testb_replace_video_without_s3copy(self):
            argv = ['replace_video', '-i', self.entry_id_not_in_s3]
            rc = kaltura_aws._main(argv)
            self.assertNotEqual(rc, 0)

    def testb_add_archive_tag_only_is_unhealthy(self):
            self.mentry_not_in_s3.addTag(kaltura_aws.SAVED_TO_S3, doUpdate=True)
            self.mentry_not_in_s3.reload()
            argv = ['health', '-i', self.entry_id_not_in_s3]
            rc = kaltura_aws._main(argv)
            self.assertNotEqual(rc, 0)
            self.mentry_not_in_s3.delTag(kaltura_aws.SAVED_TO_S3, doUpdate=True)
            self.mentry_not_in_s3.reload()

    def testcp_s3copy_dryrun(self):
            #DRYRUN
            argv = ['s3copy','-i', self.entry_id_not_in_s3]
            rc = kaltura_aws._main(argv)
            self.assertEqual(rc, 0)
            # no TAGS not in s3
            kaltura.MediaEntry(self.entry_not_in_s3).reload()
            self.assertFalse(self.entry_not_in_s3.getTags())
            self.assertFalse(aws.s3_exists(self.entry_id_not_in_s3, self.bucket))

    def testcp_s3copy_run(self):
            for _ in range(0,2):
                argv = ['s3copy', '--s3copy',  '-i', self.entry_id_not_in_s3]
                rc = kaltura_aws._main(argv)
                self.assertEqual(rc, 0)
                # no TAGS not in s3
                kaltura.MediaEntry(self.entry_not_in_s3).reload()
                self.assertTrue(kaltura_aws.SAVED_TO_S3, self.entry_not_in_s3.getTags())
                self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket))

    def testcp_add_place_holder_only_is_unhealthy(self):
            self.mentry_not_in_s3.addTag(kaltura_aws.PLACE_HOLDER_VIDEO, doUpdate=True)
            self.mentry_not_in_s3.reload()
            argv = ['health', '-i', self.entry_id_not_in_s3]
            rc = kaltura_aws._main(argv)
            self.assertNotEqual(rc, 0)
            self.mentry_not_in_s3.delTag(kaltura_aws.PLACE_HOLDER_VIDEO, doUpdate=True)
            self.mentry_not_in_s3.reload()

    def testr_replace_video_with_s3copy_dryrun(self):
            argv = ['replace_video', '-i', self.entry_id_not_in_s3]
            rc = kaltura_aws._main(argv)
            self.assertEqual(rc, 0)

    def testr_replace_video_run(self):
        argv = ['replace_video', '--replace', '-i', self.entry_id_not_in_s3]
        for _ in range(0,2):
            rc = kaltura_aws._main(argv)
            self.assertEqual(rc, 0)
            self._wait_original_ready()


    def testre_restore_video_from_s3_dryrun(self):
            argv = ['restore_from_s3', '-i', self.entry_id_not_in_s3]
            rc = kaltura_aws._main(argv)
            self.assertEqual(rc, 0)

    def testre_restore_video_from_s3_run(self):
            argv = ['restore_from_s3', '--restore', '-i', self.entry_id_not_in_s3]
            for _ in range(0,2):
                rc = kaltura_aws._main(argv)
                self.assertEqual(rc, 0)
                self._wait_original_ready()

    def _wait_original_ready(self):
        while (True):
            kaltura_aws._pause(5, True)
            self.mentry_not_in_s3.reload()
            if (kaltura.Flavor(self.mentry_not_in_s3.getOriginalFlavor()).isReady()):
                break;

if __name__ == '__main__':
    unittest.main()
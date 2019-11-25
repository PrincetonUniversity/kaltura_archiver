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
		mentry = kaltura.MediaEntry(kaltura.api.getClient().media.get(TestKaltura.TEST_ID_NO_S3_COPY))
		if mentry.getTags():
			print("FIXING: entry {} has tags - removing all".format(TestKalturaAwsCli.no_s3_copy_id))
			mentry = kaltura.MediaEntry(kaltura.api.getClient().media.get(TestKaltura.TEST_ID_NO_S3_COPY))
			mentry.setTags([], doUpdate=True)
		if aws.s3_exists(TestKalturaAwsCli.no_s3_copy_id, TestKaltura.bucket):
			print("FIXING: deleting {} from s3://{}".format(TestKalturaAwsCli.no_s3_copy_id, TestKaltura.bucket))
			aws.s3_delete(TestKaltura.bucket, TestKalturaAwsCli.no_s3_copy_id, True)
		if (kaltura.MediaEntry(mentry.entry).getOriginalFlavor().getSize() < 350):
			print("ABORT: based on size ORIGINAL FLAVOR seems to be replacement video")
			assert (False)

	@classmethod
	def tearDownClass(cls):
		print("-- tearDownClass {}".format(cls))

	def setUp(self):
		super(TestKalturaAwsCli, self).setUp()
		self.entry_id_not_in_s3 = TestKaltura.TEST_ID_NO_S3_COPY
		self.mentry_not_in_s3 = kaltura.MediaEntry(kaltura.api.getClient().media.get(self.entry_id_not_in_s3))
		self.mentry_not_in_s3.reload()
		self.entry_not_in_s3 = self.mentry_not_in_s3.entry

	def testa_filter(self):
		for cmd in ['list', 'count']:
			argv = [cmd, '--max_entries', '3']
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)


	def testa_filter_played_within(self):
		for cmd in ['list', 'count']:
			argv = [cmd, '--played_within', '5', '--max_entries', '2']
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)

	def testa_filter_unplayed_for(self):
		for cmd in ['list', 'count']:
			argv = [cmd, '--unplayed_for', '1', '--max_entries', '1']
			rc = kaltura_aws._main(argv)

	def testa_filter_played_within_unplayed_for(self):
		for cmd in ['list', 'count']:
			argv = [cmd, '--unplayed_for', '1', '--played_within', '3', '--max_entries', '1']
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)

	def testa_filter_tag_is(self):
		for cmd in ['list', 'count', 'repair']:
			argv = [cmd, '--tag', 'archived_to_s3', '--max_entries', '1', '--page_size', '5']
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)

	def testa_filter_not_tag_is(self):
		for cmd in ['list', 'count']:
			argv = [cmd, '--tag', '!archived_to_s3', '--max_entries', '1', '--first_page', '1', '--page_size', '2']
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)

	def testa_download_from_kmc(self):
		argv = ['download', '-i', self.entry_id_not_in_s3]
		rc = kaltura_aws._main(argv)
		self.assertEqual(rc, None)
		# check not empty
		self.assertGreater(os.stat(self.entry_id_not_in_s3 + ".mp4").st_size, 0)
		os.remove(self.entry_id_not_in_s3 + ".mp4")

	def testb_replace_video_without_s3copy(self):
		argv = ['replace_video', '-i', self.entry_id_not_in_s3, '--replace']
		rc = kaltura_aws._main(argv)
		self.assertEqual(rc, None)
		self.mentry_not_in_s3.reload()
		self.assertFalse(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags())

	def testb_add_archive_tag_only_is_unhealthy(self):
		self.mentry_not_in_s3.addTag(kaltura_aws.SAVED_TO_S3, doUpdate=True)
		self.mentry_not_in_s3.reload()
		argv = ['health', '-i', self.entry_id_not_in_s3]
		rc = kaltura_aws._main(argv)
		self.assertEqual(rc, None)
		self.mentry_not_in_s3.delTag(kaltura_aws.SAVED_TO_S3, doUpdate=True)

	def testcp_s3copy_dryrun(self):
		# assert not tagged before
		self.mentry_not_in_s3.reload()
		self.assertFalse(kaltura_aws.SAVED_TO_S3 in self.mentry_not_in_s3.getTags(), "not tagged before test")
		self.assertFalse(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'not in s3 before test')
		argv = ['s3copy', '-i', self.entry_id_not_in_s3]
		rc = kaltura_aws._main(argv)
		self.assertEqual(rc, None)
		# assert not tagged and  not in s3
		self.mentry_not_in_s3.reload()
		self.assertFalse(kaltura_aws.SAVED_TO_S3 in self.mentry_not_in_s3.getTags(), "not tagged after test")
		self.assertFalse(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'not in s3 after test')

	def testcp_s3copy_run(self):
		for _ in range(0, 2):
			argv = ['s3copy', '--s3copy', '-i', self.entry_id_not_in_s3]
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)
			# check Tagged and file in s3
			kaltura.MediaEntry(self.entry_not_in_s3).reload()
			self.assertTrue(kaltura_aws.SAVED_TO_S3, self.entry_not_in_s3.getTags())
			self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket))

	def testcp_s3copy_add_place_holder_only_makes_sick(self):
		self.mentry_not_in_s3.addTag(kaltura_aws.PLACE_HOLDER_VIDEO, doUpdate=True)
		self.mentry_not_in_s3.reload()
		argv = ['health', '-i', self.entry_id_not_in_s3]
		rc = kaltura_aws._main(argv)
		self.assertEqual(rc, None)
		self.mentry_not_in_s3.delTag(kaltura_aws.PLACE_HOLDER_VIDEO, doUpdate=True)
		self.mentry_not_in_s3.reload()
		self.assertFalse(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(),
						 'tag removed successfully')

	def testr_replace_video_with_placeholder_dryrun(self):
		# assert not tagged before
		self.mentry_not_in_s3.reload()
		self.assertFalse(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(),
						 "not tagged before test")
		self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'in s3 before test')
		argv = ['replace_video', '-i', self.entry_id_not_in_s3]
		rc = kaltura_aws._main(argv)
		self.mentry_not_in_s3.reload()
		self.assertFalse(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(), "not tagged after test")
		self.assertEqual(rc, None)

	def testr_replace_video_with_placeholder_run(self):
		self.mentry_not_in_s3.reload()
		self.assertFalse(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(), "not tagged before test")
		self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'in s3 before test')
		# force inclusion of all videos even recently created ones
		argv = ['replace_video', '--replace', '--created_before', '0', '-i', self.entry_id_not_in_s3]
		for _ in range(0, 2):
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)
			self.mentry_not_in_s3.reload()
			self.assertTrue(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(), "tagged after test")

	def testre_restore_video_from_s3_dryrun(self):
		self.mentry_not_in_s3.reload()
		self.assertTrue(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(), "tagged before test")
		self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'in s3 before test')
		self.assertTrue(kaltura_aws.SAVED_TO_S3 in self.mentry_not_in_s3.getTags(), "tagged after test")
		argv = ['restore_from_s3', '-i', self.entry_id_not_in_s3]
		rc = kaltura_aws._main(argv)
		self.assertEqual(rc, None)
		self.mentry_not_in_s3.reload()
		self.assertTrue(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(), "tagged after test")
		self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'in s3 after test')
		self.assertTrue(kaltura_aws.SAVED_TO_S3 in self.mentry_not_in_s3.getTags(), "saved after test")

	def testre_restore_video_from_s3_run(self):
		self.mentry_not_in_s3.reload()
		self.assertTrue(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(), "tagged before test")
		self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'in s3 before test')
		self.assertTrue(kaltura_aws.SAVED_TO_S3 in self.mentry_not_in_s3.getTags(), "tagged before test")
		argv = ['restore_from_s3', '--restore', '-i', self.entry_id_not_in_s3]
		for _ in range(0, 2):
			rc = kaltura_aws._main(argv)
			self.assertEqual(rc, None)
			self.mentry_not_in_s3.reload()
			self.assertFalse(kaltura_aws.PLACE_HOLDER_VIDEO in self.mentry_not_in_s3.getTags(), "not tagged after test")
			self.assertTrue(aws.s3_exists(self.entry_id_not_in_s3, self.bucket), 'in s3 after test')
			self.assertTrue(kaltura_aws.SAVED_TO_S3 in self.mentry_not_in_s3.getTags(), "tagged after test")

if __name__ == '__main__':
	unittest.main()

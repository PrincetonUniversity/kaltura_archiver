#!/usr/bin/env python
import logging, traceback
import os
import sys
import time

import boto3
from argparse import RawDescriptionHelpFormatter
import envvars

import kaltura
import kaltura.api
import kaltura.aws as aws

PLACE_HOLDER_VIDEO = "flavors_deleted"
SAVED_TO_S3 = "archived_to_s3"

DEFAULT_STATUS_LIST = "-1,-2,0,1,2,7,4"
#see site-packages/KalturaClient/Plugins/Core.py  - class KalturaEntryStatus(object):

from KalturaClient.Plugins.Core import  KalturaEntryStatus


REPLACE_ONLY_IF_YEARS_SINCE_PLAYED = 2

class KalturaArgParser(envvars.ArgumentParser):
    ENV_VARS = {'partnerId': 'KALTURA_PARTNERID|Kaltura Partner Id|',
                        'secret': 'KALTURA_SECRET|Kaltura secret to access API|',
                        'userId': 'KALTURA_USERID|Kaltura user Id|',
                        'awsAccessKey': 'AWS_ACCESS_KEY_ID|AWS access Key Id|',
                        'awsAccessSecret': 'AWS_SECRET_ACCESS_KEY|AWS secret access key|',
                        'awsBucket' : 'AWS_BUCKET|AWS s3 bucket for video storage|',
                        'videoPlaceholder' : 'PLACEHOLDER_VIDEO|placeholder video|placeholder_video.mp4'}

    DESCRIPTION = """This script interacts with a Kaltura KMC and AWS to list, copy to s3 and restore videos to and from AWS storage.
    
All actions are performed in DRYRUN mode by default, meaning they are logged but not performed. 
In addition to logging to the terminal actions are logged ./kaltura.log or kaltura-dryrun.log. 
The log file is chosen based on the execution mode. 

It  uses the following environment variables
"""

    @staticmethod
    def create(description=DESCRIPTION):

        evars = envvars.to_doc(KalturaArgParser.ENV_VARS)
        for k in evars:
            description = description + "\n\t%-15s:  %s" % (k, evars[k])

        loglevels = ['ERROR', 'WARN', 'INFO', 'DEBUG']
        parser = KalturaArgParser(description=description, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("--loglevel", "-l", choices=loglevels,  default=logging.INFO, help="log level  - default: INFO")

        subparsers = parser.add_subparsers(help='sub-command help')

        subparsers.add_parser('config', description='test access to Kaltura KMC, AWS').set_defaults(func=check_config)

        subparser = subparsers.add_parser('list', description="list matching videos ")
        subparser.add_argument("--mode", "-m", choices=["video", "flavor"], default="video", help="list video or flavor information")
        KalturaArgParser._add_filter_params(subparser)
        subparser.set_defaults(func=list)

        subparser = subparsers.add_parser('count', description="count matching videos ")
        KalturaArgParser._add_filter_params(subparser)
        subparser.set_defaults(func=count)

        subparser = subparsers.add_parser('s3copy', description="copy original flavors of matching videos to AWS-s3; skip flavors bigger than {} kb".format(CheckAndLog.SIZE_LIMIT_KB))
        subparser.add_argument("--s3copy", action="store_true", default=False, help="performs in dryrun mode, unless save param is given")
        subparser.add_argument("--tmp", default=".", help="directory for temporary files")
        KalturaArgParser._add_filter_params(subparser)
        subparser.set_defaults(func=copy_to_s3)

        subparser = subparsers.add_parser('restore', description="restore matching videos from AWS-s3")
        subparser.add_argument("--restore", action="store_true", default=False, help="performs in dryrun mode, unless restore param is given")
        subparser.add_argument("--tmp", default=".", help="directory for temporary files")
        KalturaArgParser._add_filter_params(subparser)
        subparser.set_defaults(func=restore_from_s3)

        subparser = subparsers.add_parser('replace_video', description="delete flavors and replace original with place holder video of matching entries  \
        IF entries have healthy archived copy in AWS-s3")
        subparser.add_argument("--replace", action="store_true", default=False, help="performs in dryrun mode, unless replace param is given")
        KalturaArgParser._add_filter_params(subparser)
        subparser.set_defaults(func=replace_videos)

        subparser = subparsers.add_parser('download', description="download original for given video ")
        subparser.add_argument("--id", "-i",  required=True, help="kaltura media entry id")
        subparser.add_argument("--tmp", default=".", help="directory for temporary files")
        subparser.set_defaults(func=download)

        description = """
check status of entries, that is check each matching entry for the following: 
  +  has original flavor in READY status,
  +  the {} tag is set iff and only iff there is a corresponding entry in S3 
  +  if it does not have an {} tag the S# entry's size should match the size of the original flavor  
""".format(SAVED_TO_S3, PLACE_HOLDER_VIDEO)
        subparser = subparsers.add_parser('health', description=description)
        KalturaArgParser._add_filter_params(subparser)
        subparser.set_defaults(func=health_check)

        return parser

    @staticmethod
    def _add_filter_params(subparser):
        subparser.add_argument("--category", "-c",  help="kaltura category")
        subparser.add_argument("--tag", "-t",  help="kaltura tag")
        subparser.add_argument("--id", "-i",  help="kaltura media entry id")
        subparser.add_argument("--unplayed", "-u",  type=int, help="unplayed for given number of years")
        subparser.add_argument("--played", "-p",  type=int, help="played within the the given number of years")
        subparser.add_argument("--noLastPlayed", "-n",  action="store_true", default=False, help="undefined LAST_PLAYED_AT attribute")
        subparser.add_argument("--first_page", "-f",  type=int, default=1, help="page number where to start iteration - default 1")
        subparser.add_argument("--page_size", "-s", type=int, default=kaltura.Filter.MAX_PAGE_SIZE,
                               help="number of entries per page - default {}".format(kaltura.Filter.MAX_PAGE_SIZE))
        subparser.add_argument("--max_entries", "-M",  type=int, default=-1, help="maximum number of entries to work on  - default unlimited")
        subparser.add_argument("--created", "-C",  type=int, help="creation time greater or equal given int (sec since UNIX)")
        return None


class CheckAndLog:
    SIZE_LIMIT_KB = 10000000

    def __init__(self, mentry):
        self.mentry = mentry
        self.entry = self.mentry.entry

    def has_original(self):
        self.original = self.mentry.getOriginalFlavor()
        yes = self.original != None
        self._log_action(yes, 'Entry has Original')
        return yes

    def original_ready(self):
        yes = kaltura.Flavor(self.original).isReady()
        message = 'Original Flavor {} status == READY'.format(self.original.getId())
        self._log_action(yes, message)
        return yes

    def original_below_size_limit(self):
        small_enough = self.original.getSize() <= CheckAndLog.SIZE_LIMIT_KB
        message = 'Original Flavor {} smaller than {}'.format(self.original.getId(), CheckAndLog.SIZE_LIMIT_KB)
        self._log_action(small_enough, message);
        return small_enough

    def no_such_tag(self, tag):
        yes = not (tag in self.entry.getTags())
        message = 'Entry does not have tag {}'.format(tag)
        self._log_action(yes, message)
        return yes

    def has_tag(self, tag):
        yes = tag in self.entry.getTags()
        message = 'Entry has tag {}'.format(tag)
        self._log_action(yes, message)
        return yes

    def _s3_size(self, bucket):
        if not hasattr(self, 's3_size'):
            self.s3_size = aws.s3_size(self.entry.getId(), bucket)
        return self.s3_size

    def aws_s3_matching_file(self, bucket):
        if (aws.s3_exists(self.entry.getId(), bucket)):
            yes = aws_compatible_size(self.original.getSize(), self._s3_size(bucket))
            message = 'Size-Match (s3://{}/{}) = {}  - Original Flavor Size - {} kb'.format(bucket, self.entry.getId(), self._s3_size(bucket), self.original.getSize())
        else:
            message = 'Exists (s3://{}/{})'.format(bucket, self.entry.getId())
            yes = False
        self._log_action(yes, message)
        return yes

    def aws_s3_below_size_limit(self, bucket):
        yes = self._s3_size(bucket)  <= (CheckAndLog.SIZE_LIMIT_KB * 1024)
        message = 's3://{}/{}) <= {}'.format(bucket, self.entry.getId(), CheckAndLog.SIZE_LIMIT_KB)
        self._log_action(yes, message)
        return yes

    def _log_action(self, yes, message):
        log_level = logging.DEBUG if (yes) else logging.INFO
        result = '' if (yes) else 'FAILURE - '
        self.mentry.log_action(log_level, True, "Check", '{}{}'.format(result, message))

def aws_compatible_size(o_size, s3_size):
    """
    Kaltura does not exactly report original flavor siezes
    We consider sizes compatible if the smaller kb size is within 3% of the bigger size

    :param o_size:    original flavor size in kb
    :param s3_size:    s3 file size in bytes
    :return: whether compatible
    """
    s3_kb = s3_size / 1024
    if (s3_kb < o_size):
        return (1.03 * s3_kb >= o_size)
    else:
        return (1.03 * o_size >= s3_kb)


def entry_health_check(mentry, bucket):
    original  = mentry.getOriginalFlavor()
    entry = mentry.entry

    # check whether item is 'healthy'
    # has original in READY state
    healthy = original != None and kaltura.Flavor(original).isReady()
    explanation = ''
    if (not healthy):
        explanation= 'ERROR: No healthy Original'

    # if there is an s3 entry it should be tagged SAVED_TO_S3
    s3Exists = aws.s3_exists(entry.getId(), bucket)
    saved_tag = SAVED_TO_S3 in entry.getTags()
    if healthy and  s3Exists and not saved_tag:
        explanation= 'ERROR: in bucket {} - but no {} tag'.format(bucket, SAVED_TO_S3)
        healthy = False
    # if it is tagged SAVED_TO_S3 there should be an s3 entry
    if healthy and  saved_tag and not s3Exists:
        explanation= 'ERROR: has tag {} - but not in bucket {}'.format(SAVED_TO_S3, bucket)
        healthy = False

    # if it is tagged PLACE_HOLDER_VIDEO it should also be tagged  SAVED_TO_S3
    replaced_tag = PLACE_HOLDER_VIDEO in entry.getTags()
    if healthy and  replaced_tag and not saved_tag:
        explanation= 'ERROR: has tag {} - but no {} tag'.format(PLACE_HOLDER_VIDEO, SAVED_TO_S3)
        healthy = False

    if (original):
        compatible_size = aws_compatible_size(original.getSize(), aws.s3_size(entry.getId(), bucket))
        # if it is saved and not tagged PLACE_HOLDER_VIDEO then original flavor and s3 entry size should match
        if healthy and saved_tag and not replaced_tag and not compatible_size:
            explanation = 'ERROR: is {} and not {} - size mismatch of bucket entry and original flavor'.format(SAVED_TO_S3, PLACE_HOLDER_VIDEO)
            healthy = False

        # if it is saved and sizes match then there should not be a replaced_tag
        if healthy  and saved_tag and compatible_size and replaced_tag:
            explanation = 'ERROR: is {} and  {} - but size match of bucket entry and original flavor'.format(SAVED_TO_S3, PLACE_HOLDER_VIDEO)
            healthy = False

        if (healthy and s3Exists and original.getSize() > CheckAndLog.SIZE_LIMIT_KB):
            explanation= 'WARNING: in bucket {} but original beyond size limit {}'.format(bucket, CheckAndLog.SIZE_LIMIT_KB)

    if (healthy and not explanation):
        explanation= 'HEALTHY'
    return  healthy, explanation


def copy_to_s3(params):
    """
    save original flavors to aws  for  matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    doit = _setup(params, 's3copy')
    filter = _create_filter(params)
    bucket = params['awsBucket']
    tmp = params['tmp']
    nerror = 0
    for entry in filter:
        done = False
        s3_file = entry.getId()

        checker = CheckAndLog(kaltura.MediaEntry(entry))
        if (checker.has_original() and checker.original_ready()):
            if (aws.s3_exists(s3_file, bucket)):
                checker.mentry.log_action(logging.INFO, doit, "Archived", 's3://{}/{}'.format(bucket, s3_file))
            else:
                if checker.original_below_size_limit():
                    # download from kaltura
                    fname = checker.mentry.downloadOriginal(tmp, doit)
                    if (fname):
                        # store to S3
                        aws.s3_store(fname, bucket, entry.getId(), doit)
                        kaltura.MediaEntry(entry).addTag(SAVED_TO_S3, doit)
                        checker.mentry.log_action(logging.INFO, doit, "Delete", fname)
                        if (doit):
                            os.remove(fname)
                else:
                    checker.mentry.log_action(logging.INFO, doit, "Skip Copy", "original flavor exceeds size limit {} kb".format(CheckAndLog.SIZE_LIMIT_KB))
            done = True

        if (not done):
            nerror += 1

    return nerror

def download(params):
    """
    save original flavors of first matching record to a local file

    :param params: hash that contains kaltura connetion information as well as filtering options given to download action
    :return:  0 upon succesful download
    """
    doit = _setup(params, None)
    tmp = params['tmp']
    filter = _create_filter(params)
    entry =   next(iter(filter))

    checker = CheckAndLog(kaltura.MediaEntry(entry))
    if (checker.has_original() and checker.original_ready()):
        fname = checker.mentry.downloadOriginal(tmp, doit)
        print("downloded to " + fname)
        return 0
    else:
        return 1


RESTORE_DONE = 0
RESTORE_WAIT_GLACIER = 1
RESTORE_FAILED = 2

def restore_from_s3(params):
    """
    restore original flavor from s3   for  matching kaltura records

    prints number counts of videos with different outcomes:  RESTORE_DONE, RESTORE_WAIT_GLACIER, RESTORE_FAILED

    :param params: hash that contains kaltura connection information as well as filtering options given for the restore action
    :return:  number of failures
    """
    doit = _setup(params, 'restore')
    filter = _create_filter(params)
    bucket = params['awsBucket']
    tmp = params['tmp']
    counts = [0,0,0]
    for entry in filter:
        rc = restore_entry_from_s3(kaltura.MediaEntry(entry), bucket, tmp, doit)
        counts[rc] += 1

    kaltura.logger.info("# {}: {}".format('RESTORE_FAILED', counts[RESTORE_FAILED]) )
    kaltura.logger.info("# {}: {}".format('RESTORE_WAIT_GLACIER', counts[RESTORE_WAIT_GLACIER]) )
    kaltura.logger.info("# {}: {}".format('RESTORE_DONE', counts[RESTORE_DONE]) )
    return counts[REPLACE_FAILED]

    return rc[RESTORE_FAILED];


def restore_entry_from_s3(mentry, bucket, tmp, doit):
    checker = CheckAndLog(mentry)
    s3_file = mentry.entry.getId()
    rc = RESTORE_FAILED;
    to_file = None

    if (checker.has_original() and checker.original_ready()) and aws.s3_exists(s3_file, bucket) and checker.has_tag(PLACE_HOLDER_VIDEO):
        # see whether we can get the S3 file - might still be in glacier
        if aws.s3_restore(s3_file, bucket, doit):
            # download from S3
            to_file = aws.s3_download( "{}/{}.s3".format(tmp, mentry.entry.getId()), bucket, s3_file, doit)

            # delete all flavors
            if mentry.deleteFlavors(doDelete=doit):
                # replace with original from s3
                if (mentry.replaceOriginal(to_file, doit)):
                    # indicate that this is not the place_holder (but original) video
                    mentry.delTag(PLACE_HOLDER_VIDEO)
                    rc = RESTORE_DONE
        else:
            mentry.log_action(logging.INFO, doit, 'Restore', 'Waiting for s3 file to come out of Glacier');
            rc = RESTORE_WAIT_GLACIER

    if (to_file):
        os.remove(to_file)
    if (rc == RESTORE_FAILED):
        mentry.log_action(logging.ERROR, doit, 'Restore Failed', '');
    return rc



REPLACE_DONE  = 0
REPLACE_DONE_BEFORE = 1
REPLACE_BIG_FILE_SKIP = 2
REPLACE_FAILED = 3

def replace_videos(params):
    """
    replace original videos with place holder video for matching entries

    prints counts of videos with different outcomes: REPLACE_DONE, REPLACE_DONE_BEFORE, REPLACE_BIG_FILE_SKIP, REPLACE_FAILED

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    doit = _setup(params, 'replace')
    filter = _create_filter(params)
    if (not params['noLastPlayed'] and not params['unplayed'] ) or (params['unplayed']  and params['unplayed'] < REPLACE_ONLY_IF_YEARS_SINCE_PLAYED):
        filter.years_since_played(REPLACE_ONLY_IF_YEARS_SINCE_PLAYED)
        kaltura.logger.info("FILTER ADJUSTED {}".format(filter))

    bucket = params['awsBucket']
    place_holder = params['videoPlaceholder']

    counts = [0, 0, 0, 0]
    entries = []
    for entry in filter:
        rc = replace_entry_video(kaltura.MediaEntry(entry), place_holder, bucket, doit)
        counts[rc] += 1
        if (rc == REPLACE_DONE):
            entries.append(entry)

    if (entries):
        # pause to give Kaltura time to concert the replace ment videos
        _pause(10 + len(entries) *3, doit)

        #good_status = [KalturaEntryStatus.READY, KalturaEntryStatus.PRECONVERT]
        good_status = [KalturaEntryStatus.READY]
        for entry in entries:
            mentry = kaltura.MediaEntry(entry)
            mentry.reload()
            if (not mentry.entry.getStatus().value in good_status):
                mentry.log_action(logging.ERROR, doit, 'Replace Failed', 'Video status {} not in {}'.format(entry.getStatus().value, good_status))
                counts[REPLACE_FAILED] += 1

    kaltura.logger.info("# {}: {}".format('REPLACE_FAILED', counts[REPLACE_FAILED]) )
    kaltura.logger.info("# {}: {}".format('REPLACE_DONE', counts[REPLACE_DONE]) )
    kaltura.logger.info("# {}: {}".format('REPLACE_DONE_BEFORE', counts[REPLACE_DONE_BEFORE]) )
    kaltura.logger.info("# {}: {}".format('REPLACE_BIG_FILE_SKIP', counts[REPLACE_BIG_FILE_SKIP]) )
    return counts[REPLACE_FAILED]


def replace_entry_video(mentry, place_holder, bucket, doit):
    """
    if preconditions are given replace video with given place holder

    :param mentry: kaltura.MediaEntry to be replaced
    :param place_holder:  place holder video file
    :param bucket: bucket tat contains s3 copy of original
    :param doit: log actions only unless doit is true
    :return: REPLACE_DONE, REPLACE_DONE_BEFORE, REPLACE_BIG_FILE_SKIP, or REPLACE_FAILED

    """
    checker = CheckAndLog(mentry)
    rc = REPLACE_FAILED
    if (checker.has_original() and checker.original_ready()):
        if (checker.aws_s3_matching_file(bucket)):
            # s3 file in bucket that matches in size
            if checker.aws_s3_below_size_limit(bucket):
                # delete derived flavors
                # then replace with place_holder video
                if mentry.deleteFlavors(doDelete=doit):
                    if mentry.replaceOriginal(place_holder, doit):
                        # indicate successful replace
                        mentry.addTag(PLACE_HOLDER_VIDEO, doit)
                        mentry.log_action(logging.INFO, doit, 'Replace', 'Complete');
                        rc = REPLACE_DONE
            else:
                # s3 file in bucket but exceed size limit
                mentry.log_action(logging.WARN, doit, 'Skip Replace', 'Big s3 file - can\'t be restored')
                rc = REPLACE_BIG_FILE_SKIP
        else:
            # original flavor size does not match s3 file size
            # fine if this has been replaced before
            # so check on relevant tag  after reloading
            mentry.reload()
            if checker.has_tag(PLACE_HOLDER_VIDEO) and checker.has_tag(SAVED_TO_S3):
                mentry.log_action(logging.INFO, doit, 'Replaced Earlier',
                                  'According to {} and {} tags at KMC'.format(PLACE_HOLDER_VIDEO, SAVED_TO_S3))
                rc = REPLACE_DONE_BEFORE
    if (rc == REPLACE_FAILED):
        mentry.log_action(logging.ERROR, doit, 'Replace Failed', '');
    return rc;


def _pause(secs, doit):
    for i in range(0,secs):
        sys.stdout.write('.')
        sys.stdout.flush()
        if (doit):
            time.sleep(1)
    sys.stdout.write('\n')

def health_check(params):
    """
    TODO
    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    _setup(params, None)
    filter = _create_filter(params)
    bucket = params['awsBucket']

    columns = []
    nerror = 0

    print('\t'.join(columns))
    columns = [kaltura.ORIGINAL, kaltura.ORIGINAL_STATUS,
               PLACE_HOLDER_VIDEO, SAVED_TO_S3]
    print "\t".join([kaltura.ENTRY_ID, 'status-ok'] + columns + ['s3-size', kaltura.ORIGINAL_SIZE, '---'])
    for entry in filter:
        mentry = kaltura.MediaEntry(entry);
        healthy, message = entry_health_check(mentry, bucket)
        vals = [mentry.report_str(kaltura.ENTRY_ID), str(healthy).ljust(len('status-ok'))]
        vals = vals + [mentry.report_str(c) for c in columns]
        vals = vals + [str(aws.s3_size(entry.getId(), bucket)/1024), mentry.report_str(kaltura.ORIGINAL_SIZE), message]

        print "\t".join(v.decode('utf-8') for v in vals)
        if (not healthy):
            mentry.log_action(logging.ERROR, True, 'STATUS', message)
            nerror +=1
    return nerror


def check_config(params):
    _setup(params, 'loglevel')
    return 0

def count(params):
    """
    count matching kaltura media entry records

    :param params: hash that contains kaltura connection information as well as filtering options given for the list action
    :return:  None
    """
    _setup(params, None)
    filter = _create_filter(params)
    cnt = filter.get_count()
    print("#COUNT\t{}".format(cnt))
    return 0


def list(params):
    """
    print matching kaltura records

    :param params: hash that contains kaltura connection information as well as filtering options given for the list action
    :return:  None
    """
    _setup(params, None)
    filter = _create_filter(params)

    if (params['mode'] == 'video'):
        columns = [kaltura.LAST_PLAYED_DATE, kaltura.LAST_PLAYED, kaltura.VIEWS,
                   kaltura.ENTRY_ID, SAVED_TO_S3, PLACE_HOLDER_VIDEO,
                   kaltura.TOTAL_SIZE, kaltura.ORIGINAL_SIZE, kaltura.ORIGINAL_STATUS,
                   kaltura.CREATED_AT_DATE, kaltura.CREATED_AT, kaltura.CREATOR_ID]
        print('\t'.join(columns))
        for entry in filter:
            kentry = kaltura.MediaEntry(entry)
            vals = [kentry.report_str(c) for c in columns]
            print("\t".join(v.decode('utf-8') for v in vals))
    else:
        columns = [kaltura.ENTRY_ID, kaltura.FLAVOR_ID, kaltura.ORIGINAL, kaltura.SIZE,
                   kaltura.CREATED_AT, kaltura.DELETED_AT,
                   kaltura.CREATED_AT_DATE, kaltura.DELETED_AT_DATE,
                   kaltura.STATUS]
        print('\t'.join(columns))
        for entry in filter:
            for f in kaltura.FlavorAssetIterator(entry):
                kf = kaltura.Flavor(f)
                vals = [kf.report_str(c) for c in columns]
                print("\t".join(v.decode('utf-8') for v in vals))
    return 0

def _create_filter(params):
    filter = kaltura.Filter().entry_id(params['id'])
    if  params['id'] is None:
        filter.status(DEFAULT_STATUS_LIST)
        if 'tag' in params:
            # implies all the other tags are there too
            # see ArgParser
            filter.tag(params['tag'])
            filter.category(params['category'])
            filter.years_since_played(params['unplayed']).played_within_years(params['played'])
            if (params['noLastPlayed']) :
                 filter.undefined_LAST_PLAYED_AT()
            filter.first_page(params['first_page']).page_size(params['page_size']).max_iter(params['max_entries']).created_greater_equal(params['created'])
    kaltura.logger.info("FILTER {}".format(filter))
    return filter

def _setup(params, doit_prop):
    doit = params[doit_prop] if doit_prop else True
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(message)s')
    handler.setFormatter(formatter)
    kaltura.logger.addHandler(handler)

    logging.root.setLevel(logging.INFO)
    kaltura.logger.setLevel(params['loglevel'])

    kaltura.logger.info("---")
    kaltura.logger.info("FUNC  {}".format(params['func']))
    for k in sorted(params.keys()):
        if k != 'func' and params[k] != None:
            kaltura.logger.info("PARAM %s=%s" % (k, '***' if "SECRET" in k.upper() else params[k]))


    # connect to Kaltura
    kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

    # Check for existence of placeholder video
    if not os.path.isfile(params['videoPlaceholder']):
        raise(RuntimeError("Can not access placeholder file '{}'".format(params['videoPlaceholder'])))

    # check on AWS bucket
    bucket = params['awsBucket']
    try:
        s3resource = boto3.resource('s3')
        s3resource.meta.client.head_bucket(Bucket=bucket)
    except Exception as e:
        raise(RuntimeError("Can't access AWS Bucket '{}'".format(bucket)))
    return doit

def _main(argv):
    parser = KalturaArgParser.create()
    args = parser.parse_args(argv)
    params = envvars.to_value(KalturaArgParser.ENV_VARS)
    print(args)
    params.update(vars(args))
    return params['func'](params)

if __name__ == '__main__':
    try:
        status = _main(sys.argv[1:])
        sys.exit(status)
    except Exception as e:
        print("\n" + str(e) + "\n")
        parser = KalturaArgParser.create()
        parser.print_usage()
        if (True or not isinstance(e, RuntimeError)):
            traceback.print_exc()
        sys.exit(-1)

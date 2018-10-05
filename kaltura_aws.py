#!/usr/bin/env python
import logging, traceback
import os
import sys
import boto3
from argparse import RawDescriptionHelpFormatter
import envvars

import kaltura
import kaltura.api
import kaltura.aws as aws

PLACE_HOLDER_VIDEO = "flavors_deleted"
SAVED_TO_S3 = "archived_to_s3"

class KalturaArgParser(envvars.ArgumentParser):
    ENV_VARS = {'partnerId': 'KALTURA_PARTNERID|Kaltura Partner Id|',
                        'secret': 'KALTURA_SECRET|Kaltura secret to access API|',
                        'userId': 'KALTURA_USERID|Kaltura user Id|',
                        'awsAccessKey': 'AWS_ACCESS_KEY_ID|AWS access Key Id|',
                        'awsAccessSecret': 'AWS_SECRET_ACCESS_KEY|AWS secret access key|',
                        'awsBucket' : 'AWS_BUCKET|AWS s3 bucket for video storage|',
                        'videoPlaceholder' : 'PLACEHOLDER_VIDEO|placeholder video|placeholder_video.mp4'}

    DESCRIPTION = """This script interacts with a Kaltura KMC and AWS to list, archive and restore videos to and from AWS storage.
    
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

        loglevels = ['CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG', 'NOTSET']
        parser = KalturaArgParser(description=description, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("--loglevel", "-l", choices=loglevels,  default=logging.INFO, help="log level  - default: INFO")

        subparsers = parser.add_subparsers(help='sub-command help')

        subparsers.add_parser('config', description='test access to Kaltura KMC, AWS').set_defaults(func=check_config)

        subparser = subparsers.add_parser('list', description="list matching videos ")
        subparser.add_argument("--mode", "-m", choices=["video", "flavor"], default="video", help="list video or flavor information")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=list)

        subparser = subparsers.add_parser('archive', description="archive original flavors of matching videos to AWS-s3")
        subparser.add_argument("--archive", action="store_true", default=False, help="performs in dryrun mode, unless save param is given")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=archive_to_s3)

        subparser = subparsers.add_parser('replace_video', description="delete flavors and replace original with place holder video of matching entries  \
        IF entries have healthy archived copy in AWS-s3")
        subparser.add_argument("--replace", action="store_true", default=False, help="performs in dryrun mode, unless replace param is given")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=replace_videos)

        description = """
check status of entries, that is check each matching entry for the following: 
  +  has original flavor in READY status,
  +  the {} tag is set iff and only iff there is a corresponding entry in S3 
  +  if it does not have an {} tag the S# entry's size should match the size of the original flavor  
""".format(SAVED_TO_S3, PLACE_HOLDER_VIDEO)

        subparser = subparsers.add_parser('status', description=description)
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=health_check)

        return parser

    @staticmethod
    def _add_filter_parsm(subparser):
        subparser.add_argument("--category", "-c",  help="kaltura category")
        subparser.add_argument("--tag", "-t",  help="kaltura tag")
        subparser.add_argument("--id", "-i",  help="kaltura media entry id")
        subparser.add_argument("--unplayed", "-u",  type=int, help="unplayed for given number of years")
        subparser.add_argument("--played", "-p",  type=int, help="played within the the given number of years")
        subparser.add_argument("--noLastPlayed", "-n",  action="store_true", default=False, help="undefined LAST_PLAYED_AT attribute")
        return None


class CheckAndLog:
    def __init__(self, mentry):
        self.mentry = mentry

    def hasOriginal(self):
        self.original = self.mentry.getOriginalFlavor()
        yes = self.original != None
        self._log_action(yes, 'Entry has Original')
        return yes

    def originalIsReady(self):
        yes = kaltura.Flavor(self.original).isReady()
        message = 'Original Flavor {} status == READY'.format(self.original.getId())
        self._log_action(yes, message)
        return yes

    def doesNotHaveTag(self, tag):
        yes = not (tag in self.mentry.entry.getTags())
        message = 'Entry does not have tag {}'.format(tag)
        self._log_action(yes, message)
        return yes

    def hasTag(self, tag):
        yes = tag in self.mentry.entry.getTags()
        message = 'Entry has tag {}'.format(tag)
        self._log_action(yes, message)
        return yes

    def aws_S3_file(self, bucket):
        yes = matching_aws_s3_file(self.original, self.mentry.getId(), bucket)
        message = 'Size-Mismatch (s3://{}/{}) Orginal Flavor Size'.format(bucket, self.mentry.entry.getId())
        self._log_action(yes, message)
        return yes

    def _log_action(self, yes, message):
        log_level = logging.DEBUG if (yes) else logging.INFO
        result = '' if (yes) else 'FAILURE - '
        self.mentry.log_action(log_level, True, "Check", '{}{}'.format(result, message))

def matching_aws_s3_file(original, s3_file, bucket):
    s3_file_size_kb = aws.s3_size(s3_file, bucket) / 1024
    return abs(s3_file_size_kb - original.getSize()) <= 1


def entry_info(mentry, bucket):
    info = {}
    original  = mentry.getOriginalFlavor()
    info['original'] = original.getId() if original else None
    info['originalStatus'] = kaltura.FlavorAssetStatus.str(original.getStatus()) if original else None
    info['originalSize'] = original.getSize() if original else None
    info['s3Exists'] = aws.s3_exists(mentry.entry.getId(), bucket)
    info['s3Size'] = aws.s3_size(mentry.entry.getId(), bucket) if info['s3Exists'] else None
    for k in [SAVED_TO_S3,  PLACE_HOLDER_VIDEO]:
        info[k] = k in mentry.entry.getTags()

    # check whether item is 'healthy'
    # has original in READY state
    healthy = original != None and kaltura.Flavor(original).isReady()
    if (not healthy):
        info['status'] = 'ERROR: No healthy Original'
    # if there is an s3 entry it should be tagged SAVED_TO_S3
    if healthy and  info['s3Exists'] and not info[SAVED_TO_S3]:
        info['status'] = 'ERROR: in bucket {} - but no {} tag'.format(bucket, SAVED_TO_S3)
        healthy = False
    # if it is tagged SAVED_TO_S3 there should be an s3 entry
    if healthy and  info[SAVED_TO_S3] and not info['s3Exists']:
        info['status'] = 'ERROR: has tag {} - but not in bucket'.format(SAVED_TO_S3, bucket)
        healthy = False
    # if it is tagged PLACE_HOLDER_VIDEO it should also be tagged  SAVED_TO_S3
    if healthy and  info[PLACE_HOLDER_VIDEO] and not info[SAVED_TO_S3]:
        info['status'] = 'ERROR: has tag {} - but no {} tag'.format(PLACE_HOLDER_VIDEO, SAVED_TO_S3)
        healthy = False
    # if it is not tagged PLACE_HOLDER_VIDEO original flavor and s3 entry size should match
    if healthy and  info[PLACE_HOLDER_VIDEO] and not matching_aws_s3_file(original, mentry.entry.getId(), bucket):
        info['status'] = 'ERROR: has tag {} - bucket entry / original flavor size-mismatch '.format(PLACE_HOLDER_VIDEO)
        healthy = False
    info['healthy'] = healthy
    if (healthy):
        info['status'] = 'HEALTHY'
    return info


def archive_to_s3(params):
    """
    save original flavors to aws  for  matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    doit = setup(params, 'archive')
    filter = _create_filter(params)
    bucket = params['awsBucket']
    nerror = 0
    for entry in filter:
        done = False
        s3_file = entry.getId()

        checker = CheckAndLog(kaltura.MediaEntry(entry))
        if (checker.hasOriginal() and checker.originalIsReady()):
            if (aws.s3_exists(s3_file, bucket)):
                checker.mentry.log_action(logging.INFO, doit, "Archived", 's3://{}/{}'.format(bucket, s3_file))
                done = True
            else:
                # download from kaltura
                fname = checker.mentry.downloadOriginal(doit)
                if (fname):
                    # store to S3
                    aws.s3_store(fname, bucket, entry.getId(), doit)
                    kaltura.MediaEntry(entry).addTag(SAVED_TO_S3, doit)
                    done = True
        if (not done):
            nerror += 1

    return nerror

def replace_videos(params):
    """
    replace original videos with place holder video for matching entries
    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    doit = setup(params, 'replace')
    filter = _create_filter(params)
    bucket = params['awsBucket']
    place_holder = params['videoPlaceholder']

    nerror = 0
    for entry in filter:
        if (not replace_entry_video(kaltura.MediaEntry(entry), place_holder, bucket, doit)):
            nerror += 1

    return nerror

def health_check(params):
    """
    TODO
    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params, None)
    filter = _create_filter(params)
    bucket = params['awsBucket']

    columns = []
    nerror = 0
    for entry in filter:
        mentry = kaltura.MediaEntry(entry);
        status = entry_info(mentry, bucket)
        if (not columns):
            columns = sorted(status.keys())
            print('\t'.join(columns))

        print "\t".join([repr(status[c]) for c in columns])
        if (not status['healthy']):
            nerror +=1
    return nerror

def replace_entry_video(mentry, place_holder, bucket, doit):
    checker = CheckAndLog(mentry)
    if (checker.hasOriginal()):
        if (checker.aws_S3_file(bucket)):
            # delete derived flavors
            if (not mentry.deleteFlavors(doDelete=doit)):
                return False

            # replace with place_holder video
            if (not mentry.replaceOriginal(place_holder, doit)):
                return False

            # indicate successful replace
            mentry.addTag(PLACE_HOLDER_VIDEO, doit)
            return True
        else:
            # original flavor size does not match s3 file size
            # fine if this has been processed before
            # so check on relevant tag
            # reset kaltura connection
            kaltura.api.getClient(True)
            if checker.hasTag(PLACE_HOLDER_VIDEO):
                mentry.log_action(logging.INFO, doit, 'Replaced', 'tag: {} ==> Place Holder Video at KMC'.format(PLACE_HOLDER_VIDEO))
                return True
    return False;



def is_healthy_entry(mentry, place_holder, bucket, doit):
    original = mentry.getOriginalFlavor()
    return False;

def check_entry_ready(mentry):
    checker = CheckAndLog(mentry)
    return checker.hasOriginal() and checker.originalIsReady()


def check_config(params):
    setup(params, 'loglevel')
    return 0

def list(params):
    """
    print matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params, None)
    filter = _create_filter(params)
    bucket = params['awsBucket']

    if (params['mode'] == 'video'):
        columns = [kaltura.LAST_PLAYED_DATE, kaltura.LAST_PLAYED, kaltura.VIEWS,
                   kaltura.ENTRY_ID, kaltura.TOTAL_SIZE, SAVED_TO_S3, PLACE_HOLDER_VIDEO, kaltura.ORIGINAL, kaltura.ORIGINAL_STATUS,
                   kaltura.CATEGORIES_IDS, kaltura.CATEGORIES, kaltura.NAME]
        print('\t'.join(columns))
        for entry in filter:
            kentry = kaltura.MediaEntry(entry)
            vals = [kentry.report_str(c) for c in columns]
            s = "\t".join(v.decode('utf-8') for v in vals)
            print(s)
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
                s = "\t".join(v.decode('utf-8') for v in vals)
                print(s)
    return None


def _create_filter(params):
    filter = kaltura.Filter()
    filter.entry_id(params['id']).tag(params['tag']).category(params['category'])
    filter.years_since_played(params['unplayed']).played_within_years(params['played'])
    if (params['noLastPlayed']) :
        filter.undefined_LAST_PLAYED_AT();
    kaltura.logger.info("FILTER {}".format(filter))
    return filter

def setup(params, doit_prop):
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

def _get_env_vars():
    env = envvars.to_value(KalturaArgParser.ENV_VARS)
    return env


def _main(args):
    params = _get_env_vars()
    params.update(args)
    return params['func'](params)

if __name__ == '__main__':
    parser = KalturaArgParser.create()
    try:
        args = parser.parse_args()
        status = _main(vars(args))
        sys.exit(status)
    except Exception as e:
        print("\n" + str(e) + "\n")
        parser.print_usage()
        if (True or not isinstance(e, RuntimeError)):
            traceback.print_exc()
        sys.exit(-1)

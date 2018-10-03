#!/usr/bin/env python 
import logging, traceback
import os
import sys
import time
import boto3
from argparse import RawDescriptionHelpFormatter
import envvars

import kaltura
import kaltura.aws as aws

FLAVORS_DELETED_TAG = "flavors_deleted"
PLACE_HOLDER_VIDEO = "place_holder_video"
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

        subparser = subparsers.add_parser('del_flavors', description="delete derived flavors of matching videos at Kaltura KMC ")
        subparser.add_argument("--delete", action="store_true", default=False, help="performs in dryrun mode, unless delete param is given")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=del_flavors)

        subparser = subparsers.add_parser('archive', description="archive original flavors of matching videos to AWS-s3")
        subparser.add_argument("--archive", action="store_true", default=False, help="performs in dryrun mode, unless save param is given")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.set_defaults(func=archive_to_s3)

        subparser = subparsers.add_parser('replace_video', description="delete flavors and replace original with place holder video of matching entries  \
        IF entries have healthy archived copy in AWS-s3")
        subparser.add_argument("--replace", action="store_true", default=False, help="performs in dryrun mode, unless replace param is given")
        KalturaArgParser._add_filter_parsm(subparser)
        subparser.add_argument("--wait", "-w",  type=int, default=60, help="wait time in seconds before checking that uploaded original's status is READY")
        subparser.set_defaults(func=replace_videos)

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


class CheckCondition:
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
        s3_file = self.mentry.entry.getId()
        s3_file_size_kb = aws.s3_size(s3_file, bucket) / 1024
        yes = abs(s3_file_size_kb - self.original.getSize()) <= 1
        message = 'Size(s3://{}/{})={} kb equals  size of Flavor {} '.format(bucket, s3_file, s3_file_size_kb, self.original.getSize())
        self._log_action(yes, message)
        return yes

    def _log_action(self, yes, message):
        log_level = logging.DEBUG if (yes) else logging.INFO
        result = '' if (yes) else 'FAILURE - '
        self.mentry.log_action(log_level, True, "Check", '{}{}'.format(result, message))


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

        checker = CheckCondition(kaltura.MediaEntry(entry))
        if (checker.hasOriginal() and checker.originalIsReady()):
            if (aws.s3_exists(s3_file, bucket)):
                checker.mentry.log_action(logging.INFO, doit, "Archived", 's3://{}/{}'.format(bucket, s3_file))
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
    wait = params['wait']

    nerror = 0
    check_ready = []
    for entry in filter:
        if (not replace_entry_video(kaltura.MediaEntry(entry), place_holder, bucket, doit)):
            nerror += 1
        else:
            check_ready.append(entry)

    if (check_ready):
        kaltura.api.log_action(logging.INFO, doit, 'Entry', '*', 'Wait',  '{} sec'.format(wait))
        if (doit):
            time.sleep(wait)
        kaltura.api.log_action(logging.INFO, doit, 'Entry', '*', 'Check',  'Check that uploaded videos have status READY')

    for entry in check_ready:
        if (not check_entry_ready(kaltura.MediaEntry(entry))):
             nerror += 1
    return nerror

def del_flavors(params):
    """
    delete derived flavors from  matching kaltura records from matching entries

    skip entries that are not marked with the tag

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    doit = setup(params, 'de;ete')
    filter = _create_filter(params)

    nerror = 0;
    for entry in filter:
        if (not del_entry_flavors(kaltura.MediaEntry(entry), doit)):
            nerror += 1
    return nerror

def replace_entry_video(mentry, place_holder, bucket, doit):
    checker = CheckCondition(mentry)
    try:
        if (checker.hasOriginal()):
            if (checker.aws_S3_file(bucket)):
                # delete derived flavors
                if not del_entry_flavors(mentry, doit):
                    return False

                # delete original flavor
                kaltura.Flavor(checker.original).delete(doit)

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
                return checker.hasTag(PLACE_HOLDER_VIDEO)
    finally:
        if (not checker.hasTag(PLACE_HOLDER_VIDEO)):
            checker.mentry.log_action(logging.ERROR, doit, 'Replace Video', 'FAILURE')


def check_entry_ready(mentry):
    checker = CheckCondition(mentry)
    return checker.hasOriginal() and checker.originalIsReady()


def del_entry_flavors(mentry, doit):
    # delete entry flavors returns False when there is no original
    if (mentry.deleteDerivedFlavors(doDelete=doit)):
        mentry.addTag(FLAVORS_DELETED_TAG, doit)
        return True
    else:
        return False

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
        columns = ['lastPlayedDate', 'lastPlayedAt', 'views', 'id', 'totalSize', 'isArchived', 'hasOriginal', 'originalStatus', 'categories', 'categoriesIds', '|', 'tags', '|',  'name']
        print('\t'.join(columns))
        for entry in filter:
            kentry = kaltura.MediaEntry(entry)
            s = ""
            s += "{:>10}\t".format(kentry.getLastPlayedDate())
            s += "{:>12}\t".format(entry.getLastPlayedAt())
            s += "{}\t".format(entry.getViews())
            s += "{:>12}\t".format(entry.getId())
            s += "{:>10}\t".format(kentry.getTotalSize())
            s += "{}\t".format(str(aws.s3_exists(entry.getId(), bucket)))
            original = kentry.getOriginalFlavor()
            s += "{}\t".format(str(original != None))
            s += "{}\t".format(str(kaltura.FlavorAssetStatus.str(original.getStatus()) if original != None else 'None'))
            s += "{:.15}\t".format(entry.getCategories())
            s += "{}\t".format(entry.getCategoriesIds())
            s += "|\t"
            s += "{}\t".format(entry.getTags())
            s += "|\t"
            s += "{}\t".format(entry.getName())
            print s
    else:
        columns = ['id', 'flavor-id', 'original', 'size(KB)', 'createdAt', 'createdAtDate', 'deletedAt', 'deletedAtDate', 'status', 'status']
        print('\t'.join(columns))
        for entry in filter:
            for f in kaltura.FlavorAssetIterator(entry):
                s = ""
                s += "{}\t".format(entry.getId())
                s += "{}\t".format(f.getId())
                s += "{}\t".format(f.getIsOriginal())
                s += "{:>10}\t".format(f.getSize())
                s += "{:>12}\t".format(f.getCreatedAt())
                s += "{:>10}\t".format(kaltura.dateString(f.getCreatedAt()))
                s += "{:>12}\t".format(f.getDeletedAt())
                s += "{:>10}\t".format(kaltura.dateString(f.getDeletedAt()))
                s += "{}\t".format(f.getStatus().value)
                s += "{}\t".format(kaltura.FlavorAssetStatus.str(f.getStatus()))
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

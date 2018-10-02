#!/usr/bin/env python 
import logging, traceback
import os
import sys
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

        subparsers.add_parser('config', description='test access to Kaltura KMC, AWS').set_defaults(func=setup)

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

def archive_to_s3(params):
    """
    save original flavors to aws  for  matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    doit = params['archive']
    bucket = params['awsBucket']
    logging.info("save_to_aws archive={} {}".format(doit, filter))

    failed_save = []
    no_orig = []
    failed_replace = []
    for entry in filter:
        mentry = kaltura.MediaEntry(entry)
        original = mentry.getOriginalFlavor()
        s3_file = entry.getId()

        if (not original):
            no_orig.append(entry)
            continue

        if (aws.s3_exists(s3_file, bucket)):
            mentry.log_action(logging.ERROR, doit, "Archived", 's3://{}/{}'.format(bucket, s3_file))
        else:
            # download from kaltura
            fname = mentry.downloadOriginal(doit)
            if (not fname):
                continue

            # store to S3
            aws.s3_store(fname, bucket, entry.getId(), doit)
            kaltura.MediaEntry(entry).addTag(SAVED_TO_S3, doit)

    if (failed_save):
        logging.error("FAILED to save original for {}".format(",".join(e.getId() for e in failed_save)))
    if (no_orig):
        logging.warn("Entries without original flavor: {}".format(",".join(e.getId() for e in no_orig)))
    return None

def replace_videos(params):
    """
    replace original videos with place holder video for matching entries
    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    doit = params['replace']
    bucket = params['awsBucket']
    place_holder = params['videoPlaceholder']
    logging.info("replace_videos archive={} {}".format(doit, filter))

    failed_replace = []

    for entry in filter:
        if (not replace_entry_video(kaltura.MediaEntry(entry), place_holder, bucket, doit)):
                failed_replace.append(entry)

    if (failed_replace):
        logging.error("FAILED to replace original for {}".format(",".join(e.getId() for e in failed_replace)))
    return None


def replace_entry_video(mentry, place_holder, bucket, doit):
    # bail if there is no original
    original = mentry.getOriginalFlavor()
    if (original == None):
        mentry.log_action(logging.ERROR, doit, "Abort", 'Entry has no ORIGINAL')
        return False

    # bail if no have healthy s3 back up
    s3_file = mentry.entry.getId()
    if (not have_equal_sizes(original, s3_file, bucket, doit)):
        mentry.log_action(logging.ERROR, doit, "Size Mismatch",
                          's3://{}/{}: Flavor {} has size {}kb'.
                         format(bucket, s3_file, original.getId(), original.getSize()))
        return False

    # delete derived flavors
    if not del_entry_flavors(mentry, doit):
        return False

    # delete original flavor
    kaltura.Flavor(original).delete(doit)

    # replace with place_holder video
    if (not mentry.replaceOriginal(place_holder, doit)):
        return False

    # indicate successful replace
    mentry.addTag(PLACE_HOLDER_VIDEO, doit)
    return True


def del_entry_flavors(mentry, doit):
    # delete entry flavors returns False when there is no original
    if (mentry.deleteDerivedFlavors(doDelete=doit)):
        mentry.addTag(FLAVORS_DELETED_TAG, doit)
        return True
    else:
        return False

def have_equal_sizes(original, s3_file, bucket, doit):
    s3_file_size_kb = aws.s3_size(s3_file, bucket) / 1024
    return abs(s3_file_size_kb - original.getSize()) <= 1

def del_flavors(params):
    """
    delete derived flavors from  matching kaltura records from matching entries

    skip entries that are not marked with the tag

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    doit = params['delete']
    logging.info("del_flavors delete={} {}".format(doit, filter))

    failed = []
    for entry in filter:
        if (not del_entry_flavors(kaltura.MediaEntry(entry), doit)):
            failed.append(entry)
    if (failed):
        logging.error("FAILED to delete derived flavors from {}".format(",".join(e.getId() for e in failed)))
    return None

def list(params):
    """
    print matching kaltura records

    :param params: hash that contains kaltura connetion information as well as filtering options given for the list action
    :return:  None
    """
    setup(params)
    filter = _create_filter(params)
    mode = params['mode']
    bucket = params['awsBucket']
    logging.info("list {} {}".format(mode, filter))

    if (params['mode'] == 'video'):
        columns = ['lastPlayedDate', 'lastPlayedAt', 'views', 'id', 'totalSize', 'isArchived', 'hasOriginal', 'categories', 'categoriesIds', '|', 'tags', '|',  'name']
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
            s += "{}\t".format(str(kentry.getOriginalFlavor() != None))
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
    return filter

def setup(params):
    # connect to Kaltura
    kaltura.api.startSession(partner_id=params['partnerId'], user_id=params['userId'], secret=params['secret'])

    # Check for existence of placeholder video
    if not os.path.isfile(params['videoPlaceholder']):
        raise(RuntimeError("Can not access placeholder file '{}'".format(params['videoPlaceholder'])))
    else:
        logging.info("setup: videoPlaceholder={}".format(params['videoPlaceholder']))
    print(params)

    # check on AWS bucket
    bucket = params['awsBucket']
    try:
        s3resource = boto3.resource('s3')
        s3resource.meta.client.head_bucket(Bucket=bucket)
        logging.info("Using AWS bucket {}".format(bucket))
    except Exception as e:
        raise(RuntimeError("Can't access AWS Bucket '{}'".format(bucket)))


def _get_env_vars():
    env = envvars.to_value(KalturaArgParser.ENV_VARS)
    for v in env:
        logging.info("%s=%s" % (v, '***' if "SECRET" in v.upper() else env[v]))
    return env


def _main(args):
    if 'loglevel' in args:
        logging.getLogger().setLevel(args['loglevel'])
    logging.info(args)
    params = _get_env_vars()
    params.update(args)
    #print(params)
    params['func'](params)

if __name__ == '__main__':
    parser = KalturaArgParser.create()
    try:
        args = parser.parse_args()
        _main(vars(args))
        sys.exit(0)
    except Exception as e:
        print("\n" + str(e) + "\n")
        parser.print_usage()
        if (not isinstance(e, RuntimeError)):
            traceback.print_exc()
        sys.exit(-1)

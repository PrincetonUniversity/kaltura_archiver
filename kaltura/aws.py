import logging
import boto3
import botocore

import api

_s3 = boto3.resource('s3')

def s3_exists(filename, bucketname):
    """
    :param filename:  file name
    :param bucketname:  name of S3/GLACIER bucket
    :return:  whether filename exists in bucket
    """
    try:
        _s3.Object(bucketname, filename).load()
        return True
    except botocore.exceptions.ClientError as e:
        logging.debug("s3_object_exists({}, {}): {}".format(bucketname, filename, e))
        return False

def s3_size(filename, bucketname):
    """
    :param filename:  file name
    :param bucketname:  name of S3/GLACIER bucket
    :return:  size in bytes if object exists; otherwise return 0
    """
    try:
        o = _s3.Object(bucketname, filename)
        return o.content_length
    except botocore.exceptions.ClientError as e:
        logging.debug("s3_object_size({}, {}): {}".format(bucketname, filename, e))
        return 0

def s3_store(src_file, bucketname, bucketfile, doit=False):
    if (doit):
        _s3.meta.client.upload_file(src_file, bucketname, bucketfile)
    api.log_action(logging.INFO, doit, "AWS-S3",  "{}".format(bucketfile), "Upload", "to s3://{} from {}".format(bucketname,  src_file))
    return None

def s3_restore(filename, bucketname, doit=False):
    """
    if file's storage indicates that it is in GLACUER issue a restore request unless there is a request already underway

     - calling this method for the first time issues a restore request if necessary
     - on following calls it will simply return false
     - and once file is available for download it returns True

    :param filename: filename to restore
    :param bucketname: name of Glacier bucket
    :param doit: unless doit  simply dryRun/log actions
    :return: whether file is available in S3 ready to be downloaded
    """

    try:
        obj = _s3.Object(bucketname, filename)

        if obj.storage_class == 'GLACIER':
            if str(obj.restore).startswith('ongoing-request="false"'):
                api.log_action(logging.INFO, "AWS-S3", "{}/{}".format(bucketname, filename), "Request Restore", "storage-class={}".format(obj.storage_class))
                if doit:
                    bucket = _s3.Bucket(bucketname)
                    bucket.meta.client.restore_object(
                        Bucket=bucketname,
                        Key=filename,
                        RestoreRequest={'Days': 2,
                                        'GlacierJobParameters': {'Tier': 'Bulk'}}
                    )
            else:
                api.log_action("AWS-S3", "{}/{}".format(bucketname, filename), "Restoring", "obj.restore={}".format(obj.restore))
        elif (obj.storage_class == None):
            api.log_action(logging.INFO, "AWS-S3", "{}/{}".format(bucketname, filename), "Available", "")
            return True
        else:
            api.log_action(logging.ERROR, "AWS-S3", "{}/{}".format(bucketname, filename), "Unknown class", "obj.restore={}".format(obj.restore))
    except botocore.exceptions.ClientError as e:
        api.log_action(logging.ERROR, "AWS-S3", "{}/{}".format(bucketname, filename), "Access Error", e)

    return False


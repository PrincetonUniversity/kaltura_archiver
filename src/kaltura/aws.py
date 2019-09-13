import logging
import boto3
import botocore
from botocore.exceptions import ClientError
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
    except ClientError as e:
        api.logger.debug("s3_object_exists({}, {}): {}".format(bucketname, filename, e))
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
    except ClientError as e:
        api.logger.debug("s3_object_size({}, {}): {}".format(bucketname, filename, e))
        return -1

def s3_store(src_file, bucketname, bucketfile, doit=False):
    """
    upload src_file to s3://bucketname/bucketfile
    :param src_file:  name of local file
    :param bucketname:   name of bucket
    :param bucketfile:  bucket key
    :param doit: if false - simply trace
    :return:
    """
    if (doit):
        _s3.meta.client.upload_file(src_file, bucketname, bucketfile)
    api.log_action(logging.INFO, doit, "AWS-S3",  "{}".format(bucketfile), "Upload", "to s3://{}/{} from {}".format(bucketname,  bucketfile, src_file))
    return None

def s3_download(to_file, bucketname, bucketfile, doit=False):
    try:
        if (doit):
            _s3.meta.client.download_file(bucketname, bucketfile, to_file)
        api.log_action(logging.INFO, doit, "AWS-S3",  "{}".format(bucketfile), "Download", "s3://{}/{} to {}".format(bucketname,  bucketfile, to_file))
        return to_file
    except ClientError as e:
        return None

def s3_delete(bucketname, bucketfile, doit=False):
    if (doit):
        _s3.Object(bucket_name=bucketname, key=bucketfile).delete()
    api.log_action(logging.INFO, doit, "AWS-S3",  "{}".format(bucketfile), "Delete", "s3://{}/{}".format(bucketname,  bucketfile))
    return None

def s3_restore(filename, bucketname, doit=False):
    """
    if file's storage indicates that it is in GLACIER issue a restore request unless there is a request already underway

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
        s3_path = "s3://{}/{}".format(bucketname, filename)
        api.log_action(logging.INFO, doit, "AWS-S3", filename, "Status", "class={} restore={} path {}".format(obj.storage_class, obj.restore, s3_path))
        if obj.storage_class == 'GLACIER':
             if obj.restore is None:
                api.log_action(logging.INFO, doit, "AWS-S3", filename, "Request Restore", "path {}".format(s3_path))
                if doit:
                    bucket = _s3.Bucket(bucketname)
                    bucket.meta.client.restore_object(
                        Bucket=bucketname,
                        Key=filename,
                        RestoreRequest={'Days': 2,
                                        'GlacierJobParameters': {'Tier': 'Bulk'}}
                    )
                return False
             elif obj.restore.startswith('ongoing-request="false"'):
                api.log_action(logging.INFO, doit, "AWS-S3", filename, "Ready", "path {}".format(s3_path))
                return True
        else:
            # if its not in GLACIER - no need to restore
            api.log_action(logging.ERROR, doit, "AWS-S3", filename, "No-GLACIER", "class={} restore={} path {}".format(obj.storage_class, obj.restore, s3_path))
            return True
    except ClientError as e:
        api.log_action(logging.ERROR, doit, "AWS-S3", filename, "Access Error", "{} path {}".format(e, s3_path))

    return False

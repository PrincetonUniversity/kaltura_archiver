from __future__ import print_function
import sys
import boto3
import traceback
import argparse

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

_client = boto3.client('ecs')

def lambda_handler(event, context):
    response = runDockerTask(event)
    print(response)


def runDockerTask(args):
    if (process_args(args)):
        if (args['taskVersion'] == 'LATEST'):
            # TODO find latest task version
            # aws ecs list-task-definitions --family-prefix kaltura-restores --sort DESC --max-items 1
            # unless a version number is passed
            eprint('NOT YET implemented')
            return 0

        networkConfig = {
            'awsvpcConfiguration': {
                'subnets': args['subnet'] ,
                'securityGroups': [ args['securityGroup'] ],
                'assignPublicIp': 'DISABLED'
            }
        }

        response = _client.run_task(
            cluster=args['cluster'],
            launchType='FARGATE',
            taskDefinition="{}:{}".format(args['taskName'], args['taskVersion']),
            count=1,
            platformVersion=args['platformVersion'],
            networkConfiguration=networkConfig
        )
        return response

def process_args(args):
    error = False
    for key in ['cluster', 'subnet', 'securityGroup', 'taskName', 'platformVersion']:
        if ((not key in args)) or (not bool(args[key])):
            eprint('missing {} argument'.format(key))
            error = True
    if (not error):
        args['platformVersion']  = args['platformVersion'].upper()
        splits = args['taskName'].split(':')
        if (len(splits) != 2):
            eprint("taskName '{}' does not have format name:version".format(args['taskName']))
            error = True
        else:
            args['taskVersion'] = splits[1]
            try:
                args['taskVersion'] = int(args['taskVersion'])
            except ValueError:
                args['taskVersion'] = args['taskVersion'].upper()
                if (args['taskVersion'] != 'LATEST'):
                    eprint("task version in '{}' is neither a number nore 'LATEST'".format(args['taskName']))
                    error = True
            args['taskName'] = splits[0]
    return not error


class ArgParser(argparse.ArgumentParser):

    @staticmethod
    def create():
        description = "define AWS task to run docker container\n"
        parser = ArgParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("--cluster", "-c",  required=True, help="cluster name - defaults to taskName")
        parser.add_argument("--securityGroup",  required=True, help="name of securityGroup")
        parser.add_argument("--subnet",  nargs='+', help="name of subnet")
        parser.add_argument("--platformVersion",  "-p",  default='LATEST', help="platformVersion : number or LATEST")
        parser.add_argument('taskName', help='taskName:version, where version is a positive integer or the string latest')
        return parser

    def parse_args(self, args=None, namespace=None):
        print(args)
        return super(ArgParser, self).parse_args(args, namespace)


"""
 Function called when run from the command line
"""
if __name__ == '__main__':
    try :
        parser = ArgParser.create()
        args = parser.parse_args()
        vargs = vars(args)
        print("event for lambda_handler: {}".format(vargs))
        runDockerTask(vargs)
    except Exception as e:
        traceback.print_stack()
        traceback.print_exc()

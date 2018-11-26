#!/usr/bin/env python
import sys, argparse
import envvars
from puldap import PuLdap, LDAP_ENV_VARS

LDAP_QUERY_PATTERN = '&(uid={})(|(puresource=authentication=enabled)(puresource=authentication=goingaway))'
URL_PATTERN =  'https://kmc.kaltura.com/index.php/kmcng/content/entries/entry/{}/metadata'
def _build_ldap_query_expression(uid):
    expr =  LDAP_QUERY_PATTERN.format(uid)
    return expr


class AddLdapStatusParser(envvars.ArgumentParser):

    @staticmethod
    def create():
        description = "add a column that indicates whether the netid found in the creatrId column is active\n"
        description += "script uses the following environment variables:\n" + envvars.ArgumentParser.describe_vars(LDAP_ENV_VARS)
        parser = AddLdapStatusParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("--tsv", "-t",  default=sys.stdin, type=argparse.FileType('r'), help="tsv file; first line must contain column names")
        parser.add_argument("--creatorId", "-c",  default='creatorId', help="name of column that contains netid/email")
        parser.add_argument("--entryId", "-e",  default='entryId', help="name of column that contains teh kaltura entry id")
        return parser

    def parse_args(self, args=None, namespace=None):
        args= argparse.ArgumentParser.parse_args(self, args)
        args.env = envvars.to_value(LDAP_ENV_VARS)

        try:
            args.ldap = PuLdap(args.env['host'], args.env['port'])
            args.ldap.bind(args.env['user'], args.env['password'])
        except Exception as e:
            raise e
        return args

def _enhance(tsvin, entryid_col, netid_col, ldap):
    line = tsvin.readline().strip()
    header = line.split("\t")
    entry_idx = header.index(entryid_col)
    netid_idx = header.index(netid_col)

    print("\t".join([line, 'status', 'name', 'org_unit']))
    for line in tsvin.readlines():
        line = line.strip()
        cols = line.split("\t")

        # get netid and chop off '@....' if given as email
        netid = cols[netid_idx]
        if (netid.find('@') >= 0 ):
            netid = netid[:netid.find('@')]
        #determine ldap status, name, and org-unit
        name, active, ou  = '', 'inactive', ''
        try:
            res_type, res_data, res_msgid, res_controls = next(ldap.all_results_with(_build_ldap_query_expression(netid), ['displayName', 'cn', 'ou']))
            data = res_data[0][1]
            if data['displayName']:
                name  = data['displayName'][0]
            elif data['cn']:
                name = data['cn'][0]
            if ('ou' in data): 
                ou = data['ou'][0]
            else: 
                ou = ''
            status = 'active'
        except StopIteration as e:
            status = 'inactive'
            name = ''

        print("\t".join([line, status, name, ou]))

if __name__ == '__main__':
    parser = AddLdapStatusParser.create()
    args = parser.parse_args()

    _enhance(args.tsv, args.entryId, args.creatorId, args.ldap)

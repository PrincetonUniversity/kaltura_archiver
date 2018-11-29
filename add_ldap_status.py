#!/usr/bin/env python
import sys, argparse
import envvars
from puldap import PuLdap, LDAP_ENV_VARS

LDAP_QUERY_UID_PATTERN = 'uid={}'
LDAP_QUERY_SPONSOR_PATTERN = 'universityid={}'
URL_PATTERN =  'https://kmc.kaltura.com/index.php/kmcng/content/entries/entry/{}/metadata'

def _build_ldap_uid_expr(uid):
    expr =  LDAP_QUERY_UID_PATTERN.format(uid)
    return expr

def _build_ldap_sponsor_expr(sponsorid):
    expr =  LDAP_QUERY_SPONSOR_PATTERN.format(sponsorid)
    return expr

def _ldap_empty_results(fields):
    results = {}
    for f in fields:
        results[f] = ''
    return results

def _ldap_get_match(ldap, expr, fields):
    res_type, res_data, res_msgid, res_controls = next(ldap.all_results_with(expr, fields))
    results = _ldap_empty_results(fields)
    data = res_data[0][1]
    for k in data.keys():
        results[k] = data[k][0]
    return results


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

    print("\t".join([line, 'status', 'puincomingemail', 'pustatus', 'sponsor', 'name', 'org_unit']))
    for line in tsvin.readlines():
        line = line.strip()
        cols = line.split("\t")

        # get netid and chop off '@....' if given as email
        netid = cols[netid_idx]
        eid = cols[entry_idx]
        if (netid.find('@') >= 0 ):
            netid = netid[:netid.find('@')]
        _do_entry(ldap, eid, netid)

def _do_entry(ldap, eid, netid):
        #determine ldap status, name, and org-unit
        fields = ['universityidref', 'displayName', 'cn', 'ou', 'pustatus', 'puincomingemail']
        try:
            results = _ldap_get_match(ldap, _build_ldap_uid_expr(netid), fields)
            if not results['displayName']:
                results['displayName'] = results['cn'][0]
            if results['universityidref']:
                sponsor = _ldap_get_match(ldap, _build_ldap_sponsor_expr(results['universityidref']), ['uid'])['uid']
                results['sponsor'] = sponsor
                _do_entry(ldap, eid, sponsor)
            results['status'] = 'active'

        except StopIteration as e:
            results = _ldap_empty_results(fields)
            results['status'] = 'inactive'
            pass;
        if (not results.has_key('sponsor')):
            results['sponsor'] = ''
        print("\t".join([eid, netid, results['status'], results['puincomingemail'], results['pustatus'], results['sponsor'], results['displayName'], results['ou']]))

if __name__ == '__main__':
    parser = AddLdapStatusParser.create()
    args = parser.parse_args()

    _enhance(args.tsv, args.entryId, args.creatorId, args.ldap)

#!/usr/bin/env python
import sys, argparse
import envvars
from puldap import PuLdap, LDAP_ENV_VARS

LDAP_QUERY_UID_PATTERN = '|(campusid={})(uid={})'
LDAP_QUERY_SPONSOR_PATTERN = 'universityid={}'
URL_PATTERN =  'https://kmc.kaltura.com/index.php/kmcng/content/entries/entry/{}/metadata'

def _build_ldap_uid_expr(uid):
    return LDAP_QUERY_UID_PATTERN.format(uid, uid)

def _build_ldap_sponsor_expr(sponsorid):
    return LDAP_QUERY_SPONSOR_PATTERN.format(sponsorid)

def _ldap_empty_results(fields):
    results = {}
    for f in fields:
        results[f] = ''
    return results

def _ldap_has_more(iter):
    try:
        next(iter);
        return True
    except StopIteration:
        return False

def _ldap_get_match(ldap, expr, fields):
    results = _ldap_empty_results(fields)
    iter = ldap.all_results_with(expr, fields)
    res_type, res_data, res_msgid, res_controls = next(iter)
    if (not _ldap_has_more(iter)):
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

    header = True
    for line in tsvin.readlines():
        line = line.strip()
        cols = line.split("\t")

        # get netid and chop off '@....' if given as email
        netid = cols[netid_idx]
        eid = cols[entry_idx]
        if (netid.find('@') >= 0 ):
            netid = netid[:netid.find('@')]
        _do_entry(ldap, eid, netid, header)
        header = False

def _do_entry(ldap, eid, netid, header, sponsorId = ''):
        #determine ldap status, name, and org-unit
        fields = ['universityid', 'pustatus', 'universityidref', 'puincomingemail', 'emailbox', 'emailrewrite', 'displayName', 'cn', 'ou']
        if (header):
            print("\t".join(['entryId', 'sponsering', 'netid'] + fields))
        try:
            results = _ldap_get_match(ldap, _build_ldap_uid_expr(netid), fields)
            if not results['displayName']:
                results['displayName'] = results['cn']
            if results['universityidref'] and results['pustatus'] == '#sv':
                sponsor = _ldap_get_match(ldap, _build_ldap_sponsor_expr(results['universityidref']), ['uid'])['uid']
                results['sponsor'] = sponsor
                _do_entry(ldap, eid, sponsor, False, results['universityid'])
            results['status'] = 'active'

        except StopIteration as e:
            results = _ldap_empty_results(fields)
            results['status'] = 'inactive'
            pass;
        if (not results.has_key('sponsor')):
            results['sponsor'] = ''
        print("\t".join([eid, sponsorId, netid] + map(lambda(x) :  results[x]  , fields) ))

if __name__ == '__main__':
    parser = AddLdapStatusParser.create()
    args = parser.parse_args()

    _enhance(args.tsv, args.entryId, args.creatorId, args.ldap)

from __future__ import print_function

import sys, argparse, logging
import ldap,ldap.resiter
import envvars

# LDAP documentation lives at https://www.python-ldap.org/en/latest/reference

LDAP_ENV_VARS = {'host': 'LDAP_SERVER|Domain name of ldap server|',
                   'user': 'LDAP_USER|User to query LDAP_SERVER|',
                   'port': 'LDAP_PORT|Port at LDAP_SERVER|636',
                   'password': 'LDAP_PWD|Password for LDAP_USER|'}

class PuLDAPConnection(ldap.ldapobject.LDAPObject,ldap.resiter.ResultProcessor):
    pass

class PuLdap:
    def __init__(self, server,  port = 636, trace_level = 0):
        self.base = 'o=princeton university,c=us'
        self.url = "ldaps://%s:%s" % (server, port)
        try:
            self.connection = PuLDAPConnection(self.url)
        except ldap.LDAPError as e:
            raise Exception("%s Could not connect: %s" % (e.__class__.__name__, self))
        if (not self.connection):
            raise Exception(("%s Could not connect: %s" % ("None connection", self)))
        logging.debug("PuLdap()->" + str(self))

    def bind(self, user, password):
        """
        bind to ldap server
        :param user: user name
        :param password: password
        """
        try:
            self.user = "uid=%s,%s" % (user, self.base)
            self.prt_password =  "(%dchar)" % len(password)
            self.prt_user =  user
            logging.debug("PuLdap.bind '%s'   '%s'" % (self.user, self.prt_password))
            self.connection.bind_s(self.user, password)
        except ldap.LDAPError as e:
            raise Exception("%s Could not bind: %s" % (e.__class__.__name__, self))

    def all_results_with(self, expr, attrlist = []):
        """
        return iterator of all ldap entries matching the given ldap filter expression
        :param expr: ldap expression
        :param attrlist: attributes to request from ldap
        :return:  iterator for matching ldap entries
        """
        scope = ldap.SCOPE_SUBTREE
        filter = "(%s)" % expr
        logging.debug("all_results_with [%s] filter=%s" % (self, filter))
        search_id = self.connection.search(self.base, scope, filter, attrlist)
        returns =  self.connection.allresults(search_id)
        return returns

    def __str__(self):
        if (hasattr(self, 'connection')):
            s = "Conn(%s)" % self.connection.get_option(ldap.OPT_URI)
        else:
            s ="None(%s)" % self.url
        if hasattr(self, 'user'):
            s = s + ", user:%s, pwd:%s" %  (self.prt_user, self.prt_password)
        return s

    @staticmethod
    def get_property_list(results, property):
        """
        return values of given property for each result in results iterator

        :param results: iterator returning tuple, where second elem is an ldap res_data
        :param property: name of property to retrieve
        :return: list of property values
        """
        lst = []
        for res_type, res_data, res_msgid, res_controls in results:
            for dn, entry in res_data:
                pval = ",".join(_.decode() for _ in entry[property])
                lst.append(pval)
        return lst

    @staticmethod
    def get_properties(ldap_entry, properties):
        """
        grab the ldap_entry's values for the given properties and return in a list
        add "" where the entry has no ptoperty value

        :param ldap_entry:
        :param properties:
        :return: ldap_entry's property values
        """
        ldap_keys = ldap_entry.keys()
        vals = []
        for p in properties:
            if p in ldap_keys:
                pval = ",".join(_.decode() for _ in ldap_entry[p])
                vals.append(pval)
            else:
                vals.append("")
        return vals

    @staticmethod
    def print_file(results, properties, file=sys.stdout):
        """
        print tab separated table if property values for each of the results

        based on https://www.python-ldap.org/en/latest/reference/ldap-resiter.html

        :param results: iterator returning tuple, where second elem is an ldap res_data
        :param properties: list of property names
        :param file:    output file
        :return: number of printed results
        """
        i = 0
        print("#" + "\t".join(properties), file=file)
        for res_type, res_data, res_msgid, res_controls in results:
            for dn, entry in res_data:
                logging.debug("result " + "\t".join(("%d" % i, str(dn), str(entry))))
                print("\t".join(PuLdap.get_properties(entry, properties)), file=file)
                i = i + 1
        return i

class LDAPArgParser(envvars.ArgumentParser):

    @staticmethod
    def create():
        loglevels = ['CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG', 'NOTSET']
        description = "connect to LDAP server and list matching records if no returns are given retrieve 'uid' field values\n\n"
        description += envvars.ArgumentParser.describe_vars(LDAP_ENV_VARS)
        parser = LDAPArgParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("--expr", "-e", required=True, help="ldap seearch filter expression")
        parser.add_argument("--loglevel", "-l", choices=loglevels,  default=logging.INFO, help="log level  - default: ERROR")
        parser.add_argument("--out", "-o",  default=sys.stdout, type=argparse.FileType('w'), help="output file listing matches")
        parser.add_argument('returns', nargs='*', help="ldap fields to request")
        return parser

    def parse_args(self, args=None, namespace=None):
        args= argparse.ArgumentParser.parse_args(self, args)
        args.env = envvars.to_value(LDAP_ENV_VARS)
        if (not args.returns):
            args.returns = ['uid']
        logging.getLogger().setLevel(args.loglevel)

        try:
            args.ldap = PuLdap(args.env['host'], args.env['port'])
            args.ldap.bind(args.env['user'], args.env['password'])
        except Exception as e:
            raise e
        logging.debug("%s  returns %s" % (args.ldap, ",".join(args.returns)))
        return args


if __name__ == '__main__':
    parser = LDAPArgParser.create()
    args = parser.parse_args()

    n_printed = PuLdap.print_file(args.ldap.all_results_with(args.expr, args.returns), args.returns, file=args.out)
    args.out.close()
    logging.info("#total matches: %d for %s  %s" % (n_printed, args.ldap, args.expr))

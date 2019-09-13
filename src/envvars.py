import os
import argparse

"""
describe a set of environment variables through a hash, 
that maps a key to a string containing with the following format: 
    VAR_NAME|description|optional default value

for example 

{ 'user': 'LDAP_USER|User to query LDAP_SERVER|',
  'password': 'LDAP_PWD|Password for LDAP_USER|'} 
                        
"""

def to_doc(described_variables):
    """
    return a hash mapping keys to a human readable string
    containing the environmant variable name, its description and option default value

    the returned hash is intended to be used in printing documentation
    """
    cvars = {}
    for k in described_variables:
        evar, edoc, edef = described_variables[k].split('|')
        if edef != '': edoc = edoc + " - default: " + edef
        cvars[evar] = edoc
    return cvars

def to_value(described_variables):
    """
    compute a hash mapping keys to the value of the environment variables defined in described_variables[key]

    :return: return computed hash
    :raise: RuntimeError if an environment variable with an optional value is undefined
    """
    missing = []
    evars = {}
    for k in described_variables:
        evar, edoc, edef = described_variables[k].split('|')
        evars[k] = os.getenv(evar)
        if not evars[k]:
            evars[k] = edef
        if not evars[k]:
            missing.append(evar)
    if missing:
        raise RuntimeError("Missing environment variables: %s" % ", ".join(missing))
    return evars



class ArgumentParser(argparse.ArgumentParser):
    @staticmethod
    def describe_vars(described_variables):
        env_descr = "The script uses the following environment variables:"
        doc = to_doc(described_variables)
        for k in to_doc(described_variables):
            env_descr = env_descr + "\n\t%-15s:  %s" % (k, doc[k])
        return env_descr


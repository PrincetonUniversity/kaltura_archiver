#!/usr/bin/env python 
from kaltura_aws import * 

def test_size(s3_size, o_size, want):
    result = aws_compatible_size(o_size, s3_size)
    description = 'aws_compatible_size: {}, {}'.format(s3_size, o_size)
    label = 'SUCCESS' if result == want else 'FAILURE'
    print("\t".join([label, description]))

if __name__ == '__main__':
    test_size(1339130980, 1310720, True)
    test_size(251149730,   245760, True)
    test_size(220350223, 215040, True)
    test_size(204800, 207, False)
    test_size(204800, 206, True)
    test_size(204800, 205, True)

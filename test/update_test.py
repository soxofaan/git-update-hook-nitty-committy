#!/usr/bin/env python

# Copyright (c) 2011 Stefaan Lippens

import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import update


class UpdateTest(unittest.TestCase):

    def test_normalize_message(self):
        data = [
        ('foo', 'foo'),
        ('FOO', 'foo'),
        ('bar    bal', 'bar bal'),
        (' bar  \t  bal ', ' bar bal '),
        ('a:B: c%D!e...', 'ab cde'),
        ]
        for message, expected in data:
            actual = update.normalize_message(message)
            self.assertEqual(actual, expected)





if __name__ == '__main__':          
    unittest.main()

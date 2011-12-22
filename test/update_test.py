#!/usr/bin/env python

# Copyright (c) 2011 Stefaan Lippens

import os
import sys
import unittest
import tempfile
import shutil

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


class MessageHistogramTest(unittest.TestCase):

    def setUp(self):
        self._work_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._work_dir)

    def test_constructor(self):
        db_file = os.path.join(self._work_dir, 'db.sqlite')
        self.assertFalse(os.path.exists(db_file))
        h = update.MessageHistogram(db_file)
        self.assertTrue(os.path.exists(db_file))

    def test_observe(self):
        db_file = os.path.join(self._work_dir, 'db.sqlite')
        h = update.MessageHistogram(db_file)
        h.observe('a')
        h.observe('bb')
        h.observe('a')
        top_n = h.get_top_n_messages(n=10)
        expected = [('a', 2), ('bb', 1)]
        self.assertEqual(top_n, expected)

    def test_top_n(self):
        db_file = os.path.join(self._work_dir, 'db.sqlite')
        h = update.MessageHistogram(db_file)
        h.observe('a')
        h.observe('bb')
        h.observe('a')
        h.observe('ccc')
        h.observe('a')
        h.observe('bb')
        top_n = h.get_top_n_messages(n=2)
        expected = [('a', 3), ('bb', 2)]
        self.assertEqual(top_n, expected)
        top_n = h.get_top_n_messages(n=1)
        expected = [('a', 3)]
        self.assertEqual(top_n, expected)

    def test_in_top_n(self):
        db_file = os.path.join(self._work_dir, 'db.sqlite')
        h = update.MessageHistogram(db_file)
        h.observe('a')
        h.observe('bb')
        h.observe('a')
        self.assertTrue(h.in_top_n('a'))
        self.assertTrue(h.in_top_n('bb'))
        self.assertFalse(h.in_top_n('ccc'))

if __name__ == '__main__':
    unittest.main()

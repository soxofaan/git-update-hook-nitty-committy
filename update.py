#!/usr/bin/env python

# Copyright (c) 2011 Stefaan Lippens

'''
Git update hook Nitty Committy
==============================
Git update hook that manages a commit message histogram
and complains about or blocks pushes with messages that are too common.

Usage as hook
-------------
Copy/symlink update.py to hooks/update in the git repo to protect.

This script will be invoked by git with three arguments: 
1) ref name
2) current SHA1 of that ref (or 0000...0 for new refs)
3) newly pushed SHA1 for the ref

Additional usage
----------------
Additionally you can also invoke this script manually without with extra
options (and possibly without those hook-related argments) 
for inspection or additional functionality. 
Use option --help for more info.

'''

import os
import sys
import subprocess
import sqlite3
import logging
import re
import optparse

# TODO: support for pushing new branches (instead of ignoring them)
# TODO: work with config file to define behavior: block push, delay push, randomly block push, trigger command, keep user score, ...
# TODO: config to set logging level/target
# TODO: config to set top N size
# TODO: support for whitelisted commit messages (e.g. automated system commits)
# TODO: trim off long tail from database (regularly, based on db file size, row count, time?)
# TODO: add command line interface to query/reset/trim the histogram
# TODO: keep user score/karma
# TODO: add cli option to remove an entry from the database



def git_log(begin, end):
    proc = subprocess.Popen(['git', 'log', '--no-merges', '--format=%an:%cn:%s', begin + '..' + end], stdout=subprocess.PIPE)
    stdout = proc.communicate()[0]
    assert proc.returncode == 0
    log = []
    for line in stdout.split('\n'):
        if len(line) > 1:
            log.append(tuple(line.split(':', 2)))
    return log

def normalize_message(message):
    '''
    Normalize a message by collapsing whitespace, removing capitalization, unimportant characters, ...
    '''
    message = message.lower()
    message = re.sub('[^a-z0-9 ]', '', message)
    message = re.sub('\s+', ' ', message).strip()
    return message

class MessageHistogram(object):
    '''
    Wrapper class that manages a message histrogram in an sqlite database file
    '''

    def __init__(self, db_file_name):
        logging.debug('MessageHistogram from file ' + db_file_name)

        if not os.path.exists(db_file_name):
            MessageHistogram._create_database(db_file_name)

        self._conn = sqlite3.connect(db_file_name)

    @classmethod
    def _create_database(cls, db_file_name):
        '''
        Create the database and tables in given sqlite file.
        '''
        logging.debug('Creating database in file "{0}".'.format(db_file_name))
        conn = sqlite3.connect(db_file_name)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE message_histogram (
                message varchar(160),
                count int unsigned,
                UNIQUE (message)
            )
        ''')
        conn.commit()

    def observe(self, message):
        '''Observe a message: increase its counter.'''
        c = self._conn.cursor()
        try:
            c.execute('INSERT INTO message_histogram (message, count) VALUES (:msg, 1)', {'msg': message})
        except sqlite3.IntegrityError:
            c.execute('UPDATE message_histogram SET count = count + 1 WHERE message = :msg', {'msg': message})
        self._conn.commit()
        logging.debug('Increased count for message "{0}"'.format(message))

    def dump_messages(self):
        c = self._conn.cursor()
        c.execute('SELECT message, count FROM message_histogram')
        return c.fetchall()

    def get_top_n_messages(self, n=10):
        '''Get the top N messages.'''
        c = self._conn.cursor()
        c.execute('SELECT message, count FROM message_histogram ORDER BY count DESC LIMIT ?', (n,))
        return c.fetchall()

    def in_top_n(self, message, n=10):
        '''Check whether the given message is in the top N (and return the given count if so).'''
        top_n = self.get_top_n_messages(n)
        for msg, count in top_n:
            if msg == message:
                return count



def main():
    logging.basicConfig(level=logging.WARNING)
    logging.debug('sys.argv = {0!r}'.format(sys.argv))

    parser = optparse.OptionParser(usage='%prog [options] [ref currsha1 newsha1]')
    parser.add_option('--dbdump',
        dest='dbdump', action='store_true', default=False,
        help='Dump the complete message histogram database',
    )
    parser.add_option('--top',
        dest='topdump', action='store_true', default=False,
        help='Show the top "forbidden" messages of the message histogram.',
    )
    parser.add_option('--observe', metavar='MSG',
        dest='to_observe', action='append', default=[],
        help='Observe/add the given messages to the histogram.',
    )

    (options, args) = parser.parse_args()


    db_filename = os.path.splitext(__file__)[0] + '.messagehistogram.sqlite'


    if options.dbdump:
        histogram = MessageHistogram(db_filename)
        for message, count in histogram.dump_messages():
            print '{0:6d} {1}'.format(count, message)
    elif options.topdump:
        histogram = MessageHistogram(db_filename)
        for message, count in histogram.get_top_n_messages(10):
            print '{0:6d} {1}'.format(count, message)
    elif len(options.to_observe) > 0:
        histogram = MessageHistogram(db_filename)
        for msg in options.to_observe:
            histogram.observe(msg)
    else:
        if len(args) != 3:
            parser.error('Three arguments expected')
        (ref, current, new) = args

        if current == '0000000000000000000000000000000000000000':
            # Pushing a new branch/tag: not easy to do a git log here.
            # TODO: support checking of new branches
            return

        if new == '0000000000000000000000000000000000000000':
            # Removing a ref: nothing to do.
            return

        # Get log messages
        log = git_log(current, new)

        # Load commit message database
        histogram = MessageHistogram(db_filename)

        for (author, committer, msg) in log:
            msg = normalize_message(msg)
            if histogram.in_top_n(msg):
                print 'Warning: I don\'t like this commit message (by {author}): "{msg}"'.format(msg=msg, author=author)
            histogram.observe(msg)



if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print sys.argv[0], 'failed with exception:', repr(e)


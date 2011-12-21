#!/usr/bin/env python

# Copyright (c) 2011 Stefaan Lippens

'''
Git update hook Nitty Committy
==============================
Git update hook that manages a commit message histogram
and complains about or blocks pushes with messages that are too common.

Usage:
-----
Copy/symlink update.py to hooks/update in the git repo to protect.

'''

import os
import sys
import subprocess
import sqlite3
import logging


# TODO: support for pushing new branches (00000)
# TODO: support for non-fast forward pushes
# Safeguard against crashes: don't block pushe when wsomething fails
# TODO: normalize messages (capitalization, non alphanum characters, ...)

def git_log(begin, end):
    proc = subprocess.Popen(['git', 'log', '--no-merges', '--format=%an:%cn:%s', begin + '..' + end], stdout=subprocess.PIPE)
    stdout = proc.communicate()[0]
    assert proc.returncode == 0
    log = []
    for line in stdout.split('\n'):
        if len(line) > 1:
            log.append(tuple(line.split(':')))
    return log


class MessageHistogram(object):
    '''
    Wrapper class that manages a message histrogram
    '''

    def __init__(self, db_file_name):
        logging.debug('MessageHistogram from file ' + db_file_name)

        if not os.path.exists(db_file_name):
            MessageHistogram.create_database(db_file_name)

        self._conn = sqlite3.connect(db_file_name)

    @classmethod
    def create_database(cls, db_file_name):
        logging.debug('creating database')
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

    def get_count(self, message):
        '''Get the count for a message'''
        c = self._conn.cursor()
        c.execute('SELECT count FROM message_histogram WHERE message = ? LIMIT 1', (message,))
        count = c.fetchone()
        if count == None:
            count = 0
        return count

    def increase(self, message):
        '''Increase the count for a message'''
        c = self._conn.cursor()
        try:
            c.execute('INSERT INTO message_histogram (message, count) VALUES (:msg, 1)', {'msg': message})
        except sqlite3.IntegrityError:
            c.execute('UPDATE message_histogram SET count = count + 1 WHERE message = :msg', {'msg': message})
        self._conn.commit()

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


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    logging.debug('sys.argv = {0!r}'.format(sys.argv))
    (ref, current, new) = sys.argv[1:4]

    if current == '0000000000000000000000000000000000000000':
        # Pushing a new branch/tag: not easy to do a git log here.
        # TODO: support checking of new branches
        sys.exit(0)

    # Get log messages
    log = git_log(current, new)

    # Load commit message database
    filename = os.path.splitext(__file__)[0] + '.db.sqlite'
    histogram = MessageHistogram(filename)

    for (author, committer, msg) in log:
        if histogram.in_top_n(msg):
            print 'Warning: bad commit message (by {author}): "{msg}"'.format(msg=msg, author=author)
        histogram.increase(msg)




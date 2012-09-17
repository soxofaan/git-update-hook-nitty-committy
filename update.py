#!/usr/bin/env python

# Copyright (c) 2011 Stefaan Lippens

'''
Git update hook Nitty Committy
==============================
Git update hook that manages a commit message histogram
and complains about or blocks pushes with messages that are too common.

http://github.com/soxofaan/git-update-hook-nitty-committy
'''

import os
import sys
import subprocess
import sqlite3
import logging
import re
import optparse
import json

# TODO: support for pushing new branches (instead of ignoring them)
# TODO: work with config file to define behavior: block push, delay push, randomly block push, trigger command, keep user score, ...
# TODO: trim off long tail from database (regularly, based on db file size, row count, time?)
# TODO: add command line interface to query/reset/trim the histogram
# TODO: keep user score/karma

# Where the hook scripts live (relative to git repo root).
# Used to search for configs and store database.
HOOK_DIR = '.git/hooks'

# Default configuration settings.
DEFAULT_CONFIG = {
    "top-size": 20,
    "white-list": [],
    "log-level": logging.WARNING,
    "db-filename": os.path.join(HOOK_DIR, 'update.nitty-committy.messagehistogram.sqlite'),
}


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

    def delete(self, message):
        '''Remove the entry for a message.'''
        c = self._conn.cursor()
        c.execute('DELETE FROM message_histogram WHERE message = :msg', {'msg': message})
        self._conn.commit()

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
        top_n = self.get_top_n_messages(n=n)
        for msg, count in top_n:
            if msg == message:
                return count


def load_config(config_filename):
    # Start with default config values
    global DEFAULT_CONFIG
    config = DEFAULT_CONFIG

    # If available: load a config file and override default values.
    try:
        with open(config_filename, 'r') as f:
            config.update(json.load(f))
    except:
        # No valid config found.
        pass

    return config


def main():
    # Load config values form (optional) config file.
    config_filename = os.path.join(HOOK_DIR, 'update.nitty-committy.cfg')
    config = load_config(config_filename)

    # Set log level according to config.
    log_level = config['log-level']
    logging.basicConfig(level=log_level)

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
    parser.add_option('--delete', metavar='MSG',
        dest='to_delete', action='append', default=[],
        help='Delete the given messages from the histogram.',
    )

    (options, args) = parser.parse_args()

    # Get settings from config
    top_size = config['top-size']
    white_list = [normalize_message(msg) for msg in config['white-list']]
    db_filename = config['db-filename']

    if options.dbdump:
        histogram = MessageHistogram(db_filename)
        for message, count in histogram.dump_messages():
            print '{0:6d} {1}'.format(count, message)
    elif options.topdump:
        histogram = MessageHistogram(db_filename)
        for message, count in histogram.get_top_n_messages(top_size):
            print '{0:6d} {1}'.format(count, message)
    elif len(options.to_observe) > 0:
        histogram = MessageHistogram(db_filename)
        for msg in options.to_observe:
            histogram.observe(msg)
    elif len(options.to_delete) > 0:
        histogram = MessageHistogram(db_filename)
        for msg in options.to_delete:
            histogram.delete(msg)

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
            if msg in white_list:
                continue
            if histogram.in_top_n(msg, n=top_size):
                print 'Warning: I don\'t like this commit message (by {author}): "{msg}"'.format(msg=msg, author=author)
            histogram.observe(msg)


if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print sys.argv[0], 'failed with exception:', repr(e)

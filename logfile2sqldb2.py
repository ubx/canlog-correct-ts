#!/usr/bin/env python
# coding: utf-8

"""
Converts can.logger to sql sqlite3 db.

"""

from __future__ import absolute_import, print_function

import sqlite3
import sys
import argparse
from datetime import datetime

import can
from can import LogReader, MessageSync


def my_logger(conn, messages):
    conn.executemany("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)", messages)
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        "python logfile2sql",
        description="Writes can log file into sql sqlite3 db.")

    parser.add_argument('infile', metavar='input-file', type=str,
                        help='The file to read. For supported types see can.LogReader.')

    parser.add_argument('outfile', metavar='output-file', type=str,
                        help='The file to write. For supported types see can.LogReader.')

    parser.add_argument("-v", action="count", dest="verbosity",
                        help='''How much information do you want to see at the command line?
                        You can add several of these e.g., -vv is DEBUG''', default=2)

    # print help message when no arguments were given
    if len(sys.argv) < 2:
        parser.print_help(sys.stderr)
        import errno
        raise SystemExit(errno.EINVAL)

    results = parser.parse_args()

    verbosity = results.verbosity

    logging_level_name = ['critical', 'error', 'warning', 'info', 'debug', 'subdebug'][min(5, verbosity)]
    can.set_logging_level(logging_level_name)

    reader = LogReader(results.infile)
    in_nosync = MessageSync(reader, timestamps=False, skip=3600)
    print('Can LogReader (Started on {})'.format(datetime.now()))

    conn = sqlite3.connect(results.outfile)
    conn.cursor().execute("""
        CREATE TABLE IF NOT EXISTS messages
        (
          ts REAL,
          arbitration_id INTEGER,
          extended INTEGER,
          remote INTEGER,
          error INTEGER,
          dlc INTEGER,
          data BLOB
        )""")
    conn.commit()

    messages = []
    try:
        for msg in in_nosync:
            if verbosity >= 3:
                print(msg)
            messages.append((
                msg.timestamp,
                msg.arbitration_id,
                msg.is_extended_id,
                msg.is_remote_frame,
                msg.is_error_frame,
                msg.dlc,
                memoryview(msg.data)))
            if len(messages) > 100_000:
                my_logger(conn, messages)
                messages = []
                print(".....")

    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()
        if len(messages) > 0:
            my_logger(conn, messages)
        conn.close()


if __name__ == "__main__":
    main()
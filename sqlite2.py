# coding: utf-8

"""
Implements an SQL database writer and reader for storing CAN messages.

.. note:: The database schema is given in the documentation of the loggers.
"""

from can import SqliteReader


class SqliteReader2(SqliteReader):

    def __init__(self, file, table_name, start_time):
        """
        :param file: a `str` or since Python 3.7 a path like object that points
                     to the database file to use
        :param str table_name: the name of the table to look for the messages
        :param real start_time: time where to start reading
        """
        super().__init__(file, table_name)
        self.start_time = start_time

    def __iter__(self):
        for frame_data in self._cursor.execute(
                "SELECT * FROM {} where ts >= {:f}".format(self.table_name, self.start_time)):
            yield SqliteReader2._assemble_message(frame_data)

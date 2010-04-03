#!/usr/bin/env python

import unittest
import psycopg2
import psycopg2.extensions
import psycopg2.extras
import tests

class ConnectionStub(object):
    """A `connection` wrapper allowing analysis of the `poll()` calls."""
    def __init__(self, conn):
        self.conn = conn
        self.polls = []

    def fileno(self):
        return self.conn.fileno()

    def poll(self):
        rv = self.conn.poll()
        self.polls.append(rv)
        return rv

class GreenTests(unittest.TestCase):
    def connect(self):
        return psycopg2.connect(tests.dsn)

    def setUp(self):
        self._cb = psycopg2.extensions.get_wait_callback()
        psycopg2.extensions.set_wait_callback(psycopg2.extras.wait_select)

    def tearDown(self):
        psycopg2.extensions.set_wait_callback(self._cb)

    def set_stub_wait_callback(self, conn):
        stub = ConnectionStub(conn)
        psycopg2.extensions.set_wait_callback(
            lambda conn: psycopg2.extras.wait_select(stub))
        return stub

    def test_flush_on_write(self):
        # a very large query requires a flush loop to be sent to the backend
        conn = self.connect()
        stub = self.set_stub_wait_callback(conn)
        curs = conn.cursor()
        for mb in 1, 5, 10, 20, 50:
            size = mb * 1024 * 1024
            del stub.polls[:]
            curs.execute("select %s;", ('x' * size,))
            self.assertEqual(size, len(curs.fetchone()[0]))
            if stub.polls.count(psycopg2.extensions.POLL_WRITE) > 1:
                return

        self.fail("sending a large query didn't trigger block on write.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == "__main__":
    unittest.main()
# -*- coding: utf-8 -
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
#
# Copyright 2011 Cloudant, Inc.

import logging
import socket
import time
import sys
import threading
import Queue


log = logging.getLogger(__name__)


class DebugSocket(object):
    def sendall(self, data):
        sys.stdout.write(data)


class CarbonClient(threading.Thread):
    def __init__(self, queue, cfg):
        super(CarbonClient, self).__init__()
        self.setDaemon(True)
        self.ip = cfg.graphite_ip
        self.queue = queue
        self.port = cfg.graphite_port
        self.debug = cfg.debug
        self.max_reconnects = cfg.graphite_max_reconnects
        self.reconnect_delay = cfg.graphite_reconnect_delay
        if self.max_reconnects < 0:
            self.max_reconnects = sys.maxint
        self.connect()

    def run(self):
        while True:
            try:
                stat, value, time = self.queue.get(True, 1)
            except:
                # any queue error, start over
                continue

            mesg = "%s %s %s\n" % (stat, value, time)

            for i in xrange(self.max_reconnects):
                try:
                    if self.sock.sendall(mesg) is None:
                        continue
                except socket.error, err:
                    if i + 1 >= self.max_reconnects:
                        raise
                    log.error("Failed to send data to Carbon server: %s" % err)
                    if self.reconnect():
                        continue

    def connect(self):
        if self.debug:
            log.debug("Connected the debug socket.")
            self.sock = DebugSocket()
            return

        for i in xrange(self.max_reconnects):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.connect((self.ip, self.port))
                log.info("Connected to Carbon at %s:%s" % (self.ip, self.port))
                return True
            except socket.error, e:
                if i + 1 >= self.max_reconnects:
                    raise
                args = (self.ip, self.port, e)
                log.error("Failed to connect to %s:%s: %s" % args)
                if self.reconnect_delay > 0:
                    time.sleep(self.reconnect_delay)

    def reconnect(self):
        self.close()
        self.connect()

    def close(self):
        try:
            self.sock.close()
        except:
            pass

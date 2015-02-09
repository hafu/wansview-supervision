#/bin/env python
import logging
import socket
import threading
from RefreshClientThread import RefreshClientThread


"""
SocketThread Class
"""
class SocketThread(threading.Thread):
    def __init__(self, bind_host, bind_port, db_helper, config):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.s      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.db     = db_helper
        self.config = config

        self.logger.debug('Binding to %s:%i' % (bind_host, bind_port))
        self.s.bind((bind_host, bind_port))
        self.s.listen(0)
        
        self.cs         = None
        self.running    = True
        self.rct        = RefreshClientThread(self.db, self.config)

    def run(self):
        self.rct.start()
        frontend_users = 0
        self.accept()
        while self.running:
            if self.cs:
                data = self.cs.recv(128)
                if len(data) == 0:
                    self.logger.warn('Data len is 0, closing client connection')
                    self.close_cs()
                    self.accept()
                else:
                    self.logger.debug('Got data: %s, len: %i' % (data, len(data)))
                    if data. startswith('users:') and int(data.split(':')[1]) >= 1:
                        self.logger.info('Start client')
                        self.rct.check(self.cs)
                    else:
                        self.logger.info('pause client')
                        self.rct.pause()
                    # -> start Refresh client if clients >= 1
                    # maybe another thread here


    def accept(self):
        if self.running:
            (self.cs, ca) = self.s.accept()
            self.logger.debug('Got connection from %s' % str(ca))

    def close_cs(self):
        if self.cs:
            self.logger.debug('Closing client connection')
            self.cs.shutdown(socket.SHUT_RDWR)
            self.cs.close()
            self.cs = None

    def send(self, data):
        self.logger.debug('send()');
        if self.cs:
            try:
                self.logger.debug('Sending data: ' + str(data))
                self.cs.sendall(data)
            except socket.error as e:
                self.logger.error('Lost connection: ' + str(e))
                self.close_cs()
                self.accept()

    def stop(self):
        self.running = False
        self.rct.stop()
        self.close_cs()
        self.logger.debug('Closing socket')
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

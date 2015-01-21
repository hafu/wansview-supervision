#/bin/env python
import logging
import socket
import threading

"""
SocketThread Class
"""
class SocketThread(threading.Thread):
    def __init__(self, bind_host, bind_port):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.s      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.logger.debug('Binding to %s:%i' % (bind_host, bind_port))
        self.s.bind((bind_host, bind_port))
        self.s.listen(True)

        self.con    = None
        self.addr   = None
        self.stop   = False

    def run(self):
        if not self.stop:
            self.con, self.addr = self.s.accept()

    def send(self, data):
        if self.con is not None:
            try:
                self.logger.debug('Sending data')
                self.con.sendall(data)
            except socket.error as e:
                self.logger.error('Lost connection')
                self.con.close()
                if self.s is not None or not self.stop:
                    self.logger.debug('Allowing new connection')
                    self.con, self.addr = self.s.accept()

    def close(self):
        self.con.close()
    
    def stop(self):
        self.stop = True
        self.logger.info('Closing socket')
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

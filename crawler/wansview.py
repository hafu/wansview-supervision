#!/bin/env python
import ConfigParser
import argparse
import threading
import logging
import time
import Queue
import random
import sys
import signal
import os
import json
import base64

from lib.DBHelper import DBHelper
from lib.WansViewClient import WansViewClient
from lib.SocketThread import SocketThread

"""
QueueThread Class
"""
class QueueThread(threading.Thread):
    def __init__(self, config):
        threading.Thread.__init__(self)
        self.logger     = logging.getLogger(self.__class__.__name__)
        self.config     = config
        self.q          = Queue.Queue(int(self.config.get('daemon', 'queue_size_max')))
        # using own db helper ...
        self.db_helper  = DBHelper(self.config)
        self.running    = True

    def run(self):
        while self.running:
            if (self.q.qsize() < int(self.config.get('daemon', 'queue_size_min'))):
                    self.logger.debug('Queue is getting empty %i' % self.q.qsize())
                    unchecked_hosts = self.db_helper.get_unchecked_host_count()
                    #TODO maybe in firs if block
                    if (unchecked_hosts > 0):
                        items_to_get = int(self.config.get('daemon', 'queue_size_max')) - self.q.qsize()
                        self.logger.debug('Getting %i items from db' % items_to_get)
                        for item in self.db_helper.get_unchecked_hosts(items_to_get):
                            self.q.put(item)
            time.sleep(1)
        self.logger.info('Exiting Queue Thread')

    def get_queue(self):
        return self.q

    def get_item(self):
        return self.q.get()

    def full(self):
        return self.q.full()

    def is_minimum_full(self):
        if self.q.qsize() >= int(self.cconfi.get('daemon', 'queue_size_min')):
            return True
        return False

    def done(self):
        self.q.task_done()

    def stop(self):
        self.logger.debug('Stopping queue Thread')
        self.running = False
        while not q.empty():
            item = self.q.get()
            self.logger.debug('Removing item')
            self.q.task_done()
        self.logger('Joining Queue')
        self.q.join()


"""
QorkerThread Class
"""
class WorkerThread(threading.Thread):
    def __init__(self, config, queue_thread, db_helper):
        threading.Thread.__init__(self)
        self.logger     = logging.getLogger(self.__class__.__name__)
        self.running    = True
        self.q_thread   = queue_thread
        self.db_helper  = db_helper
        self.config     = config

    def run(self):
        while self.running:
            time.sleep(random.uniform(0.5, int(self.config.get('daemon', 'worker_threads'))))
            item = self.q_thread.get_item()
            self.logger.debug('Starting WansViewClient')
            # this one is blocking ...
            wvc = WansViewClient(self.config, self.db_helper, item[0])
            result = wvc.run()
            self.logger.debug('Got a result from WansViewClient')
            
            # update status
            if result['status'] is not None:
                self.logger.info('Saving status %s for host %s' % (result['status'], item[0]))
                self.db_helper.update_status(item[0], result['status'])
            else:
                self.logger.error('Status is None for host %s' % item[0])

            # save image
            if result['auth_data'] is not None and result['image'] is not None:
                self.logger.info('Saving image for host %s in country %s' % (item[0],  result['country']))
                self.db_helper.save_image(item[0], result['auth_data'][0], result['auth_data'][1], result['image'], result['country'])
            elif not (result['auth_data'] is None and result['image'] is None):
                self.logger.error('Something is wrong, auth_data: %s, image: %s for host %s' % (str(result['auth_data']), str(result['image']), item[0]))
            #else:
            #    self.logger.error('Something went wrong! Dumping result:\n %s' % str(result))

            self.q_thread.done()


        self.logger.info('Exiting worker Thread')

    def stop(self):
        self.logger.debug('Stopping worker Thread')
        self.running = False




if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '-c', 
            '--config', 
            dest='config', 
            action='store', 
            required=True, 
            help='Configuration File'
            )
    parser.add_argument(
            '-d', 
            '--daemon', 
            dest='daemon', 
            action='store_true', 
            help='Daemonize'
            )
    args = parser.parse_args()

    # ConfigParser
    config = ConfigParser.RawConfigParser()
    config.read(args.config)

    # setup logging: debug, info, warn, error
    log_level = config.get('logging', 'level').lower()
    if log_level.startswith('d'):
        log_level = logging.DEBUG
    elif log_level.startswith('i'):
        log_level = logging.INFO
    elif log_level.startswith('w'):
        log_level = logging.WARNING
    elif log_level.startswith('e'):
        log_level = logging.ERROR
    else:
        log_level = logging.WARNING

    if args.daemon:
        # damonzie
        logging.basicConfig(
                filename=config.get('logging', 'file'), 
                format='%(asctime)s %(levelname)-7s %(threadName)-15s %(name)-22s %(message)s', 
                level=log_level
                )
    else:
        logging.basicConfig(
                format='%(asctime)s %(levelname)-7s %(threadName)-15s %(name)-22s %(message)s', 
                level=log_level
                )


    # db helper ...
    db_helper = DBHelper(config)

    logging.info('Starting QueueThread')
    q_thread = QueueThread(config)
    q_thread.start()

    logging.info('Waiting for queue to be filled')
    while not q_thread.is_minimum_full():
        time.sleep(1)


    
    workers = []
    logging.info('Starting WorkerThreads')
    for i in range(int(config.get('daemon', 'worker_threads'))):
        t = WorkerThread(config, q_thread, db_helper)
        t.start()
        workers.append(t)
    logging.info('WorkerThreads started')

    logging.info('Setup signals')
    def exit_gracefully(signum, frame):
        global q_thread
        global workers
        logging.info('Try to exit ...')
        logging.debug('Stopping WorkerThreads ... this can take some time')
        for w in workers:
            w.stop()
            w.join()
        logging.debug('All WorkerThreads should be stopped')
        logging.debug('Stopping QueueThread')
        q_thread.stop()
        q_thread.join()

    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, exit_gracefully)

    logging.info('Setup done')


    

"""
    with open(cfg.get('daemon', 'pid'), 'w') as fp:
        fp.write(str(os.getpid()))
        fp.close()

    running = True
    main_thread = threading.currentThread()

    def exit_gracefully(signum, frame):
        global running
        running = False
        logging.info('Try to exit ...')
        #st.stop()
        for t in threading.enumerate():
            if t is not main_thread:
                logging.debug('Waiting for Thread: %s' % t.name)
                t.join()

        while not q.empty():
            item = q.get()
            logging.debug('%s removed' % item[0])
            #q.task_done()
        #while q.qsize() > 0 and threading.activeCount() >= (int(cfg.get('daemon', 'queue_size')) + int(cfg.get('daemon', 'worker_threads')) + 1):
        #    logging.debug('Waiting for Threads to exit: %i' % threading.activeCount())
        #    logging.debug('Empty Queue .. Queue size: %i' % q.qsize())
        #    time.sleep(1)
        #while threading.activeCount() >= (int(cfg.get('daemon', 'queue_size')) + int(cfg.get('daemon', 'worker_threads')) + 1):
        #    logging.debug('Waiting for Threads to exit: %i' % threading.activeCount())
        #    time.sleep(1)
        try:
            os.remove(cfg.get('daemon', 'pid'))
        except OSError as e:
            logging.error('PID already deleted: %s' % e)
        #sys.exit(0)

    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
        signal.signal(sig, exit_gracefully)

    # Test
    # Create DB Class
    def worker(db_helper):
        #global running
        # TODO (queue?)
        while running:
            #time.sleep(random.uniform(0.5, int(cfg.get('daemon', 'worker_threads'))))
            item = q.get()
            wvc = WansViewClient(config, db_helper, item[0])
            result = wvc.run()
            if result['status'] is not None:
                logging.info('Saving status %s for host %s' % (result['status'], item[0]))
                db_helper.update_status(item[0], result['status'])
            else:
                logging.error('Status is None for host %s' % item[0])
            
            if result['auth_data'] is not None and result['image'] is not None:
                logging.info('Saving image')
                logging.info('Country: %s' % result['country'])
                db_helper.save_image(item[0], result['auth_data'][0], result['auth_data'][1], result['image'], result['country'])
                #st.send(json.dumps({newImage: base64.b64encode(result['image'])}))
            elif not (result['auth_data'] is None and result['image'] is None):
                logging.error('Something is wrong, auth_data: %s, image: %s for host %s' % (str(result['auth_data']), str(result['image']), item[0]))
                
            q.task_done()
            #while threading.activeCount() >= (int(cfg.get('daemon', 'queue_size')) * 2) + 1:
            #while threading.activeCount() >= (int(cfg.get('daemon', 'queue_size')) + int(cfg.get('daemon', 'worker_threads')) + 1):
            #    logging.debug('Active Threads: %i' % threading.activeCount())
            #    time.sleep(5)
        logging.info('Exiting worker')

    db_helper = DBHelper(config)
    q = Queue.Queue(int(cfg.get('daemon', 'queue_size')))

    #st = SocketThread(cfg.get('socket', 'lhost'), int(cfg.get('socket', 'lport')))
    #st.start()
    
    for i in range(int(cfg.get('daemon', 'worker_threads'))):
        t = threading.Thread(target=worker, name='WorkerThread-%i' % i, args=(db_helper,))
        t.daemon = True
        t.start()

    while db_helper.get_unchecked_host_count() > 0 and running:
        for item in db_helper.get_unchecked_hosts(int(cfg.get('daemon', 'queue_size'))):
            logging.debug('Putting new Item in Queue')
            #print 'Host: %s' % item
            #time.sleep(random.uniform(0.5,3))
            if running:
                q.put(item)
        while q.full() and running:
            logging.debug('Queue is full, waiting ...')
            time.sleep(random.uniform(0.5,3))
        logging.debug('Running: ' + str(running))
    
    # no more hosts to check
    running = False

    #logging.debug('Joining queue')
    logging.debug('Que size: %i' % q.qsize())
    #q.join()
    logging.debug('Closing db connection')
    db_helper.close()
    logging.info('Exit')
"""
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

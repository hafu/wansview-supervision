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
    cfg = config = ConfigParser.RawConfigParser()
    cfg.read(args.config)

    # setup logging: debug, info, warn, error
    log_level = cfg.get('logging', 'level').lower()
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
                filename=cfg.get('logging', 'file'), 
                format='%(asctime)s %(levelname)-7s %(threadName)-15s %(name)-22s %(message)s', 
                level=log_level
                )
    else:
        logging.basicConfig(
                format='%(asctime)s %(levelname)-7s %(threadName)-15s %(name)-22s %(message)s', 
                level=log_level
                )


    with open(cfg.get('daemon', 'pid'), 'w') as fp:
        fp.write(str(os.getpid()))
        fp.close()

    running = True
    main_thread = threading.currentThread()

    def exit_gracefully(signum, frame):
        global running
        running = False
        logging.info('Try to exit ...')
        st.stop()
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
            item = q.get()
            time.sleep(random.uniform(0.5, int(cfg.get('daemon', 'worker_threads'))))
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
                st.send(json.dumps({newImage: base64.b64encode(result['image'])}))
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

    st = SocketThread(cfg.get('socket', 'lhost'), int(cfg.get('socket', 'lport')))
    st.start()
    
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

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

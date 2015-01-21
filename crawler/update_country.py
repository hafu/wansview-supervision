#!/bin/env python
import ConfigParser
import argparse
import logging
import pgdb
import GeoIP

from lib.DBHelper import DBHelper
from lib.HTTPClient import HTTPClient


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
    args = parser.parse_args()

    # ConfigParser
    cfg = config = ConfigParser.RawConfigParser()
    cfg.read(args.config)

    logging.basicConfig(
       format='%(asctime)s %(levelname)-7s %(threadName)-15s %(name)-22s %(message)s',
       level=logging.DEBUG
       )


    db_helper = DBHelper(config)

    pg_con = pgdb.connect(
            dsn=config.get('pgsql', 'host') + ':' + config.get('pgsql', 'db'),
            user=config.get('pgsql', 'user'),
            password=config.get('pgsql', 'pass')
            )
    pg_cur = pg_con.cursor()
    pg_cur.execute("SELECT hostname, country FROM ip_cam_images WHERE country = 'Unknown'")
    
    http_client = HTTPClient(config)
    gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)

    for result in pg_cur.fetchall():
        logging.debug('Get country for %s' % result[0])
        http_client.set_ua(db_helper.get_random_ua())
        http_client.set_url('http://' +  result[0] + '/')
        res = http_client.openurl()
        if http_client.get_r_code() == 200 and res.read() == 'OFFLINE':
            logging.debug('Host %s is offline' % result[0])
        elif http_client.get_r_code() == 503:
            logging.debug('Host %s is not reachable' % result[0])
        else:
            ip = http_client.get_ip()
            logging.debug('IP of %s is %s' % (result[0], ip))
            if ip is not None:
                c = gi.country_name_by_addr(ip)
                logging.debug('Country is %s' % c)
                if c is not 'Unknown':
                    logging.info('Updating: %s, ip: %s, country: %s' % (result[0], ip, c))
                    pg_cur.execute("UPDATE ip_cam_images SET country = '%s' WHERE hostname = '%s'" % (c, result[0]))
                    pg_con.commit()

    pg_cur.close()
    pg_con.close()

            


    
    
    



# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#/bin/env python
import logging
import pgdb
import threading

"""
DBHelper Class
"""
class DBHelper():
    def __init__(self, config):
        self.lock   = threading.Lock()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.lock.acquire()
        self.con    = pgdb.connect(
                dsn=config.get('pgsql', 'host') + ':' + config.get('pgsql', 'db'), 
                user=config.get('pgsql', 'user'), 
                password=config.get('pgsql', 'pass')
                )
        self.cur    = self.con.cursor()
        self.lock.release()

    def get_random_ua(self):
        self.lock.acquire()
        self.logger.debug('get_random_ua()')
        self.cur.execute("SELECT ua FROM uas ORDER BY RANDOM() LIMIT 1")
        r = self.cur.fetchone()[0]
        self.logger.debug('get_random_ua() done')
        self.lock.release()
        return r

    def get_credentials(self):
        self.lock.acquire()
        self.logger.debug('get_credentials()')
        self.cur.execute("""SELECT
                                u.username,
                                u.priority as uprio,
                                p.password,
                                p.priority as pprio, 
                                u.priority + p.priority as prio 
                            FROM 
                                usernames u, 
                                passwords p 
                            ORDER BY prio, RANDOM()""")
        r = self.cur.fetchall()
        self.logger.debug('get_credentials() done')
        self.lock.release()
        return r
    
    
    def update_status(self, host, status):
        self.lock.acquire()
        self.logger.debug('update_status(%s, %s)' % (host, status))
        self.cur.execute("""UPDATE 
                                ip_cam_hosts 
                            SET 
                                status = '%s', 
                                updated = NOW() 
                            WHERE 
                                hostname = '%s'""" % (status, host))
        self.con.commit()
        self.logger.debug('update_status(%s, %s) done' % (host, status))
        self.lock.release()

    def save_image(self, host, username, password, image_data, country):
        self.lock.acquire()
        self.logger.debug('save_image(%s, %s, %s, ..., %s)' % (host, username, password, country))
        self.cur.execute("""SELECT 
                                count(hostname) 
                            FROM 
                                ip_cam_images 
                            WHERE 
                                hostname = '%s'""" % host)
        if int(self.cur.fetchone()[0]) == 0:
            self.cur.execute("""INSERT INTO 
                                    ip_cam_images (hostname, username, password, image, country) 
                                VALUES 
                                    ('%s', '%s', '%s', '%s', '%s')""" % (host, username, password, pgdb.escape_bytea(image_data), country))
        else:
            self.cur.execute("""UPDATE
                                    ip_cam_images
                                SET
                                    username = '%s',
                                    password = '%s',
                                    image = '%s',
                                    country = '%s'
                                WHERE
                                    hostname = '%s'""" % (username, password, pgdb.escape_bytea(image_data), country, host))

        self.cur.execute("""UPDATE 
                                ip_cam_hosts 
                            SET 
                                updated = NOW() 
                            WHERE 
                                hostname = '%s'""" % host)
        self.con.commit()
        self.logger.debug('save_image(%s, %s, %s, ..., %s) done' % (host, username, password, country))
        self.lock.release()


    def get_unchecked_hosts(self, count):
        self.lock.acquire()
        self.logger.debug('get_unchecked_hosts(%i)' % count)
        self.logger.debug('get_unchecked_hosts(...) -> execute(...)')
        self.cur.execute("""SELECT 
                                hostname 
                            FROM 
                                ip_cam_hosts 
                            WHERE 
                                status = 'unchecked' 
                            ORDER BY RANDOM() LIMIT %i""" % count)
        self.logger.debug('get_unchecked_hosts(...) -> fetchall(...)')
        r = self.cur.fetchall()
        self.logger.debug('get_unchecked_hosts(%i) done' % count)
        self.lock.release()
        return r

    def get_unchecked_host_count(self):
        self.lock.acquire()
        self.logger.debug('get_unchecked_host_count()')
        self.cur.execute("SELECT count(*) FROM ip_cam_hosts WHERE status = 'unchecked'")
        r = self.cur.fetchone()[0]
        self.logger.debug('get_unchecked_host_count() done')
        self.lock.release()
        return r

    def close(self):
        self.cur.close()
        self.con.close()
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

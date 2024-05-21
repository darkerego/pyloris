# pyloris
A Denial of Service Tool Written in Python


ddos
====

DDOS tool in python.

=============== usage =============

usage: python attack.py [-t] [-c] http://www.baidu.com/

positional arguments:
  host                  The schema and target ip or hostname, ie "https://example.com"

options:
  -h, --help            show this help message and exit
  -t TIME, --time TIME  Time to run this attack in seconds. Defaults to 10 minutes or 600 seconds.
  -c CONCURRENCY, --concurrency CONCURRENCY
                        How many threads to run at once. Uses Semaphore. Defaults to 100.
  -r REQUEST_COUNT, --request-count REQUEST_COUNT
                        The total number of requests to send.
  -v, --verbosity       Output verbosity.


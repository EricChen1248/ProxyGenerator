#%%
import requests
from bs4 import BeautifulSoup
from time import sleep
import threading
import re

class ProxyGenerator():
    def __init__(self, testing_link = "https://www.sslproxies.org"):
        super().__init__()
        self.link = testing_link
        self.prog = re.compile(r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]):[0-9]+$')
        self.proxy_thread = None
        self.timer_thread = None
        self.proxy_lst = []
        self.success = []
        self.lock = threading.Lock()
        self.thread_lock = threading.Lock()
        self._get_new_proxies()
        self.error_rate = {}
        self.crawl_threads = []

    def _proxy_generator(self):
        soup = BeautifulSoup(requests.get("https://sslproxies.org/").content, 'lxml')
        proxy_list = list(map(lambda x:x[0]+':'+x[1], list(zip(map(lambda x:x.text, 
        soup.findAll('td')[::8]), map(lambda x:x.text, soup.findAll('td')[1::8])))))
        return [p for p in proxy_list if self.prog.match(p) is not None]


    def _job(self, proxy):
        ''' Try to send a request. On any error, does nothing, on success adds to proxy list '''
        try:
            requests.get(self.link, proxies={'https':proxy, 'http':proxy}, headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0'}, timeout=20)
        except:
            return

        self.success.append(proxy)

    def _get_new_proxies(self, renew = False):
        '''
            Get new proxies and adds to original list.
            - renew: On true, completely replaces original list
        ''' 
        self.proxy_thread = threading.Thread(target = self._get_new_proxies_helper, args =[renew])
        self.proxy_thread.start()

    def _get_new_proxies_helper(self, renew = False):
        ts = []
        self.sucess = []
        for proxy in self._proxy_generator() + self.__proxy_scrape_https() + self.__proxy_scrape_socks():
            t = threading.Thread(target= self._job, args=[proxy])
            t.start()
            ts.append(t)

        for t in ts:
            t.join()

        self.lock.acquire()
        if renew:
            self.proxy_lst = self.success
        else:
            self.proxy_lst = [p for p in set(self.proxy_lst + self.success)]

        self.error_rate = {}

        self.lock.release()

        self.timer_thread = threading.Thread(target = self._sleep_thread, daemon=True, name="ProxyGeneratorSleep")
        self.timer_thread.start()


    def _sleep_thread(self):
        ''' Sleeps for 60 minutes, and forces renew of proxies '''
        thread = self.timer_thread
        for _ in range(20):
            sleep(60)
            if thread != self.timer_thread:
                return

        self._get_new_proxies(renew = True)

    def GetProxy(self) -> str:
        self.thread_lock.acquire()
        if len(self.proxy_lst) == 0:
            print('Waiting for new proxies')
            self.proxy_thread.join()
            print(f'Total proxies: {len(self.proxy_lst)}')
        self.thread_lock.release()

        self.lock.acquire()
        proxy = self.proxy_lst.pop(0)
        self.proxy_lst.append(proxy)
        self.lock.release()

        return proxy

    def RemoveProxy(self, proxy):
        self.lock.acquire()
        try:
            self.proxy_lst.remove(proxy)
        except ValueError:
            pass
        self.error_rate[proxy] = 0
        self.lock.release()
        if len(self.proxy_lst) < 20:
            self._get_new_proxies()

    def ErrorProxy(self, proxy):
        self.lock.acquire()
        self.error_rate[proxy] = self.error_rate.get(proxy, 0) + 1
        self.lock.release()
        if (self.error_rate[proxy] > 30):
            self.RemoveProxy(proxy)

    def count(self):
        return len(self.proxy_lst)

    def __proxy_scrape_https(self):
        return requests.get('https://api.proxyscrape.com/?request=getproxies&proxytype=http&timeout=10000&country=all&ssl=all&anonymity=all').text.split('\r\n')

    def __proxy_scrape_socks(self):
        return ['socks5://' + r for r in requests.get('https://api.proxyscrape.com/?request=getproxies&proxytype=socks5&timeout=10000&country=all').text.split('\r\n')]

    def HandleErrors(self, error, proxy) -> str:
        try:
            raise error
        except requests.exceptions.ConnectTimeout:
            self.ErrorProxy(proxy)
            return f"ConnectTimeout with {proxy}"
        except requests.exceptions.ProxyError:
            self.RemoveProxy(proxy)
            return f"ProxyError with {proxy}"
        except requests.exceptions.ConnectionError:
            self.ErrorProxy(proxy)
            return f"ConnectionError with {proxy}"
        except requests.exceptions.ReadTimeout:
            self.RemoveProxy(proxy)
            return f"ReadTimeout with {proxy}"
        except Exception as error:
            raise error


    def CrawlThread(self, target = None, args=[]):
        t = threading.Thread(target=target, args=args)
        t.start()
        self.crawl_threads.append(t)

        while (len(self.crawl_threads) >= len(self.proxy_lst)):
            t = threading.Thread(target=self.__wait_thread)
            t.start()
            t.join()

    def WaitAllCrawl(self):
        while (len(self.crawl_threads) > 0):
            t = threading.Thread(target=self.__wait_thread)
            t.start()
            t.join()

    def __wait_thread(self):
        for t in self.crawl_threads:
            if not t.isAlive():
                self.crawl_threads.remove(t)
                return



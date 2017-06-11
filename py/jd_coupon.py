# -*- coding: utf-8 -*-

"""
JD online coupon helper tool
-----------------------------------------------------

only support to login by QR code, 

"""


import bs4
import requests
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()
import os
import time
import json
import random
import logging
import argparse
import multiprocessing
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# get function name
FuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name

def get_current_time():
    try:
        response = requests.get('http://www.jd.com')
        date = response.headers['date']
        ltime=time.strptime(date[5:25], "%d %b %Y %H:%M:%S")
        ttime=time.localtime(time.mktime(ltime)+ 8* 60* 60) 
        return ttime
    except Exception, e:
        logging.info('Exp {0} : {1}'.format(FuncName(), e))
        return None


def tags_val(tag, key='', index=0):
    '''
    return html tag list attribute @key @index
    if @key is empty, return tag content
    '''
    if len(tag) == 0 or len(tag) <= index:
        return ''
    elif key:
        txt = tag[index].get(key)
        return txt.strip(' \t\r\n') if txt else ''
    else:
        txt = tag[index].text
        return txt.strip(' \t\r\n') if txt else ''


def tag_val(tag, key=''):
    '''
    return html tag attribute @key
    if @key is empty, return tag content
    '''
    if tag is None: 
        return ''
    elif key:
        txt = tag.get(key)
        return txt.strip(' \t\r\n') if txt else ''
    else:
        txt = tag.text
        return txt.strip(' \t\r\n') if txt else ''


class JDWrapper(object):
    '''
    This class used to simulate login JD
    '''
    
    def __init__(self, usr_name=None, usr_pwd=None):
        # cookie info
        self.trackid = ''
        self.uuid = ''
        self.eid = ''
        self.fp = ''

        self.usr_name = usr_name
        self.usr_pwd = usr_pwd

        self.interval = 0

        # init url related
        self.home = 'https://passport.jd.com/new/login.aspx'
        self.login = 'https://passport.jd.com/uc/loginService'
        self.imag = 'https://authcode.jd.com/verify/image'
        self.auth = 'https://passport.jd.com/uc/showAuthCode'
        
        self.sess = requests.Session()

        self.headers = {
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
            'ContentType': 'text/html; charset=utf-8',
            'Accept-Encoding':'gzip, deflate, sdch',
            'Accept-Language':'zh-CN,zh;q=0.8',
            'Connection' : 'keep-alive',
        }
        
        self.cookies = {

        }

    @staticmethod
    def print_json(resp_text):
        '''
        format the response content
        '''
        if resp_text[0] == '(':
            resp_text = resp_text[1:-1]
        
        for k,v in json.loads(resp_text).items():
            logging.info(u'%s : %s' % (k, v))

    @staticmethod
    def response_status(resp):
        if resp.status_code != requests.codes.OK:
            logging.info('Status: %u, Url: %s' % (resp.status_code, resp.url))
            return False
        return True

    def login_by_QR(self):
        # jd login by QR code
        try:
            logging.info('+++++++++++++++++++++++++++++++++++++++++++++++++++++++')
            logging.info(u'{0} > 请打开京东手机客户端，准备扫码登陆:'.format(time.ctime()))

            urls = (
                'https://passport.jd.com/new/login.aspx',
                'https://qr.m.jd.com/show',
                'https://qr.m.jd.com/check',
                'https://passport.jd.com/uc/qrCodeTicketValidation'
            )

            # step 1: open login page
            resp = self.sess.get(
                urls[0], 
                headers = self.headers
            )
            if resp.status_code != requests.codes.OK:
                logging.info(u'获取登录页失败: %u' % resp.status_code)
                return False

            ## save cookies
            for k, v in resp.cookies.items():
                self.cookies[k] = v
            

            # step 2: get QR image
            resp = self.sess.get(
                urls[1], 
                headers = self.headers,
                cookies = self.cookies,
                params = {
                    'appid': 133,
                    'size': 147,
                    't': (long)(time.time() * 1000)
                }
            )
            if resp.status_code != requests.codes.OK:
                logging.info(u'获取二维码失败: %u' % resp.status_code)
                return False

            ## save cookies
            for k, v in resp.cookies.items():
                self.cookies[k] = v

            ## save QR code
            image_file = 'qr.png'
            with open (image_file, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    f.write(chunk)
            
            ## scan QR code with phone
            os.system('explorer ' + image_file)

            # step 3： check scan result
            ## mush have
            self.headers['Host'] = 'qr.m.jd.com' 
            self.headers['Referer'] = 'https://passport.jd.com/new/login.aspx'

            # check if QR code scanned
            qr_ticket = None
            retry_times = 100
            while retry_times:
                retry_times -= 1
                resp = self.sess.get(
                    urls[2],
                    headers = self.headers,
                    cookies = self.cookies,
                    params = {
                        'callback': 'jQuery%u' % random.randint(100000, 999999),
                        'appid': 133,
                        'token': self.cookies['wlfstk_smdl'],
                        '_': (long)(time.time() * 1000)
                    }
                )

                if resp.status_code != requests.codes.OK:
                    continue

                n1 = resp.text.find('(')
                n2 = resp.text.find(')')
                rs = json.loads(resp.text[n1+1:n2])

                if rs['code'] == 200:
                    logging.info(u'{} : {}'.format(rs['code'], rs['ticket']))
                    qr_ticket = rs['ticket']
                    break
                else:
                    logging.info(u'{} : {}'.format(rs['code'], rs['msg']))
                    time.sleep(3)
            
            if not qr_ticket:
                logging.info(u'二维码登陆失败')
                return False
            
            # step 4: validate scan result
            ## must have
            self.headers['Host'] = 'passport.jd.com'
            self.headers['Referer'] = 'https://passport.jd.com/uc/login?ltype=logout'
            resp = self.sess.get(
                urls[3], 
                headers = self.headers,
                cookies = self.cookies,
                params = {'t' : qr_ticket },
            )
            if resp.status_code != requests.codes.OK:
                logging.info(u'二维码登陆校验失败: %u' % resp.status_code)
                return False
            
            ## login succeed
            self.headers['P3P'] = resp.headers.get('P3P')
            for k, v in resp.cookies.items():
                self.cookies[k] = v
            
            logging.info(u'登陆成功')
            return True
        
        except Exception as e:
            logging.info('Exp:', e)
            raise

        return False

    def click(self, url, verbose):
        try:
            resp = self.sess.get(url)
            if verbose != 0:
                soup = bs4.BeautifulSoup(resp.text, "html.parser")
                tags = soup.select('div.content')
                logging.info(u'{}'.format(tags[0].text.strip('\n')))
            if resp.status_code != requests.codes.OK:
                return 0
            return 1
        except Exception, e:
            if verbose != 0:
                logging.info('Exp {0} : {1}'.format(FuncName(), e))
            return 0

def click_thread(jd, url, target, id):    
    cnt = 0
    logging.info(u'进程{}:开始运行'.format(id+1))
    while(time.time() < target):
        cnt = cnt + jd.click(url, 0)
    jd.click(url, 1)
    return cnt

def main(options):
    step = 1
    jd = JDWrapper()
    if not jd.login_by_QR():
        return
    pool = multiprocessing.Pool(processes=options.process+1)
    result = []
    target = (options.hour * 3600) + (options.minute * 60)
    jd.click(options.url, 1)
    for i in range(3):
        ttime = get_current_time()
        stime = time.time()
        if (ttime != None):
            break;
    if ttime == None:
        logging.info(u'获取时间失败')
        return
    current = (ttime.tm_hour * 3600) + (ttime.tm_min * 60) + ttime.tm_sec
    delta = int(current - stime)
    logging.info(u'系统时间差为{}秒'.format(delta))
    if (target < current):
        target = current
    while 1:
        tick = time.time()
        verbose = 0
        if ((int(tick) % 10) == 0):
            verbose = 1
        jd.click(options.url, verbose)
        if (tick + delta + 60) >= target:
            break;
        time.sleep(step)
    current = time.time() + delta
    m, s = divmod(current, 60)
    h, m = divmod(m, 60)
    logging.info(u'#开始时间 {:0>2}:{:0>2}:{:0>2} #目标时间 {:0>2}:{:0>2}:{:0>2}'.format(int(h), int(m), int(s), options.hour, options.minute, 0))
    jd.click(options.url, 1)
    deadline = time.time() + (options.duration * 60)
    for i in range(options.process):
        result.append(pool.apply_async(click_thread, args=(jd, options.url, deadline, i,)))
    pool.close()
    pool.join()
    cnt = 0
    for res in result:
        cnt += res.get()
    logging.info(u'运行{}分钟，点击{}次'.format(options.duration, cnt))

if __name__ == '__main__':
    # help message
    parser = argparse.ArgumentParser(description='Simulate to login Jing Dong, and click coupon')
    parser.add_argument('-u', '--url', 
                        help='Coupon URL', required=True)
    parser.add_argument('-hh', '--hour', 
                        type=int, help='Target hour', default=10)
    parser.add_argument('-m', '--minute', 
                        type=int, help='Target minute', default=0)
    parser.add_argument('-d', '--duration', 
                        type=int, help='Duration in minutes', default=24*60)
    parser.add_argument('-p', '--process', 
                        type=int, help='Number of processes', default=1)
    parser.add_argument('-l', '--log', 
                        help='Log file', default=None)

    options = parser.parse_args()
    if (options.log != None):
        logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s', datefmt='%H:%M:%S', filename=options.log, filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    main(options)


#!/usr/bin/env python
# -*- coding:utf-8 -*-
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from requests.utils import cookiejar_from_dict
import lxml
import json
import os
import time
from optparse import OptionParser


def log(text):
    s = '[%s] %s' % (str(datetime.now()), text)
    open('clean_tieba.log', 'a').write(s + '\n')
    print('[%s] %s' % (str(datetime.now()), text))

class Tieba:
    user_id = -1
    username = ''
    match = '.*'
    r = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'http://tieba.baidu.com/',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'http://tieba.baidu.com',
    }

    def error_check(self, text):
        log(text)
        try:
            _ = json.loads(text)
            if _['err_code'] == 0:
                log('Success')
                return True
            elif _['err_code'] == 220034:
                log('Failed: 您的操作太频繁了')
                return 'exit'
            elif _['err_code'] == 260005:
                log('Failed: Cookies失效')
                return False
            elif _['err_code'] == 230308:
                log('Failed: 据说tbs不对')
                return False
            else:
                log('Failed: 不造啥错误')
                return False

        except json.decoder.JSONDecodeError:
            return False

    def get_tie(self):
        tie_list = []
        page = 1
        while(1):
            url = 'https://tieba.baidu.com/i/%s/my_tie?&pn=%d' % (self.user_id, page)
            log('-->%s' % url)
            _ = self.r.get(url, headers=self.headers)
            my_tie = BeautifulSoup(_.text, 'lxml').select('.simple_block_container')[0].ul
            lis = my_tie.select('li')
            if len(lis) == 0:
                break
            for li in lis:
                a = li.select('a')
                bar_name = a[0].text
                bar_url = 'https://tieba.baidu.com' + a[0]['href']
                tie_name = a[1].text
                tie_url = 'https://tieba.baidu.com' + a[1]['href']
                new_tie = {
                    'bar_name': bar_name,
                    'bar_url': bar_url,
                    'tie_name': tie_name,
                    'tie_url': tie_url
                }
                log('add new tie: [%s][%s]' % (bar_name, tie_name))
                tie_list.append(new_tie)
            page += 1
        return tie_list
        # print(json.dumps(tie_list, ensure_ascii=False, indent=4))

    def get_reply(self):
        reply_list = []
        page = 1
        while(1):
            url = 'https://tieba.baidu.com/i/%s/my_reply?&pn=%d' % (self.user_id, page)
            log('-->%s' % (url))
            _ = self.r.get(url, headers=self.headers)
            my_reply = BeautifulSoup(_.text, 'lxml').select('.t_forward')
            if len(my_reply) == 0:
                break
            # print(my_reply)
            for one in my_reply:
                try:
                    reply_content = one.select('.for_reply_context')[0].text
                    reply_url = 'https://tieba.baidu.com' + one.select('.for_reply_context')[0]['href']
                except IndexError:
                    reply_content = ''
                    reply_url = 'https://tieba.baidu.com' + one.select('.b_reply')[0]['href']
                tie_name = one.select('.thread_title')[0].text
                tie_url = 'https://tieba.baidu.com' + one.select('.thread_title')[0]['href']
                bar = one.select('.common_source_main')[0].select('a')[-1]
                bar_name = bar.text
                bar_url = 'https://tieba.baidu.com' + bar['href']
                new_reply = {
                    'reply_content': reply_content,
                    'reply_url': reply_url,
                    'tie_name': tie_name,
                    'tie_url': tie_url,
                    'bar_name': bar_name,
                    'bar_url': bar_url,
                }
                if re.match(self.match, reply_content):
                    log('add new reply: [%s][%s]' % (reply_content, tie_name))
                    reply_list.append(new_reply)
                else:
                    log('NOT match, pass: [%s][%s]' % (reply_content, tie_name))
            page += 1
        return reply_list
        # print(json.dumps(reply_list, ensure_ascii=False, indent=4))

    def del_tie(self, reply):
        log(json.dumps(reply, ensure_ascii=False, indent=4))
        log('-->%s' % reply['tie_url'])
        _ = self.r.get(reply['tie_url'], headers=self.headers)
        html = _.text
        check = re.findall('该贴已被删除', html)
        if len(check) > 0:
            tid = re.findall('p/(\d+)\?', reply['tie_url'])[0]
            url = 'https://tieba.baidu.com/errorpage/deledErrorInfo?tid=%s' % tid
            error = json.loads(self.r.get(url, headers=self.headers).text)
            type_no = int(error['data']['type'])
            if type_no == 0:
                log('很抱歉，该贴已被删除')
            elif type_no == 1:
                log('小广告太多啦。商品交易贴，度娘建议每天不能超过5条哦')
            elif type_no == 2:
                log('亲，由于您使用机器刷贴，影响了吧友在贴吧的浏览体验，导致贴子被删')
            elif type_no == 3:
                log('亲，由于您的贴子内含有敏感词汇/图片，影响了吧友在贴吧的浏览体验，导致贴子被删')
            elif type_no == 4:
                log('很抱歉，您的贴子已被系统删除')
            elif type_no == 5:
                log('很抱歉，您的贴子已被自己删除')
            elif type_no == 6:
                log('很抱歉，您的贴子已被吧务删除')
            else:
                log('Failed')
                return False
            log('Success')
            return True
        if '该吧被合并您所访问的贴子无法显示' in html:
            log('该吧被合并您所访问的贴子无法显示')
            log('Success')
            return True
        elif '您访问的贴子被隐藏' in html:
            log('抱歉，您访问的贴子被隐藏，暂时无法访问')
            log('Failed')
            return False
        else:
            pass
        data = {
            'ie': re.findall('\"?charset\"?\s*:\s*[\'\"]?(.*?)[\'\"]', html)[0].lower(),
            # 'tbs': re.findall('"tbs"  : "([\d\w]+)"', html)[0],
            'tbs': re.findall('\"?tbs\"?\s*:\s*[\'\"]?([\w\d]+)[\'\"]', html)[0],
            'kw': re.findall('name="kw" value="(.*?)"', html)[0].encode().decode(),
            'fid': re.findall("fid:'(\d+)'", html)[0],
            'tid': re.findall("tid:'(\d+)'", html)[0],
            'username': self.username,
            'delete_my_post': 1,
            'delete_my_thread' : 0,
            'is_vipdel': 0,
            # 'pid': re.findall('pid=(\d+)&', reply['tie_url'])[0],
            'pid': re.findall('cid=(\d+)#', reply['tie_url'])[0],
            'is_finf': 'false'
        }
        if data['pid'] == '0':
            data['pid'] = re.findall('pid=(\d+)', reply['tie_url'])[0]

        url = 'https://tieba.baidu.com/f/commit/post/delete'
        log('-->%s' % url)
        log('delete reply')
        h = self.headers

        h.update({'Referer': reply['tie_url']})
        log(data)

        _ = self.r.post(url, data=data, headers=h)
        log(_.status_code)

        # log(_.content.decode())
        # log(_.request.headers)
        # exit(0)
        return self.error_check(_.text)


    def del_reply(self, reply):
        log(json.dumps(reply, ensure_ascii=False, indent=4))
        log('-->%s' % reply['reply_url'])
        _ = self.r.get(reply['reply_url'], headers=self.headers)
        html = _.text
        if '该吧被合并您所访问的贴子无法显示' in html:
            log('该吧被合并您所访问的贴子无法显示')
            log('Success')
            return True
        elif '您访问的贴子被隐藏' in html:
            log('抱歉，您访问的贴子被隐藏，暂时无法访问')
            log('Failed')
            return False
        else:
            pass
        pid = re.findall('cid=(\d+)#', reply['reply_url'])[0]
        if pid == '0':
             pid = re.findall('pid=(\d+)&', reply['reply_url'])[0]
        data = {
            'ie': re.findall('\"?charset\"?\s*:\s*[\'\"]?(.*?)[\'\"]', html)[0].lower(),
            'tbs': re.findall('\"?tbs\"?\s*:\s*[\'\"]?([\w\d]+)[\'\"]', html)[0],
            'kw': re.findall('name="kw" value="(.*?)"', html)[0].encode().decode(),
            'fid': re.findall("fid:'(\d+)'", html)[0],
            'tid': re.findall("tid:'(\d+)'", html)[0],
            'username': self.username,
            'delete_my_post': 1,
            'delete_my_thread' : 0,
            'is_vipdel': 0,
            # 'pid': re.findall('pid=(\d+)&', reply['reply_url'])[0],
            'pid': pid,
            'is_finf': 'false'
        }
        url = 'https://tieba.baidu.com/f/commit/post/delete'
        log('-->%s' % url)
        log('delete reply')
        _ = self.r.post(url, data=data, headers=self.headers)
        log(_.status_code)
        return self.error_check(_.text)




    def login(self):
        print('这次不用输入前缀`Cookie:`了，直接复制后面的key-value对')
        cookie = input('give me cookies[xxx=xxx; xxx=xxx]:')
        q = {k:v for k,v in re.findall(r'([^=]*)=([^;]*);{0,1}\s{0,1}', cookie)}
        self.r.cookies = cookiejar_from_dict(q)
        url = 'https://tieba.baidu.com'
        log('-->%s' % url)
        _ = self.r.get(url)
        self.username = re.findall('"user_name": "(.*?)",', _.text)[0]
        log('get username: %s' % (self.username))
        url = 'https://tieba.baidu.com/home/profile?un=%s' % self.username
        log('-->%s' % url)
        _ = self.r.get(url)
        self.user_id = re.findall('user_id":(\d+)', _.text)[0]

    def start(self, input_file=True):
        if input_file:
            tie_json = input('Do you have tie json, give me file, if not, just enter:')
            if tie_json != '':
                tie_list = json.load(open(tie_json, 'r'))
            else:
                tie_list = self.get_tie()
                open('clean_tieba_tie_list.json', 'w').write(json.dumps(tie_list, ensure_ascii=False, indent=4))
        else:
            if os.path.exists('clean_tieba_tie_fail.json'):
                log('load tie failed from file')
                tie_list = json.load(open('clean_tieba_tie_fail.json', 'r'))
            else:
                tie_list = self.get_tie()
                open('clean_tieba_tie_list.json', 'w').write(json.dumps(tie_list, ensure_ascii=False, indent=4))


        if input_file:
            reply_json = input('Do you have reply json, give me file, if not, just enter:')
            if reply_json != '':
                reply_list = json.load(open(reply_json, 'r'))
            else:
                reply_list = self.get_reply()
                open('clean_tieba_tie_reply.json', 'w').write(json.dumps(reply_list, ensure_ascii=False, indent=4))
        else:
            if os.path.exists('clean_tieba_reply_fail.json'):
                log('load reply failed from file')
                reply_list = json.load(open('clean_tieba_reply_fail.json', 'r'))
            else:
                reply_list = self.get_reply()
                open('clean_tieba_reply_list.json', 'w').write(json.dumps(reply_list, ensure_ascii=False, indent=4))



        tie_count = len(tie_list)
        tie_fail = []
        reply_count = len(reply_list)
        reply_fail = []
        if tie_count == 0 and reply_count == 0:
            log('done')
            exit()

        tie_is_max = False
        for i in range(tie_count):
            log('tie: %d/%d' % (i + 1, tie_count))
            if tie_is_max:
                tie_fail.append(tie_list[i])
                continue
            status = self.del_tie(tie_list[i])
            if status == 'exit':
                print('达到每日上限，等待下一轮')
                tie_is_max = True
                tie_fail.append(tie_list[i])
            elif status == False:
                tie_fail.append(tie_list[i])
            else:
                pass
        open('clean_tieba_tie_fail.json', 'w').write(json.dumps(tie_fail, ensure_ascii=False, indent=4))


        reply_is_max = False
        for i in range(reply_count):
            log('reply: %d/%d' % (i + 1, reply_count))
            if reply_is_max:
                reply_fail.append(reply_list[i])
                continue
            status = self.del_reply(reply_list[i])
            if status == 'exit':
                print('达到每日上限，等待下一轮')
                reply_is_max = True
                reply_fail.append(reply_list[i])
            elif status == False:
                reply_fail.append(reply_list[i])
            else:
                pass
        open('clean_tieba_reply_fail.json', 'w').write(json.dumps(reply_fail, ensure_ascii=False, indent=4))


if __name__ == '__main__':
    tieba = Tieba()
    parser = OptionParser()
    parser.add_option('-m', '--match',
                      help="give me re format, if match in reply, I will delete")
    (options, args) = parser.parse_args()
    if options.match is not None:
        tieba.match = match
        log('match had set: (%s)' % tieba.match)
    else:
        log('match had set: (%s)' % tieba.match)

    tieba.login()
    tieba.start()

    while(1):
        sleep_hours = 4
        log('will sleep %d hours' % (sleep_hours))
        for i in range(0, sleep_hours, 1):
            log('start after %d hours' % (sleep_hours - i))
            time.sleep(60 * 60)
        tieba.start(False)

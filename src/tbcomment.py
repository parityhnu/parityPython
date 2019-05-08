#!/usr/bin/env Python
# coding=utf-8
import sys
import os
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
import requests
from lxml import etree
import re
import time
import MySQLdb
import random
from urllib import parse
import src.getIP as getIP
from pymongo import MongoClient
import json

mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["comments_tb"]

conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', charset='utf8', db='proxy')
cursor = conn.cursor()
tryTime = 0

class GetIp():
    def delete_ip(self, ip):
        delete_ip_sql = "delete from proxys where ip = '{0}'".format(ip)
        cursor.execute(delete_ip_sql)
        conn.commit()
        return True

    def judge_ip(self, ip, port, type, id, index):
        # 判断给出的代理 ip 是否可用
        http_url =  'https://rate.taobao.com/feedRateList.htm?auctionNumId=' + id + '&currentPageNum=' + str(index)
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)

        headers = {'authority': 'rate.taobao.com',
                   'method': 'GET',
                   'path': '/feedRateList.htm?auctionNumId=' + id + '&currentPageNum=' + str(index),
                   'scheme': 'https',
                   'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
                   'accept-encoding':'gzip, deflate, br',
                   'accept-language':'zh-CN,zh;q=0.9',
                   'cache-control':'max-age=0',
                   'Cookie':'tg=0; cna=uk05E1K1iSkCAToUSgC4Albi; thw=cn; hng=CN%7Czh-CN%7CCNY%7C156; t=f9277a6b756eadb7a19de450304dc685; enc=v7jw24a%2B8dg2MiZzVZCT8ppVjd1YCgzHD8orfbYZnJNZ1STrJMocs44oDu%2BtsjfABeOzCyDdovHNJKIrrqSdPA%3D%3D; x=e%3D1%26p%3D*%26s%3D0%26c%3D0%26f%3D0%26g%3D0%26t%3D0%26__ll%3D-1%26_ato%3D0; miid=442944951227601934; UM_distinctid=16787c0c13e1a9-09fe691b0636d7-3f674706-144000-16787c0c13f58a; _cc_=URm48syIZQ%3D%3D; mt=ci%3D-1_1; cookie2=165406e54d541df45f0b5ba966b07e1c; _tb_token_=5685eab58f6e1; v=0; _m_h5_tk=7c0a5649f5e9f8a87507c8ce65a5a2c4_1554539729108; _m_h5_tk_enc=4e527a02a735d7ee5a4a71a39e1b30cb; x5sec=7b22726174656d616e616765723b32223a226438666332343638656631646662356131663761333435373962353638313533435054366f4f5546454e6e783235716a372b4f6e7a41453d227d; l=bBgIc1l7v-IcnRXkBOCidcSthc7TTIRVgulN6Rrvi_5CFsxBmlQOlGBW5Uv6Vj5POnYB4wIEhpJt3FZUJy91.; isg=BFFRghLv6cjilgXQ3t-aIbjVYF2cmd9LriCX-TPmF5gC2nMsewy4AHcweO6ZUl1o',
                   'upgrade-insecure-requests':'1',
                   'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'
                   }
        print("proxy_url", proxy_url)
        try:
            proxy_dict = {
                'http': proxy_url
            }
            response = requests.get(http_url, headers = headers, proxies = proxy_dict, timeout = 20)

        except Exception as e:
            print("[没有返回]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
            self.delete_ip(ip)
            return False
        else:
            code = response.status_code
            if code >= 200 or code < 300:
                response.encoding='utf-8'
                html_doc = response.text
                if html_doc.find("login-title") == -1:
                    print("代理 ip {0} 及 端口号 {1} 可用".format(ip, port))
                    parsePage(html_doc, id, index)
                    return True
                else:
                    print("[有返回，但是被反爬]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                    self.delete_ip(ip)
                    return False
            else:
                print("[有返回，但是状态码异常]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                self.delete_ip(ip)
                return False

    def getHTMLText(self, id, index):
        try:
            select_random = '''
            select ip,port,proxy_type from proxys order by rand() limit 1
        '''
            cursor.execute(select_random)
            conn.commit()
            result = cursor.fetchone()
            if result is None:
                getIP.crawl_ips()
                global tryTime
                if tryTime == 1:
                    return False
                else:
                    tryTime = 1
                    self.getHTMLText(id, index)
            else:
                ip = result[0]
                port = result[1]
                type = result[2]

                judge_re = self.judge_ip(ip, port, type, id, index)
                if judge_re:
                    return True
                else:
                    self.getHTMLText(id, index)
                    return False
        except Exception as e:
            print(e)

def parsePage(html, id, index):
    try:
        mongoSet.delete_many({"index" : int(index), "gid" : id})
        html = html.split('(', 1)[1]
        html = html[:-2]
        datas1 = json.loads(html)
        datas = datas1['comments']
        content = {}
        attendpics = []
        for data in datas:
            ctime = data['date']
            if ctime == '':
                ctime = 0
            else:
                ctime = int(float(time.mktime(time.strptime(ctime,"%Y年%m月%d日 %H:%M"))) * 1000)
            appendComment = data['append']
            rateContent = data['content']
            pics = data['photos']
            picsresult = []
            for pic in pics:
                picsresult.append(pic['url'])
            auctionSku = data['auction']['sku']
            auctionSku = auctionSku.replace('&nbsp', '')
            displayUserNick = data['user']['nick']
            appendpicsresult = []
            if appendComment is not None:
                content = appendComment['content']
                attendpics = appendComment['photos']
                for pic in attendpics:
                    appendpicsresult.append(pic['url'])

            doc = {"gid" : id, "index" : index, "ctime" : ctime,
                   "rateContent" : rateContent, "pics" : picsresult, "auctionSku" : auctionSku,
                   "displayUserNick" : displayUserNick, "content": content, "attendpics": appendpicsresult}
            x = mongoSet.insert_one(doc)

    except Exception as e:
        print (e)

def start(id):
    time1 = time.time()
    getHtml = GetIp();
    for page in range(5):
        html= getHtml.getHTMLText(id, page + 1)
        time.sleep(random.uniform(0.1,0.3))
    time2 = time.time()
    print('tbcomment:' +str(time2-time1))

if __name__=="__main__":
    start('587861043551')

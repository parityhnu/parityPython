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
import py.getIP as getIP
from pymongo import MongoClient
import json

mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["comments_tm"]

conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', charset='utf8', db='proxy')
cursor = conn.cursor()
tryTime = 0

class GetIp():
    def delete_ip(self, ip):
        delete_ip_sql = "delete from proxys where ip = '{0}'".format(ip)
        cursor.execute(delete_ip_sql)
        conn.commit()
        return True

    def judge_ip(self, ip, port, type, id, index, user):
        # 判断给出的代理 ip 是否可用
        http_url =  'https://rate.tmall.com/list_detail_rate.htm?itemId=' + id + '&sellerId=' + user + '&currentPage=' + str(index)
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)

        headers = {'authority': 'rate.tmall.com',
                   'method': 'GET',
                   'path': '/list_detail_rate.htm?itemId=' + id + '&sellerId=' + user + '&currentPage=' + str(index),
                   'scheme': 'https',
                   'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
                   'accept-encoding':'gzip, deflate, br',
                   'accept-language':'zh-CN,zh;q=0.9',
                   'cache-control':'max-age=0',
                   'Cookie':'lid=%E6%9B%BC%E9%99%80%E8%8A%B1%E7%9A%84%E6%A2%A6; cna=uk05E1K1iSkCAToUSgC4Albi; otherx=e%3D1%26p%3D*%26s%3D0%26c%3D0%26f%3D0%26g%3D0%26t%3D0; hng=CN%7Czh-CN%7CCNY%7C156; x=__ll%3D-1%26_ato%3D0; enc=gne1gTqi1OtRNhkvrXpgjxVbVbux0H%2FCuKccpVFXEvGRVtl1l%2BDxDl6ykZ6lEgGtcGsspErn1VsmptWXoWE0sQ%3D%3D; t=f9277a6b756eadb7a19de450304dc685; _tb_token_=5685eab58f6e1; cookie2=165406e54d541df45f0b5ba966b07e1c; l=bB__8TeuvpUQzKEsBOfGqcSthc7ONQAf5sPr_DwNWICPOkCXGz3hWZsOykTWC3GVa6MJR37dYx9eB4LSOyUCl; isg=BDAwYEDLGJv6rcSifMcXn-OIAf71Xg6490-WeiqD0guF5daP0o2vU23XOa0g9cyb',
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
                    parsePage(html_doc, id, index, user)
                    return True
                else:
                    print("[有返回，但是被反爬]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                    self.delete_ip(ip)
                    return False
            else:
                print("[有返回，但是状态码异常]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                self.delete_ip(ip)
                return False

    def getHTMLText(self, id, index, user):
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
                    self.getHTMLText(id, index, user)
            else:
                ip = result[0]
                port = result[1]
                type = result[2]

                judge_re = self.judge_ip(ip, port, type, id, index, user)
                if judge_re:
                    return True
                else:
                    self.getHTMLText(id, index, user)
                    return False
        except Exception as e:
            print(e)

def parsePage(html, id, index, user):
    try:
        mongoSet.delete_many({"index" : int(index), "gid" : id})
        html = html.split('(', 1)[1]
        html = html[:-1]
        datas1 = json.loads(html)['rateDetail']
        datas = datas1['rateList']
        content = {}
        attendpics = []
        for data in datas:
            ctime = data['gmtCreateTime']['time']
            appendComment = data['appendComment']
            rateContent = data['rateContent']
            pics = data['pics']
            auctionSku = data['auctionSku']
            displayUserNick = data['displayUserNick']
            if appendComment is not None:
                content = appendComment['content']
                attendpics = appendComment['pics']

            doc = {"gid" : id, "index" : index, "ctime" : ctime,
                    "rateContent" : rateContent, "pics" : pics, "auctionSku" : auctionSku,
                    "displayUserNick" : displayUserNick, "content": content, "attendpics": attendpics}
            x = mongoSet.insert_one(doc)

    except Exception as e:
        print (e)

def start(id, user):
    time1 = time.time()
    getHtml = GetIp();
    for page in range(5):
        html= getHtml.getHTMLText(id, page + 1, user)
        time.sleep(random.uniform(0.1,0.3))
    time2 = time.time()
    print('tmcomment:' +str(time2-time1))

if __name__=="__main__":
    start('579794586729','2616970884')

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
from bs4 import BeautifulSoup


mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["attribute_tb"]

conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', charset='utf8', db='proxy')
cursor = conn.cursor()
tryTime = 0

class GetIp():
    def delete_ip(self, ip):
        delete_ip_sql = "delete from proxys where ip = '{0}'".format(ip)
        cursor.execute(delete_ip_sql)
        conn.commit()
        return True

    def judge_ip(self, ip, port, type, id):
        # 判断给出的代理 ip 是否可用
        http_url =  'https://item.taobao.com/item.htm?id=' + id
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)

        headers = {'authority': 'item.taobao.com',
                   'method': 'GET',
                   'path': '/item.htm?id=' + id,
                   'scheme': 'https',
                   'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                   'accept-encoding':'gzip, deflate, br',
                   'accept-language':'zh-CN,zh;q=0.9',
                   'cache-control':'max-age=0',
                   'Cookie':'cna=gWiWEzd3KCgCAXHw6t/tdRt+; tracknick=little%5Cu6B22%5Cu513F; _cc_=U%2BGCWk%2F7og%3D%3D; tg=0; t=e9801ad20b3c927468a784a61e1843b6; hng=CN%7Czh-CN%7CCNY%7C156; thw=cn; _m_h5_tk=43598389d9d5c183061caf2bf88a531e_1555488871521; _m_h5_tk_enc=cd41e3e27cf7d9677770989c215f2d45; v=0; cookie2=53a11f5ed55396a5bb1e4b2acc24fcaa; _tb_token_=e19717ebf6bb0; isg=BI6OVXXZXk9XZOp9lQdl-wyY32SQp1HgmnacFrjX-hFMGy51IJ-iGTTZUwfSGEoh; l=bBOGb8NPv2IcXDusBOCanurza77OSIRYYuPzaNbMi_5Bd6TsOn_Olaz5bF96Vj5RsYTB4smPRvp9-etkZ',
                   'upgrade-insecure-requests':'1',
                   'user-agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
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
                response.encoding='gbk'
                html_doc = response.text
                if html_doc.find("login-title") == -1:
                    print("代理 ip {0} 及 端口号 {1} 可用".format(ip, port))
                    parsePage(html_doc, id)
                    return True
                else:
                    print("[有返回，但是被反爬]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                    self.delete_ip(ip)
                    return False
            else:
                print("[有返回，但是状态码异常]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                self.delete_ip(ip)
                return False

    def getHTMLText(self, id):
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
                    self.getHTMLText(id)
            else:
                ip = result[0]
                port = result[1]
                type = result[2]

                judge_re = self.judge_ip(ip, port, type, id)
                if judge_re:
                    return True
                else:
                    self.getHTMLText(id)
                    return False
        except Exception as e:
            print(e)

def parsePage(html, id):
    try:
        mongoSet.delete_many({ "gid" : id})
        html1 = BeautifulSoup(html, "html.parser")
        datas= html1.select('.attributes-list li')
        for data in datas:
            doc = {"gid" : id, "attribute" : data.text}
            print(doc)
            x = mongoSet.insert_one(doc)
    except Exception as e:
        print (e)

def start(id):
    time1 = time.time()
    getHtml = GetIp();
    html= getHtml.getHTMLText(id)
    time2 = time.time()
    print('tbattribute:' +str(time2-time1))

if __name__=="__main__":
    start('588958332404')

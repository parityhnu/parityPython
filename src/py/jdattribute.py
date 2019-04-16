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
from bs4 import BeautifulSoup

mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["attribute_jd"]

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
        http_url =  'https://item.jd.com/'+ id+'.html'
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)

        headers = {'authority': 'item.jd.com',
                   'method': 'GET',
                   'path': '/'+ id+'.html',
                   'scheme': 'https',
                   'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                   'accept-encoding':'gzip, deflate, br',
                   'accept-language':'zh-CN,zh;q=0.9',
                   'cache-control':'max-age=0',
                   'Cookie':'unpl=V2_ZzNtbUVWQxx0WkVUfB1cDGJRRghLXhMTIV8VXHNJDlBjVxFbclRCFX0UR1FnGVsUZwUZXERcQRFFCEdkeBBVAWMDE1VGZxBFLV0CFSNGF1wjU00zQwBBQHcJFF0uSgwDYgcaDhFTQEJ2XBVQL0oMDDdRFAhyZ0AVRQhHZHgaXA1kBRVVR2dzEkU4dlN5GVsAYzMTbUNnAUEpDkJTfBxUSGQAElVBUUQdcDhHZHg%3d; __jda=122270672.221927694.1555405664.1555405664.1555405665.1; __jdc=122270672; __jdv=122270672|baidu-pinzhuan|t_288551095_baidupinzhuan|cpc|0f3d30c8dba7459bb52f2eb5eba8ac7d_0_60180c2165184ced88a7efb99acd5e27|1555405665412; areaId=18; __jdu=221927694; PCSYCityID=1482; shshshfpa=4b551b55-4435-8b97-5587-ec6ba5b87b7a-1555405669; shshshfpb=d0oxqEDdqIkvt4xrp7S6XHQ%3D%3D; ipLoc-djd=1-72-2799-0; 3AB9D23F7A4B3C9B=FRNBRC6YPTZGRSSUTEUEZSE2MRFXHCXGHRPO37EOTGK7G6PXXXNQ7WPP7ZK6SDXMLYZ7OPAGHYXU7UPEAON7CV467E; shshshfp=e329ad89a310477b2c018711f6f4af23; shshshsID=eae49bea0ebe18d2fb48e447fd6671bb_3_1555405711159; __jdb=122270672.3.221927694|1.1555405665; _gcl_au=1.1.1919730360.1555405712',
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
        datas= html1.select('.p-parameter li')
        for data in datas:
            doc = {"gid" : id, "attribute" : data.text}
            x = mongoSet.insert_one(doc)
    except Exception as e:
        print (e)

def start(id):
    time1 = time.time()
    getHtml = GetIp();
    html= getHtml.getHTMLText(id)
    time2 = time.time()
    print('jdcomment:' +str(time2-time1))

if __name__=="__main__":
    start('100000177760')

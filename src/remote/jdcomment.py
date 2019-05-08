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
import remote.getIP as getIP
from pymongo import MongoClient
import json

mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["comments_jd"]

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
        http_url =  'https://sclub.jd.com/comment/productPageComments.action?callback=fetchJSON_comment98vv7495&productId='+ id +'&score=0&sortType=5&page=' + str(index)+'&pageSize=10&isShadowSku=0&rid=0&fold=1'
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)

        headers = {'authority': 'sclub.jd.com',
                   'method': 'GET',
                   'path': '//productPageComments.action?callback=fetchJSON_comment98vv7495&productId='+ id +'&score=0&sortType=5&page=' + str(index)+'&pageSize=10&isShadowSku=0&rid=0&fold=1',
                   'scheme': 'https',
                   'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
                   'accept-encoding':'gzip, deflate, br',
                   'accept-language':'zh-CN,zh;q=0.9',
                   'cache-control':'max-age=0',
                   'Cookie':'shshshfpa=079cd106-c70e-091a-8867-d3b2cbd9f818-1528535015; shshshfpb=2aaf98df487014ea29fab75587978e66a5b1b97e577f1b5959b1017c96; __jdc=122270672; areaId=18; __jdu=1090355430; PCSYCityID=1482; ipLoc-djd=1-72-2799-0; mt_xid=V2_52007VwMTWlxaVl4aSxhsBW4BRgFaC1tGGk5KWxliBBJVQVFVDU9VEQ4EZwEUVloMUApPeRpdBW8fE1dBWVVLH0gSXgxsARViX2hSahxOGVQBbwEXUm1YV1wY; unpl=V2_ZzNtbRdeRxR9AEAGLBtYAGICFgpLV0IccQBHUClODgJkUxJbclRCFX0UR1FnGFsUZwYZXkJcRhZFCEdkeBBVAWMDE1VGZxBFLV0CFSNGF1wjU00zQwBBQHcJFF0uSgwDYgcaDhFTQEJ2XBVQL0oMDDdRFAhyZ0AVRQhHZHsYVARlBxZYQFZzJXI4dmRyG1UCbjMTbUNnAUEpAURQfBpdSGcCGlxAU0cQdwl2VUsa; __jda=122270672.1090355430.1554517465.1554517466.1554531701.2; __jdv=122270672|baidu-pinzhuan|t_288551095_baidupinzhuan|cpc|0f3d30c8dba7459bb52f2eb5eba8ac7d_0_d850997cf354405f81085905cfc62a17|1554531700763; 3AB9D23F7A4B3C9B=ERSFBTZNXCEIBJPRS4JQ42DLPZ2VTBO2NYYBG2LEYIGTMM65ESD5J2MRN5ZBMSRDWYM6FGD37ZPU5FZQ4OGB5CB4FM; shshshfp=e8ed4c0e9933fc3c82f4995cdec32fe4; shshshsID=a261f7366a08d23a026637235b1afa94_3_1554531706983; _gcl_au=1.1.1949692762.1554531707; __jdb=122270672.3.1090355430|2.1554531701; JSESSIONID=3305EE6659713626EDC76A58349AE558.s1',
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
                response.encoding='gbk'
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
        pics = []
        for data in datas:
            rateContent = data['content']
            ctime = data['creationTime']
            ctime = int(float(time.mktime(time.strptime(ctime,"%Y-%m-%d %H:%M:%S"))) * 1000)
            displayUserNick = data['nickname']
            picsresult = []
            if 'images' in data.keys():
                pics = data['images']
                for pic in pics:
                    picsresult.append(pic['imgUrl'])
            productSize = data['productSize']
            productColor = data['productColor']
            score = data['score']
            if 'afterUserComment' in data.keys():
                content = data['afterUserComment']['hAfterUserComment']['content']

            doc = {"gid" : id, "index" : index, "ctime" : ctime,
                   "rateContent" : rateContent, "pics" : picsresult, "productSize" : productSize, "productColor" : productColor,
                   "displayUserNick" : displayUserNick, "content": content, "score" : score}
            x = mongoSet.insert_one(doc)

    except Exception as e:
        print (e)

def start(id):
    time1 = time.time()
    getHtml = GetIp();
    for page in range(5):
        html= getHtml.getHTMLText(id, page)
        time.sleep(random.uniform(0.1,0.3))
    time2 = time.time()
    print('jdcomment:' +str(time2-time1))

if __name__=="__main__":
    start('100000177760')

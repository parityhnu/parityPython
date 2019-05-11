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
from urllib import parse
import remote.getIP as getIP
import random
import threading

conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', charset='utf8', db='proxy')
cursor = conn.cursor()
tryTime = 0

v = threading.local()

class GetIp():
    def delete_ip(self, ip):
        delete_ip_sql = "delete from proxys where ip = '{0}'".format(ip)
        cursor.execute(delete_ip_sql)
        conn.commit()
        return True

    def judge_ip(self, ip, port, type, goods_root, index, sort):
        sort = int(sort)
        psort = "default"
        # 综合排序为default，销量降序为sale-desc，价格升序为price-asc，价格降序为price-desc
        if sort == 1:
            psort = "sale-desc"
        elif sort == 2:
            psort = "price-asc"
        elif sort == 3:
            psort = "price-desc"
        goods = parse.quote(goods_root)
        # 判断给出的代理 ip 是否可用
        http_url =  'https://s.taobao.com/search?q=' + goods + '&s=' + str(44*index) + '&sort=' + psort + '&initiative_id=staobaoz_' + time.strftime('%Y%m%d',time.localtime(time.time()))
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)

        headers = {'authority': 's.taobao.com',
        'method': 'GET',
        'path': '/search?q=' + goods + '&s='+str(44*index)+ '&sort=' + psort,
        'scheme': 'https',
        'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding':'gzip, deflate, br',
        'accept-language':'zh-CN,zh;q=0.9',
        'cache-control':'max-age=0',
        'Cookie':'tg=0; cna=uk05E1K1iSkCAToUSgC4Albi; thw=cn; hng=CN%7Czh-CN%7CCNY%7C156; t=f9277a6b756eadb7a19de450304dc685; enc=v7jw24a%2B8dg2MiZzVZCT8ppVjd1YCgzHD8orfbYZnJNZ1STrJMocs44oDu%2BtsjfABeOzCyDdovHNJKIrrqSdPA%3D%3D; x=e%3D1%26p%3D*%26s%3D0%26c%3D0%26f%3D0%26g%3D0%26t%3D0%26__ll%3D-1%26_ato%3D0; miid=442944951227601934; UM_distinctid=16787c0c13e1a9-09fe691b0636d7-3f674706-144000-16787c0c13f58a; l=bBQM9JLqvNd2Ch80BOCg5uI8at_9IIRAguPRwN2Mi_5Id6T6tIQOl8GqIF96Vj5Rsx8B4xWabNp9-etlw; _m_h5_tk=352adc112846f3c2ebbfc4cd50514494_1552220416041; _m_h5_tk_enc=8b2c9881bc8423e9590367926c27fb52; _uab_collina=155228537554554124977176; _cc_=URm48syIZQ%3D%3D; mt=ci=0_0; JSESSIONID=F40EC26F9A7E103A018E967C41FABAC6; isg=BPv7jl_aI4Xr6xlDUwlpAZTfit9vb5vckiq6b-241_oRTBsudSCfohmOYqyn92dK',
        'referer': 'https://s.taobao.com/',
        'upgrade-insecure-requests':'1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36'
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
                    parsePage(html_doc, goods_root, index, sort)
                    return True
                else:
                    print("[有返回，但是被反爬]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                    self.delete_ip(ip)
                    return True
            else:
                print("[有返回，但是状态码异常]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                self.delete_ip(ip)
                return True

    def getHTMLText(self, goods, index, sort):
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
                    self.getHTMLText(goods, index, sort)
            else:
                ip = result[0]
                port = result[1]
                type = result[2]

                judge_re = self.judge_ip(ip, port, type, goods, index, sort)
                if judge_re:
                    return True
                else:
                    self.getHTMLText(goods, index, sort)
                    return False
        except Exception as e:
            print(e)

def parsePage(html, goods_root, index, sort):
    try:
        plt = re.findall(r'\"view_price\"\:\"[\d\.]*?\"',html) #正则表达式来匹配 "view_price":"\d\."类型的字符串
        tlt = re.findall(r'\"raw_title\"\:\".*?\"',html)
        #正则表达式来匹配 "raw_title":".*?"类型的字符串,.*?是任意字符的最小匹配
        nidlt = re.findall(r'\"nid\"\:\".*?\"',html)
        userlt = re.findall(r'\"user_id\"\:\".*?\"',html)
        slt = re.findall(r'\"view_sales\"\:\".*?\"',html)
        dlt = re.findall(r'\"detail_url\"\:\".*?\"',html)
        piclt = re.findall(r'\"pic_url\"\:\".*?\"',html)
        nick = re.findall(r'\"nick\"\:\".*?\"',html)
        for i in range(len(slt)-1):
            price = eval(plt[i].split(':', 1)[1])
            title = eval(tlt[i].split(':', 1)[1])
            id = eval(nidlt[i].split(':', 1)[1])
            userid = eval(userlt[i].split(':', 1)[1])
            sale = eval(slt[i].split(':', 1)[1])
            detailUrl = eval(dlt[i].split(':', 1)[1])
            picUrl = eval(piclt[i].split(':', 1)[1])
            shop = eval(nick[i].split(':', 1)[1])
            sale = sale.split('人')[0]
            sale = sale.split('+')[0]
            if '万' in sale:
                sale = float(sale.split('万')[0])*10000
            sale = int(sale)
            score = 100000 - 200 * i
            score = score + sale / 10
            type = 1
            if 'tmall' in detailUrl:
                type = 2
            doc = {"name" : title, "price" : price, "salecomment" : sale, "href" : detailUrl,
                   "image" : picUrl, "keyword" : goods_root, "page" : int(index), "shop" : shop,
                    "sort": sort, "score": score, "type" : type, "gid" : id, "user": userid}
            v.docs.append(doc)
    except Exception as e:
        print (e)

def start(goods, sort, index):
    v.docs = []
    time1 = time.time()
    getHtml = GetIp();
    for page in range(index):
        html= getHtml.getHTMLText(goods, page, sort)
        time.sleep(random.uniform(0.1,0.3))
    time2 = time.time()
    print('tb:' +str(time2-time1))
    return v.docs

if __name__=="__main__":
    start('iphone7', "0")

#!/usr/bin/env Python
# coding=utf-8
import requests
from lxml import etree
import re
import time
import MySQLdb
from urllib import parse
import src.getIP as getIP
from pymongo import MongoClient

mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["goods_tb"]
with open('tbc.txt', 'r', encoding="utf-8") as f:
    ck = f.read()

conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', charset='utf8', db='proxy')
cursor = conn.cursor()
tryTime = 0

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
        http_url =  'https://s.taobao.com/search?q=' + goods + '&s=' + str(44*index) + '&sort=' + psort
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)



        headers = {'authority': 's.taobao.com',
        'method': 'GET',
        'path': '/search?q=' + goods + '&s='+str(44*index)+ '&sort=' + psort,
        'scheme': 'https',
        'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding':'gzip, deflate, br',
        'accept-language':'zh-CN,zh;q=0.9',
        'cache-control':'max-age=0',
        'Cookie':'tg=0; cna=uk05E1K1iSkCAToUSgC4Albi; thw=cn; hng=CN%7Czh-CN%7CCNY%7C156; t=f9277a6b756eadb7a19de450304dc685; enc=v7jw24a%2B8dg2MiZzVZCT8ppVjd1YCgzHD8orfbYZnJNZ1STrJMocs44oDu%2BtsjfABeOzCyDdovHNJKIrrqSdPA%3D%3D; x=e%3D1%26p%3D*%26s%3D0%26c%3D0%26f%3D0%26g%3D0%26t%3D0%26__ll%3D-1%26_ato%3D0; miid=442944951227601934; UM_distinctid=16787c0c13e1a9-09fe691b0636d7-3f674706-144000-16787c0c13f58a; _uab_collina=155228537554554124977176; _cc_=URm48syIZQ%3D%3D; JSESSIONID=9470C3E9CF741D6CE7128695E4C8169A; l=bBQM9JLqvNd2ClIEBOCTScSthVbtOIRAgulN6R5ei_5I86L_rh7OlONJ4Fp6Vj5R_GLB4wIEhpy9-etoi; isg=BKKiGIMICmRVDBDUkkpQLmWM8yhz1LxQmeVkjOw765XAv0M51IG1Hdj967vmrx6l',
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
                    return False
            else:
                print("[有返回，但是状态码异常]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                self.delete_ip(ip)
                return False

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
        mongoSet.delete_many({"page" : int(index), "keyword" : goods_root, "sort": sort})
        plt = re.findall(r'\"view_price\"\:\"[\d\.]*?\"',html) #正则表达式来匹配 "view_price":"\d\."类型的字符串
        tlt = re.findall(r'\"raw_title\"\:\".*?\"',html)
        #正则表达式来匹配 "raw_title":".*?"类型的字符串,.*?是任意字符的最小匹配
        slt = re.findall(r'\"view_sales\"\:\".*?\"',html)
        dlt = re.findall(r'\"detail_url\"\:\".*?\"',html)
        piclt = re.findall(r'\"pic_url\"\:\".*?\"',html)
        nick = re.findall(r'\"nick\"\:\".*?\"',html)
        lp = len(plt)
        lt = len(tlt)
        ls = len(slt)
        ld = len(dlt)
        li = len(piclt)
        ln = len(nick)
        for i in range(len(plt)):
            if i >= lp | i >= lt | i >= ls| i >= ld| i >= li | i >= ln:
                return False
            price = eval(plt[i].split(':', 1)[1])
            title = eval(tlt[i].split(':', 1)[1])
            sale = eval(slt[i].split(':', 1)[1])
            detailUrl = eval(dlt[i].split(':', 1)[1])
            picUrl = eval(piclt[i].split(':', 1)[1])
            shop = eval(nick[i].split(':', 1)[1])
            score = int(str(sale)[0:-3])
            score = score - float(price)
            if ("旗舰店" in str(shop)) | ("自营" in str(shop)):
                score = score + 10000
            doc = {"name" : title, "price" : price, "sale" : sale, "href" : detailUrl,
                   "image" : picUrl, "keyword" : goods_root, "page" : int(index), "shop" : shop, "sort": sort, "score": score}
            x = mongoSet.insert_one(doc)

    except Exception as e:
        print (e)

def start(goods, page, sort):
    time1 = time.time()
    getHtml = GetIp();
    html= getHtml.getHTMLText(goods, page, sort)
    time2 = time.time()
    print('tb:' +str(time2-time1))

if __name__=="__main__":
    start('欧舒丹',"0", "0")

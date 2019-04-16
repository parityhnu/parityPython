#!/usr/bin/env Python
# coding=utf-8
import requests
from lxml import etree
import re
import MySQLdb
import time
from urllib import parse
import src.getIP as getIP
from pymongo import MongoClient
import json

mongoConn = MongoClient("mongodb://localhost:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["goods_jd"]

conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', charset='utf8', db='proxy')
cursor = conn.cursor()
tryTime = 0

class GetIp():
    def delete_ip(self, ip):
        delete_ip_sql = "delete from proxys where ip = '{0}'".format(ip)
        cursor.execute(delete_ip_sql)
        conn.commit()
        return True

    def judge_ip(self, ip, port, type, url, header, goods_root, index, sort):
        # 判断给出的代理 ip 是否可用
        http_url = url
        proxy_url = '{2}://{0}:{1}'.format(ip, port, type)

        print("proxy_url", proxy_url)
        try:
            proxy_dict = {
                '{0}'.format(type): proxy_url
            }
            response = requests.get(http_url, headers = header, proxies = proxy_dict, timeout = 20)

        except Exception as e:
            print("[没有返回]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
            self.delete_ip(ip)
            return False
        else:
            code = response.status_code
            if code >= 200 or code < 300:
                response.encoding='utf-8'
                parsePage(response.text, goods_root, index, ip, port, type, sort)
                return True
            else:
                print("[有返回，但是状态码异常]代理 ip {0} 及 端口号 {1} 不可用，即将从数据库中删除".format(ip, port))
                self.delete_ip(ip)
                return False

    def getHTMLText(self, url, header, goods_root, index, sort):
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
                self.getHTMLText(url, header, goods_root, index, sort)
        else:
            ip = result[0]
            port = result[1]
            type = result[2]

            judge_re = self.judge_ip(ip, port, type, url, header, goods_root, index, sort)
            if judge_re:
                return True
            else:
                self.getHTMLText(url, header, goods_root, index, sort)
                return False

def parsePage(html, goods_root, index, ip, port, type, sort):
    mongoSet.delete_many({"page" : int(index)-1, "keyword" : goods_root, "sort" : sort})
    html1 = etree.HTML(html)
    datas=html1.xpath('//li[contains(@class,"gl-item")]')
    p_id = []
    p_price = []
    p_name = []
    p_href = []
    p_image = []
    p_comment = []
    p_shop = []
    for data in datas:
        shop = data.xpath('div/div[@class="p-shop"]/span/a/text()')
        if len(shop) != 0:
            p_id.append(data.xpath('@data-sku')[0])
            price = data.xpath('div/div[@class="p-price"]/strong/i/text()')
            p_name.append(data.xpath('div/div[@class="p-name p-name-type-2"]/a/em')[0].xpath('string(.)'))
            p_href.append(data.xpath('div/div[@class="p-name p-name-type-2"]/a/@href')[0])
            p_image.append(data.xpath('div/div[@class="p-img"]/a/img/@source-data-lazy-img')[0])
            p_shop.append(shop[0])
            #这个if判断用来处理那些价格可以动态切换的商品，比如上文提到的小米MIX2，他们的价格位置在属性中放了一个最低价
            if len(price) == 0:
                price = data.xpath('div/div[@class="p-price"]/strong/@data-price')
                #xpath('string(.)')用来解析混夹在几个标签中的文本
            p_price.append(price[0])
    p_comment = getComment(p_id, ip, port, type)
    if p_comment != False:
        index2 = 0
        ln = len(p_name)
        lp = len(p_price)
        lc = len(p_comment)
        lh = len(p_href)
        li = len(p_image)
        ls = len(p_shop)
        for name in p_name:
            if index2 >= ln | index2 >= lp | index2 >= lc| index2 >= lh| index2 >= li | index2 >= ls:
                return False
            else:
                score = p_comment[index2]
                score = score - float(p_price[index2])
                if ("旗舰店" in str(p_shop[index2])) | ("自营" in str(p_shop[index2])):
                    score = score + 10000
                doc = {"name" : p_name[index2], "price" : p_price[index2], "comment" : p_comment[index2], "href" : p_href[index2],
                               "image" : p_image[index2], "keyword" : goods_root, "page" : int(index)-1, "shop" : p_shop[index2], "sort" : sort, "score": score}
                x = mongoSet.insert_one(doc)
                index2 = index2 + 1

def getComment(goodID, ip, port, type):
    if goodID is None:
        return False
    url = 'https://club.jd.com/comment/productCommentSummaries.action?enc=utf-8&referenceIds='
    for id in goodID:
        url = url + id + ','
    url = url[:-1]
    proxy_url = '{2}://{0}:{1}'.format(ip, port, type)
    try:
        header = {'authority': 'search.jd.com',
                'method': 'GET',
                'Referer': 'https://search.jd.com/Search?keyword=%E6%AC%A7%E8%88%92%E4%B8%B9&enc=utf-8&suggest=1.his.0.0&wq=&pvid=b3c89067906f4cae8f200079f642ad93',
                'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest',
                'Cookie':'qrsc=3; pinId=RAGa4xMoVrs; xtest=1210.cf6b6759; ipLocation=%u5E7F%u4E1C; _jrda=5; TrackID=1aUdbc9HHS2MdEzabuYEyED1iDJaLWwBAfGBfyIHJZCLWKfWaB_KHKIMX9Vj9_2wUakxuSLAO9AFtB2U0SsAD-mXIh5rIfuDiSHSNhZcsJvg; shshshfpa=17943c91-d534-104f-a035-6e1719740bb6-1525571955; shshshfpb=2f200f7c5265e4af999b95b20d90e6618559f7251020a80ea1aee61500; cn=0; 3AB9D23F7A4B3C9B=QFOFIDQSIC7TZDQ7U4RPNYNFQN7S26SFCQQGTC3YU5UZQJZUBNPEXMX7O3R7SIRBTTJ72AXC4S3IJ46ESBLTNHD37U; ipLoc-djd=19-1607-3638-3638.608841570; __jdu=930036140; user-key=31a7628c-a9b2-44b0-8147-f10a9e597d6f; areaId=19; __jdv=122270672|direct|-|none|-|1529893590075; PCSYCityID=25; mt_xid=V2_52007VwsQU1xaVVoaSClUA2YLEAdbWk5YSk9MQAA0BBZOVQ0ADwNLGlUAZwQXVQpaAlkvShhcDHsCFU5eXENaGkIZWg5nAyJQbVhiWR9BGlUNZwoWYl1dVF0%3D; __jdc=122270672; shshshfp=72ec41b59960ea9a26956307465948f6; rkv=V0700; __jda=122270672.930036140.-.1529979524.1529984840.85; __jdb=122270672.1.930036140|85.1529984840; shshshsID=f797fbad20f4e576e9c30d1c381ecbb1_1_1529984840145'
                }
        proxy_dict = {
            '{0}'.format(type): proxy_url
        }
        response = requests.get(url, headers = header, proxies = proxy_dict, timeout = 20)

    except Exception as e:
        return False
    else:
        code = response.status_code
        if code >= 200 or code < 300:
            response.encoding='utf-8'
            datas = json.loads(response.text)["CommentsCount"]
            p_comment = []
            for data in datas:
                p_comment.append(data["CommentCount"])
            return p_comment
        else:
            return False

def start(goods_root, page, sort):
    # 传进来的page为0、1、2、3、4、5
    # 京东的规则是 首页1、3、5，js 2、4、6
    time1 = time.time()
    goods =  parse.quote(goods_root)
    sort = int(sort)
    psort = 0
    # 综合排序为0，销量降序为4，价格升序为2，价格降序为1
    if sort == 1:
        psort = 4
    elif sort == 2:
        psort = 2
    elif sort == 3:
        psort = 1
    i = int(page) + 1

    getIp = GetIp()
    if i % 2 == 1:
        try:
            url='https://search.jd.com/Search?keyword=' + goods + '&enc=utf-8&page='+str(i)+'&psort='+str(psort)
            head = {'authority': 'search.jd.com',
                    'method': 'GET',
                    'path': '/s_new.php?keyword=' + goods + '&enc=utf-8&page='+str(i)+'&psort='+str(psort),
                    'scheme': 'https',
                    'referer': 'https://search.jd.com/Search?keyword=' + goods + '&enc=utf-8&page=' +str(i)+'&psort='+str(psort),
                    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                    'Cookie':'qrsc=3; pinId=RAGa4xMoVrs; xtest=1210.cf6b6759; ipLocation=%u5E7F%u4E1C; _jrda=5; TrackID=1aUdbc9HHS2MdEzabuYEyED1iDJaLWwBAfGBfyIHJZCLWKfWaB_KHKIMX9Vj9_2wUakxuSLAO9AFtB2U0SsAD-mXIh5rIfuDiSHSNhZcsJvg; shshshfpa=17943c91-d534-104f-a035-6e1719740bb6-1525571955; shshshfpb=2f200f7c5265e4af999b95b20d90e6618559f7251020a80ea1aee61500; cn=0; 3AB9D23F7A4B3C9B=QFOFIDQSIC7TZDQ7U4RPNYNFQN7S26SFCQQGTC3YU5UZQJZUBNPEXMX7O3R7SIRBTTJ72AXC4S3IJ46ESBLTNHD37U; ipLoc-djd=19-1607-3638-3638.608841570; __jdu=930036140; user-key=31a7628c-a9b2-44b0-8147-f10a9e597d6f; areaId=19; __jdv=122270672|direct|-|none|-|1529893590075; PCSYCityID=25; mt_xid=V2_52007VwsQU1xaVVoaSClUA2YLEAdbWk5YSk9MQAA0BBZOVQ0ADwNLGlUAZwQXVQpaAlkvShhcDHsCFU5eXENaGkIZWg5nAyJQbVhiWR9BGlUNZwoWYl1dVF0%3D; __jdc=122270672; shshshfp=72ec41b59960ea9a26956307465948f6; rkv=V0700; __jda=122270672.930036140.-.1529979524.1529984840.85; __jdb=122270672.1.930036140|85.1529984840; shshshsID=f797fbad20f4e576e9c30d1c381ecbb1_1_1529984840145'
                    }
            getIp.getHTMLText(url, head, goods_root, str(i),sort)
        except Exception as e:
            print(e)
    else:
        try:
            a=time.time()
            b='%.5f'%a
            url='https://search.jd.com/s_new.php?keyword=' + goods + '&enc=utf-8&page='+str(i)+'&s='+str(24*i-20)+'&scrolling=y&log_id='+str(b)+'&psort='+str(psort)
            head={'authority': 'search.jd.com',
                  'method': 'GET',
                  'path': '/s_new.php?keyword=' + goods + '&enc=utf-8'+'&psort='+str(psort),
                  'scheme':'https',
                  'referer': 'https://search.jd.com/Search?keyword=' + goods + '&enc=utf-8&page=' + str(i)+'&psort='+str(psort),
                  'user-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
                  'x-requested-with': 'XMLHttpRequest',
                  'Cookie':'qrsc=3; pinId=RAGa4xMoVrs; xtest=1210.cf6b6759; ipLocation=%u5E7F%u4E1C; _jrda=5; TrackID=1aUdbc9HHS2MdEzabuYEyED1iDJaLWwBAfGBfyIHJZCLWKfWaB_KHKIMX9Vj9_2wUakxuSLAO9AFtB2U0SsAD-mXIh5rIfuDiSHSNhZcsJvg; shshshfpa=17943c91-d534-104f-a035-6e1719740bb6-1525571955; shshshfpb=2f200f7c5265e4af999b95b20d90e6618559f7251020a80ea1aee61500; cn=0; 3AB9D23F7A4B3C9B=QFOFIDQSIC7TZDQ7U4RPNYNFQN7S26SFCQQGTC3YU5UZQJZUBNPEXMX7O3R7SIRBTTJ72AXC4S3IJ46ESBLTNHD37U; ipLoc-djd=19-1607-3638-3638.608841570; __jdu=930036140; user-key=31a7628c-a9b2-44b0-8147-f10a9e597d6f; areaId=19; __jdv=122270672|direct|-|none|-|1529893590075; PCSYCityID=25; mt_xid=V2_52007VwsQU1xaVVoaSClUA2YLEAdbWk5YSk9MQAA0BBZOVQ0ADwNLGlUAZwQXVQpaAlkvShhcDHsCFU5eXENaGkIZWg5nAyJQbVhiWR9BGlUNZwoWYl1dVF0%3D; __jdc=122270672; shshshfp=72ec41b59960ea9a26956307465948f6; rkv=V0700; __jda=122270672.930036140.-.1529979524.1529984840.85; __jdb=122270672.1.930036140|85.1529984840; shshshsID=f797fbad20f4e576e9c30d1c381ecbb1_1_1529984840145'

                  }
            getIp.getHTMLText(url, head, goods_root, str(i), sort)
        except Exception as e:
            print(e)
    time2 = time.time()
    print('jd:' +str(time2-time1))

if __name__=="__main__":
    goods_root = 'iphone'
    start(goods_root, "1", "0")
    cursor.close()
    conn.close()

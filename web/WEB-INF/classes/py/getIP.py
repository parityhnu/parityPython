import requests
from scrapy import Selector
import MySQLdb

conn = MySQLdb.connect(host='127.0.0.1', port=3306, user='root', passwd='', charset='utf8', db='proxy')
cursor = conn.cursor()

def crawl_ips():
    headers = {"user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1"}
    for i in range(1, 2):
        response = requests.get("http://www.xicidaili.com/nn/{0}".format(i), headers=headers)
        selector = Selector(text=response.text)
        all_trs = selector.css("#ip_list tr")
        ip_list = []
        for tr in all_trs[1:]:
            speed_str = tr.css("td[class='country']")[2]
            title = speed_str.css(".bar::attr(title)").extract()[0]
            if title:
                pass
                speed = float(title.split("秒")[0])
            all_texts = tr.css("td::text").extract()
            print(all_texts)

            ip = all_texts[0]
            port = all_texts[1]
            attr = all_texts[4]
            type = all_texts[5]
            if attr == 'HTTPS' or attr == 'HTTP':
                attr = '----------'
                type = all_texts[4]

            ip_list.append((ip, port, speed, type))

        # 然后插入数据库
        for ip_info in ip_list:
            insert_sql = '''
                      insert into proxys(ip,port,speed,proxy_type)
                      values('{0}','{1}','{2}','{3}')'''.format(ip_info[0], ip_info[1], ip_info[2], ip_info[3])

            print(insert_sql)
            cursor.execute(insert_sql)
            conn.commit()

if __name__ == '__main__':
    crawl_ips()
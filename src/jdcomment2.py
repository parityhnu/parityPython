#!/usr/bin/env Python
# coding=utf-8
import sys
import os
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from urllib.parse import quote
import time
from bs4 import BeautifulSoup
from pymongo import MongoClient

mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["comments_jd"]

def start(id):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(chrome_options=chrome_options)  # 打开浏览器
    url = 'https://item.jd.com/'+ id+'.html'
    driver.get(url)  # 打开页面
    driver.implicitly_wait(1)  # 等待
    driver.find_element_by_xpath('//*[@id="detail"]/div[1]/ul/li[5]').click()  # 点击商品评论
    # 获取评论数据
    for index in range(5):
        try:
            time.sleep(0.5)
            wait = ui.WebDriverWait(driver,1)
            wait.until(lambda driver: driver.find_element_by_id('comment-0').find_elements_by_class_name('comment-item'))
            divs = driver.find_element_by_id('comment-0').find_elements_by_class_name('comment-item')
            parse(driver.page_source, id, index)

            element = driver.find_element_by_class_name('ui-pager-next')
            driver.execute_script("arguments[0].click();", element)
        except Exception as e:
            driver.close()
            print(e)
    driver.close()

def parse(html_doc, id, index):
    try:
        mongoSet.delete_many({"index" : int(index), "gid" : id})
        html = BeautifulSoup(html_doc, "html.parser")
        datas= html.findAll('div',{'class':'comment-item'})
        for data in datas:
            displayUserNick = data.find('div',{'class':'user-info'}).text
            displayUserNick = displayUserNick.replace(' ','')
            #评星
            score=int(data.find('div',{'class':'comment-star'})['class'][-1][-1])
            # 评语
            rateContent=data.find('p',{'class':'comment-con'}).text

            # 追加评语
            content = ""
            append=data.findAll('div',{'class':'append-comment'})
            la = len(append)
            if la != 0:
                content = append[0].find('p',{'class':'comment-con'}).text

            # 图片数
            pic = []
            picdiv=data.findAll('a',{'class':'J-thumb-img'})
            lp = len(picdiv)
            if lp != 0:
                for a in picdiv:
                    pic.append(a.img['src'])

            spans = data.find('div',{'class':'order-info'}).findAll('span')

            order=[]
            for i, everyone in enumerate(spans):
                order.append(spans[i].text)
            lo = len(order)
            ctime = int(float(time.mktime(time.strptime(order[lo-1],"%Y-%m-%d %H:%M"))) * 1000)
            productSize = ""
            for i in range(lo-1):
                productSize = productSize + " " + order[i]

            doc = {"gid" : id,"index":index, "ctime" : ctime,
                   "rateContent" : rateContent, "pics" : pic, "productSize" : productSize,
                   "displayUserNick" : displayUserNick, "content": content, "score" : score}
            x = mongoSet.insert_one(doc)

    except Exception as e:
        print(e)

if __name__=="__main__":
    start('100000177760')

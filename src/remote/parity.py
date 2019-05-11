import urllib3
import re
import time
import sys
import os
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
import remote.jd as jd
import remote.taobao as taobao
import remote.jdcomment as jdcomment
import remote.tbcomment as tbcomment
import remote.tmcomment as tmcomment
import remote.jdattribute as jdattribute
import remote.tbattribute as tbattribute
import remote.tmattribute as tmattribute
import redis
from concurrent.futures import ThreadPoolExecutor
from pymongo import MongoClient

mongoConn = MongoClient("mongodb://47.100.108.8:27017/")
mongoDb = mongoConn["parity"]  #连接parity数据库，没有则自动创建
mongoSet = mongoDb["goods"]
mongoSetParity = mongoDb["goods_parity"]

pool = redis.ConnectionPool(host='47.100.108.8', port=6379, password='binqing')
r = redis.Redis(connection_pool=pool)

class MyGlobal:
    def __init__(self):
        self.jdfinish = False
        self.tbfinish = False
        self.filterj = False
        self.filtert = False
        self.docTB = []
        self.docJD = []
        self.resultTB = []
        self.resultJD = []

def catchTB(goodName,sort):
    try:
        docTB = []
        reTB = mongoSet.find({"keyword": goodName, "sort" : int(sort), "type" : 1})
        for tb in reTB:
            docTB.append(tb)
        return docTB
    except Exception as e:
        print(e)

def catchJD(goodName,sort):
    try:
        docJD = []
        reJD = mongoSet.find({"keyword": goodName, "sort" : int(sort), "type" : 0})
        for jd in reJD:
            docJD.append(jd)
        return docJD
    except Exception as e:
        print(e)

def filterTB(goodName, sort, myglobal):
    resultTB = []
    datas = goodName.split(' ')
    for tb in myglobal.docTB:
        if fenci(datas, tb.get('name')) == 0:
            resultTB.append(tb)
    myglobal.resultTB = resultTB
    myglobal.filtert = True
    if myglobal.filterj:
        insertparity(goodName, sort, myglobal)

def filterJD(goodName, sort, myglobal):
    resultJD = []
    datas = goodName.split(' ')
    for jd in myglobal.docJD:
        if fenci(datas, jd.get('name')) == 0:
            resultJD.append(jd)
    myglobal.resultJD = resultJD
    myglobal.filterj = True
    if myglobal.filtert:
        insertparity(goodName, sort, myglobal)

def fenci(datas, title):
    title = title.lower()
    result = 0
    for data in datas:
        data = data.lower()
        if title.find(data) < 0:
            result = 1
            break
    return result

def parity(goodName, sort, myglobal):
    with ThreadPoolExecutor(2) as executor:
        executor.submit(filterTB,goodName, sort, myglobal)
        executor.submit(filterJD,goodName, sort, myglobal)

def insertparity(goodName, sort, myglobal):

    print(len(myglobal.resultTB))
    print(len(myglobal.resultJD))
    try:
        mongoSetParity.delete_many({"keyword" : goodName, "sort" : int(sort)})
        num = 0
        for tb in myglobal.resultTB:
            min = 9999
            parityTB = tb
            parityJD = {}
            for jd in myglobal.resultJD:
                editdistnce = eidt_1(tb['name'], jd['name'])
                ave = max(len(tb['name']) , len(jd['name']))
                if (editdistnce / ave) < 0.4:
                    print(editdistnce / ave)
                    if min > editdistnce:
                        min = editdistnce
                        parityJD = jd
            if min != 9999:
                myglobal.resultJD.remove(parityJD)
                parityTB.pop('_id')
                parityJD.pop('_id')
                parityTB['distance'] = min
                parityJD['distance'] = min
                parityTB['order'] = num
                parityJD['order'] = num
                print(parityTB)
                print(parityJD)
                mongoSetParity.insert_one(parityTB)
                mongoSetParity.insert_one(parityJD)
                num = num + 1
                with ThreadPoolExecutor(4) as executor:
                    if parityTB['type'] == 2:
                        executor.submit(catchTMComment, parityTB['gid'], parityTB['user'])
                        executor.submit(catchTMAttribute, parityTB['gid'])
                    else:
                        executor.submit(catchTBComment, parityTB['gid'])
                        executor.submit(catchTBAttribute, parityTB['gid'])
                    executor.submit(catchJDComment, parityJD['gid'])
                    executor.submit(catchJDAttribute, parityJD['gid'])
    except Exception as e:
        print(e)
    print("parity finished")

def catchTMComment(id, user):
    tmcomment.start(id, user)

def catchTBComment(id):
    tbcomment.start(id)

def catchJDComment(id):
    jdcomment.start(id)

def catchTMAttribute(id):
    tmattribute.start(id)

def catchTBAttribute(id):
    tbattribute.start(id)

def catchJDAttribute(id):
    jdattribute.start(id)

def eidt_1(s1, s2):
    s1.replace(' ','')
    s2.replace(' ','')
    s1 = s1.lower()
    s2 = s2.lower()
    if s2.find(s1)>=0:
        return 0
    # 矩阵的下标得多一个
    len_str1 = len(s1) + 1
    len_str2 = len(s2) + 1

    # 初始化了一半  剩下一半在下面初始化
    matrix = [[0] * (len_str2) for i in range(len_str1)]

    for i in range(len_str1):
        for j in range(len_str2):
            if i == 0 and j == 0:
                matrix[i][j] = 0
            # 初始化矩阵
            elif i == 0 and j > 0:
                matrix[0][j] = j
            elif i > 0 and j == 0:
                matrix[i][0] = i
            # flag
            elif s1[i - 1] == s2[j - 1]:
                matrix[i][j] = min(matrix[i - 1][j - 1], matrix[i][j - 1] + 1, matrix[i - 1][j] + 1)
            else:
                matrix[i][j] = min(matrix[i - 1][j - 1] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j] + 1)

    return matrix[len_str1 - 1][len_str2 - 1]

def start(goodName, sort, docTB, docJD):
    print(goodName + "_parity_" + str(sort))
    with ThreadPoolExecutor(2) as executor:
        myglobal = MyGlobal()
        myglobal.docTB = docTB
        myglobal.docJD = docJD
        executor.submit(filterTB, goodName, sort, myglobal)
        executor.submit(filterJD, goodName, sort, myglobal)

if __name__ == '__main__':
    goodName = 'iphone xs max'
    sort = 0
    start(goodName, sort, catchTB(goodName, sort), catchJD(goodName, sort))

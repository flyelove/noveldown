# !/usr/bin/env python
# -*- coding: utf-8 -*-
import pickle
import random
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests
from loguru import logger
from lxml import etree

p = Path(__file__)
USERDATPATH = p.joinpath("../useragent.dat")
USERDATPATH = USERDATPATH.resolve()
logger.debug(f"USERDATPATH:{USERDATPATH}")


class Crawl:
    __accept = {
        "img": ('image/avif,image/webp,image/png,image/svg+xml,image/*;'
                'q=0.8,*/*;q=0.5'),
        "xml": ("text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;"
                "q=0.8,application/signed-exchange;v=b3;q=0.7"),
    }
    __url_ua = "https://www.useragentlist.net/"

    def __init__(self):
        self.headers = {}
        self.headers.setdefault("Referer", "https://www.baidu.com")
        self.headers.setdefault("Accept", "*/*")
        self.headers.setdefault("Accept-Language",
                                ("zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK; "
                                 "q=0.5,en-US;q=0.3,en;q=0.2"))
        self._up_uaset()

    def get(self, url, accept_type="", referer=""):
        """从指定url读取内容
        url:网址
        accept_type: 访问的类型，比如img等，类型不同，headers的
            accept不一样。有可能被ban
        referer: 引用页，一般为百度
        """
        url_sp = urlsplit(url)
        if not referer:
            self.headers["Referer"] = "{0.scheme}://{0.netloc}".format(url_sp)
        else:
            self.headers["Referer"] = referer
        if accept_type:
            self.headers["Accept"] = self.__accept.get(accept_type, "*/*")

        # if type(self.ua) is str:
        #     self.headers["User-Agent"] = self.ua
        # elif type(self.ua) is list:
        #     self.headers["User-Agent"] = str(random.choice(self.ua))
        if self.headers.get("User-Agent", None) is None:
            self.headers["User-Agent"] = random.choice(self.ua)
        logger.debug(f"headers:{self.headers}")
        try:
            respon = requests.get(url, headers=self.headers, timeout=(5, 21))
        except Exception as e:
            logger.warning(f"访问{url}出错,出错信息：{e}")
            return
        logger.debug(respon.headers)
        if respon.ok:
            try:
                if "text" in respon.headers[
                        "Content-Type"] and "charset" not in respon.headers[
                            "Content-Type"]:
                    respon.encoding = "utf8"
            except KeyError:
                respon.encoding = "utf8"

            logger.info(f"读取{url}成功")
            return respon
        else:
            logger.debug(respon.status_code)
            logger.debug(respon.content)

    def _up_uaset(self):
        """读取useragent数据
        先判断useragent文件的最后修改日期，如果超过一个月则重新从网上读取
        __url_ua已经失效，重新启用fake_useragent
        """
        from fake_useragent import UserAgent
        self.ua = [x["useragent"] for x in UserAgent().data_browsers]
        return
        with open(USERDATPATH, "rb") as h_file:
            self.ua_set = pickle.load(h_file)
        self.ua = list(self.ua_set)
        # 60*60*24*30=2592000
        # 60*60*24*7 = 604800
        if time.time() - USERDATPATH.stat().st_mtime > 604800:
            info = f"{USERDATPATH}超过指定时间，即将从{self.__url_ua}重新获取"
            logger.info(info)
            respon = self.get(self.__url_ua)
            if respon:
                parser = etree.HTMLParser()
                root = etree.fromstring(respon.text, parser=parser)
                ua_list = root.xpath("//code/strong/text()")
                self.ua_set = set(ua_list)
                ua_num = len(self.ua_set)
                info = f"从{self.__url_ua}读取到{ua_num}个user-agent，"
                info = info + f"保存入{USERDATPATH}"
                logger.info(info)
                with open(USERDATPATH, "wb") as h_file:
                    pickle.dump(self.ua_set, h_file)

        else:
            logger.debug(f"{USERDATPATH}不需要更新")

        self.ua = list(self.ua_set)


# 使用示例
def main():
    url = "https://www.bing.com/"
    crawler = Crawl()
    respon = crawler.get(url)
    print(respon.text)


if __name__ == "__main__":
    main()

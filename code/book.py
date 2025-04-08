# !/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional
from dataclasses import dataclass
from loguru import logger
from lxml import etree
from urllib.parse import urljoin, urlparse
import sys
from ruamel.yaml import YAML

from utils.crawler import Crawl

parser = etree.HTMLParser()


@dataclass
class SearchResult:
    title: str
    url: str
    description: Optional[str] = None


class Book:

    def __init__(self, 书名="", 作者="", 简介="", 章节=None, 封面=None):
        self.书名 = 书名
        self.作者 = 作者
        self.简介 = 简介
        if 章节 is None:
            章节 = []
        self.章节 = 章节
        self.封面 = 封面

    def __repr__(self):
        return 'Book({0.书名!r}, {0.作者!r})'.format(self)

    def __str__(self):
        c = "书名：{0.书名}\n作者：{0.作者}\n简介：{0.简介}\n"
        c = c.format(self)
        return c

    def text(self):
        ccc = "书名：{0.书名}\n作者：{0.作者}\n简介：{0.简介}\n"
        ccc = ccc.format(self)
        for c in self.章节:
            ccc = ccc + "\n" + str(c)
        return ccc

    def markdown(self):
        ccc = "# {0.书名}\n## 作者：{0.作者}\n## 简介：{0.简介}\n"
        ccc = ccc.format(self)
        for c in self.章节:
            ccc = ccc + "\n" + str(c)
        return ccc


class Zhangjie:
    sss = "零一二三四五六七八九"

    def __init__(self, index=0, title="", url="", content=None):
        self.index = index
        self.title = title
        self.url = url
        if content is None:
            content = []
        self.content = content

    def __repr__(self):
        return 'Zhangjie({0.index!r}, {0.title!r})'.format(self)

    def __str__(self):
        s = "".join([self.sss[int(x)] for x in str(self.index + 1)])
        c = f"###{self.title}\n"
        c = c + "\n".join(self.content)
        return c


class BookCrawler:

    def __init__(self, yaml_path="./book.yaml"):
        yaml = YAML(typ='safe')
        with open(yaml_path, encoding="utf8") as h_file:
            dat = yaml.load(h_file)
        self.book_rule = dat
        self.crawler = Crawl()
        self.now_rule = None

    def get_dat(self, root, nkey):
        '''
        root, nkey为规则名
        规则为：xpath路径(str), 切片/索引
        或者， xpath路径, 属性名(str)
        或者， xpath路径, 属性名, 切片/索引
        '''
        rule = self.now_rule.get(nkey, None)
        if rule is None:
            logger.info(f"未能找到{nkey}的相关规则，")
            return None
        logger.debug(f"{nkey}={rule}")
        if not isinstance(rule, str):
            rule, *value = rule
        else:
            value = []
        dat = root.xpath(rule)
        if nkey not in ['目录', '章节内容']:
            dat = dat[0]
        if not value:
            return dat
        if isinstance(value[0], str):
            dat = dat.attrib[value[0]]
            try:
                if isinstance(value[1], int):
                    dat = dat[value[1]]
                if isinstance(value[1], list):
                    sl = slice(*value[1])
                    dat = dat[sl]
            except IndexError:
                pass
        else:
            if isinstance(value[0], int):
                dat = dat[value[0]]
            if isinstance(value[0], list):
                sl = slice(*value[0])
                dat = dat[sl]

        logger.debug(f"{nkey}={dat}")
        return dat

    def crawl(self, url):
        """
        url为书签页地址，必须为http://www.baidu.com 的完整样式
        """
        urlsp = urlparse(url)
        if not (urlsp.scheme and urlsp.netloc):
            raise ValueError(f"{url}错误，请输入完整的url地址")
        for rule in self.book_rule:
            if rule["地址"] in url:
                self.now_rule = rule
                break
        if self.now_rule is None:
            logger.info(f"未能找到{url}的相关规则，"
                        "请先更新规则或者检查url")
            raise ValueError(f"{url}未能匹配规则")
        logger.info(f"即将依据{self.now_rule['站名']}的信息爬取")
        headers = self.now_rule.get("headers", None)
        if headers:
            for k in headers:
                self.crawler.headers[k] = headers[k]
        self.now_chartset = self.now_rule.get("编码", 'utf8')
        respon = self.crawler.get(url)
        if not respon:
            logger.warning(f"读取{url}失败")
            return

        respon.encoding = self.now_chartset
        root = etree.fromstring(respon.text, parser=parser)
        bk = {}
        # bk["书名"] = root.xpath(self.now_rule["书名"])[0]
        bk["书名"] = self.get_dat(root, "书名")
        # bk["作者"] = root.xpath(self.now_rule["作者"])[0]
        bk["作者"] = self.get_dat(root, "作者")
        cover_url = urljoin(url, self.get_dat(root, "封面"))
        if cover_url:
            bk['封面'] = cover_url
        # bk["简介"] = root.xpath(self.now_rule["简介"])[0]
        bk["简介"] = self.get_dat(root, "简介")
        # bk["标签"]=root.xpath(self.now_rule["xpath"]["标签"])
        mulu_url = self.get_dat(root, "目录页")
        if not mulu_url:
            mulu_url = url
        bk["章节"] = [
            Zhangjie(
                i,
                x[0],
                x[1],
            ) for i, x in enumerate(self.mulu(mulu_url, ))
        ]
        book = Book(**bk)
        logger.info(f"初步解析书籍信息结束：{book}, "
                    f"共收集到{len(book.章节)}个章节信息")
        return book

    def mulu(self, url):
        mulu_list = []
        respon = self.crawler.get(url)
        if not respon:
            return mulu_list
        respon.encoding = self.now_chartset
        root = etree.fromstring(respon.text, parser=parser)
        # bklist = root.xpath(self.now_rule["目录"])
        bklist = self.get_dat(root, "目录")
        for mmm in bklist:
            mt = mmm.text
            murl = urljoin(url, mmm.attrib['href'])
            # print(mt, murl)
            mulu_list.append((mt, murl))

        nxt_url = root.xpath("//a[contains(text(), '下一页')]")
        if nxt_url:
            nxt_url = urljoin(url, nxt_url[0].attrib['href'])
            mulu_list += self.mulu(nxt_url)

        return mulu_list

    def zhangjie_data(self, url):
        zj = []
        respon = self.crawler.get(url)
        if not respon:
            return zj
        root = etree.fromstring(respon.text, parser=parser)
        # zj = root.xpath(self.now_rule["xpath"]["章节内容"])
        zj = self.get_dat(root, "章节内容")
        zj = [x.strip() for x in zj if x.strip()]
        nxt_url = root.xpath("//a[contains(text(), '下一页')]")
        if nxt_url:
            nxt_url = urljoin(url, nxt_url[0].attrib['href'])
            zj += self.zhangjie_data(nxt_url)
        return zj

    def zhangjie_update(self, book):
        # zjtmp = []
        # for zj in book.章节:
        #     zj.content = self.zhangjie_data(zj.url)
        #     zjtmp.append(zj)
        # book.章节 = zjtmp
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        urls = [x.url for x in book.章节]
        nnn = len(urls)
        need_update = [x.url for x in book.章节 if not x.content]
        logger.info("即将读取章节内容，"
                    f"共有{nnn}个章节需要读取")
        start_time = time.time()
        with ThreadPoolExecutor() as executor:
            future_to_url = {
                executor.submit(
                    self.zhangjie_data,
                    url,
                ): url
                for url in need_update
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                    ii = urls.index(url)
                    book.章节[ii].content = data
                except Exception as exc:
                    logger.warning('%r generated an exception: %s' % (
                        url,
                        exc,
                    ))

        us_time = time.time() - start_time
        ok_zj = [x for x in book.章节 if x.content]
        if len(ok_zj) < nnn:
            n = nnn - len(ok_zj)
            logger.info(f"有{n}个章节读取失败，即将重新读取")
            book = self.zhangjie_update(book)
        per_time = us_time / nnn
        logger.info(f"章节读取完毕，{len(ok_zj)}/{nnn}，"
                    f"平均用时{per_time}")
        return book

    def save_book(self, book, save_dir="./books"):
        """
        保存book到文本文件
        book: 字典
        save_dir: str, path 保存的目录
        """
        from pathlib import Path
        import pickle
        save_dir = Path(save_dir)
        if not save_dir.exists():
            save_dir.mkdir(parents=True, exist_ok=True)
        elif not save_dir.is_dir():
            raise ValueError(f"{save_dir}不是目录")
        tmp = book.书名 + "_" + book.作者
        if book.封面:
            cover_file = save_dir.joinpath(tmp + ".jpg")
            cover_dat = self.crawler.get(book.封面)
            if cover_dat:
                with open(cover_file, "wb") as h_file:
                    h_file.write(cover_dat.content)
                logger.info(f"封面已保存到{cover_file}")
        bfile = save_dir.joinpath(tmp + ".txt")
        dfile = save_dir.joinpath(tmp + ".dat")
        logger.info(f"book将被保存到{bfile}(文本), {dfile}")
        with open(dfile, "wb") as h_file:
            pickle.dump(book, h_file)

        with open(bfile, "w", encoding="utf8") as h_file:
            h_file.write(book.text())


class BingSearch:
    """
    使用bing搜索引擎搜索书籍，这个现在不稳定，不建议使用
    """
    url_base = "https://www.bing.com/search"

    def __init__(self):
        self.crawler = Crawl()

    def search(self, search_key):
        results = []
        search_key = f"{search_key} -site:zhihu.com"
        url = f"{self.url_base}?q={search_key}"
        respon = self.crawler.get(url)
        if not respon:
            return []
        with open("tmp/bing.html", "w", encoding="utf8") as h_file:
            h_file.write(respon.text)

        root = etree.fromstring(respon.text, parser=parser)
        for li in root.xpath("//li[@class='b_algo']"):
            result = SearchResult(
                title=li.xpath(".//h2/a")[0].text,
                url=li.xpath(".//h2/a")[0].attrib["href"],
                description=li.xpath(".//p")[0].text
            )
            results.append(result)
        return results


def book_search_test():
    searh = BingSearch()
    get = searh.search("宿命之环")
    print(get)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='从指定网址下载小说',
                                     exit_on_error=False)
    parser.add_argument("url", type=str)
    args = parser.parse_args()
    # url = "https://www.uuks5.com/book/540055/"
    url = args.url
    crawler = BookCrawler()
    book = crawler.crawl(url)
    # print(book)
    # return
    book = crawler.zhangjie_update(book)
    crawler.save_book(book)


if __name__ == "__main__":
    # book_search_test()
    main()

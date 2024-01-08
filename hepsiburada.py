# CrawlerProcess scrapy projesini tek dosyada çalıştırabilmemize olanak sağlıyor.
from scrapy.crawler import CrawlerProcess
import scrapy
import json
import re
import pprint
import time

DEFAULT_USER_AGENT = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.38'
    }
    
BASE_URL = 'https://www.hepsiburada.com'
DEFAULT_ENCODING = 'utf-8'

class Kategoriler(scrapy.Spider):
    name = "hepsiburada"
    user_agent = DEFAULT_USER_AGENT
    url = BASE_URL + "/tum-kategoriler"

    def start_requests(self):
        yield scrapy.Request(
            url=self.url,
            headers=self.user_agent,
        )
        
    def save_file(self,veri,dosyaAdi):
        with open(dosyaAdi+".json","a+", encoding=DEFAULT_ENCODING) as file:
            file.write(json.dumps(veri,indent=2, ensure_ascii=False))
            
    def parse(self,response):
        categories = response.xpath("//*[@class='categories']")
        categories.append(response.xpath("//*[@class='categories left-absolute-1']"))
        categories.append(response.xpath("//*[@class='categories left-absolute-2']"))
        categories.append(response.xpath("//*[@class='categories left-absolute-3']"))
        liste = list()
        for category in categories:
            groups = category.xpath(".//*[@class='group']")
            items = dict()
            for group in groups:
                a_etiketi = group.xpath(".//div/a")[1:]
                data = dict()
                if a_etiketi != []:
                    for a in a_etiketi:
                        name = a.xpath(".//text()").extract_first()
                        link = a.xpath(".//@href").extract_first()
                        if link != '':
                            data[name] = response.urljoin(link)
                absolute_category = group.xpath(".//div[1]/a/text()").extract()
                for ctgry in absolute_category:
                    items[ctgry] = data
            liste.append(items)
        self.save_file( liste,"tum-kategoriler" )
        
class HepsiburadaCrawlSpider(scrapy.Spider):
    name = 'hepsiburada_crawl'
    allowed_domains = ['hepsiburada.com']
    user_agent = DEFAULT_USER_AGENT
    custom_settings = {
        "FEED":"csv",
        "FEED_URI":"urunler.csv",
        "FEED_EXPORT_ENCODING":"utf-8",
        'CONCURRENT_REQUESTS' : 32,
        'DOWNLOAD_DELAY': 1,
    }

    # kategori linkleri
    linkler = list()
    
    # count ,next_page 
    count = 1

    base_url = BASE_URL

    # constructer init, categories read
    def __init__(self):
        #hepsiburada_tumkategoriler.json dosyasını okuma ve içerisindeki linkleri linkler listesine ekleme
        with open('tum-kategoriler.json',encoding='utf-8') as file:
            veriler = json.load(file)
            for veri in veriler:
                for j in veri.values():
                    for i in j.values():
                        self.linkler.append(i)

    def start_requests(self):
        #linkler listesindeki her bir linke request yapmak
        for link in self.linkler:
            self.count = 0
            time.sleep(1)
            yield scrapy.Request(
                url = link,
                headers=self.user_agent
            ) 
    def parse(self, response):
        urun_kategorisi = response.xpath("//span[@class='JGSF21F9Hi81lNaldVqp']/text()").extract()
        urun_kategorisi = urun_kategorisi[len(urun_kategorisi)-1:][0]
        
        # urunleri liste olarak almak
        urunler = response.css("li.productListContent-zAP0Y5msy8OHn5z7T_K_")[1:]

        for urun in urunler:
            urun_link = urun.css("a::attr(href)").extract_first()

            yield scrapy.Request(
                    url = self.base_url + urun_link,
                    headers=self.user_agent,
                    callback=self.parse_page,
                    meta = {
                    'urun_link':urun_link,
                    'urun_kategorisi':urun_kategorisi
                    }
                )
        """
        self.count +=1
        next_page = response.urljoin(f"?sayfa={self.count}")
        yield scrapy.Request(
            url=next_page,
            headers = self.user_agent,
            callback=self.parse
        )"""
    def parse_page(self,response):
        urun_link = response.meta.get("urun_link")
        urun_kategorisi = response.meta.get("urun_kategorisi")
        
        title = response.css("#product-name::text").extract_first().strip()
        price = response.css("span.price")[0].css("span")[1].css("span::text").extract_first()
        images =  response.css("img.product-image")[:5].attrib["src"]

        # ürün değerlendirme sayısı
        comment_count =  response.css("#comments-container").css("span::text").extract_first()
        
        # satıcı adı ve puanı
        seller_name = response.xpath("//span[@class='seller']/span[2]/a/text()").extract_first().strip()

        # tüm özellikler tablosu
        all_features_th = response.xpath("//table[@class='data-list tech-spec']").xpath(".//th/text()").extract()
        all_features_td = response.xpath("//table[@class='data-list tech-spec']").xpath(".//td/span/text()").extract()
        all_features = list(zip(all_features_th,all_features_td))
        all_features_items = dict()
        for th,td in all_features:
            all_features_items[th] = td

        # comments
        comment_items = list()
        comments = response.xpath("//*[@class='hermes-ReviewCard-module-dY_oaYMIo0DJcUiSeaVW']")
        
        if comments is not None:
            for comment in comments:
                name = comment.xpath(".//strong[@data-testid='title']/text()").extract_first()
                description = comment.xpath(".//span[@itemprop='description']/text()").extract_first()
                date = comment.css("span.hermes-ReviewCard-module-WROMVGVqxBDYV9UkBWTS::text").extract_first()
                seller = comment.css("span.hermes-ReviewCard-module-_yfz1l8ZrCQDTEOSHbzQ::text").extract_first()
                star_count = len(comment.css("div.hermes-RatingPointer-module-UefD0t2XvgGWsKdLkNoX").css("div.star"))
                items = {
                    'date':date,
                    'name':name,
                    'seller':seller,
                    'comment':description,
                    'star':star_count
                }
                comment_items.append(items)
                
        items = dict()
        items['category'] = urun_kategorisi
        items['title'] = title
        items['urun_link']= urun_link
        items['price'] = price
        items['images'] = images
        items['comment_count'] = comment_count
        items['seller_name'] = seller_name
        items['all_features_items'] = all_features_items
        if comment_items == {}:
            items['comments'] = None
        else:
            items['comments'] = comment_items
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(items)
        yield items
        #print(items['comments'])
        #self.save_file(items,"tüm_ürünler")

if __name__=='__main__':
    ### Run scraper 
    crw = CrawlerProcess()
    #crw.crawl(Kategoriler)
    crw.crawl(HepsiburadaCrawlSpider)
    
    crw.start()


from scrapy.crawler import CrawlerProcess
import scrapy
import json
import re
from trkarakterdel import karakterTemizle
class Kategoriler(scrapy.Spider):
    name = "hepsiburada"
    #start_urls = ["https://www.hepsiburada.com/tum-kategoriler"]
    user_agent = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.38'
    }
    def start_requests(self):
        url = "https://www.hepsiburada.com/tum-kategoriler"
        yield scrapy.Request(
            url=url,
            headers=self.user_agent,
        )
    def save_file(self,veri,dosyaAdi):
        with open(dosyaAdi+".json","a+", encoding='utf8') as file:
            file.write(json.dumps(veri,indent=2, ensure_ascii=False))
    def parse(self,response):
        categories = response.xpath("//*[@class='categories']")
        categories.append(response.xpath("//*[@class='categories left-absolute-1']"))
        categories.append(response.xpath("//*[@class='categories left-absolute-2']"))
        categories.append(response.xpath("//*[@class='categories left-absolute-3']"))
        liste = []
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
        self.save_file(liste,"tum-kategoriler")
class HepsiburadaCrawlSpider(scrapy.Spider):
    name = 'hepsiburada_crawl'
    allowed_domains = ['hepsiburada.com']
    user_agent = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36 Edg/95.0.1020.38'
    }
    # custom_settings = {
    #     "FEED":"json",
    #     "FEED_URI":"urunler.json"
    # }
    # kategori linkleri
    linkler = []
    
    # count ,next_page 
    count = 1

    # ürün sayısı
    count_urun = 0
    def __init__(self):
        #hepsiburada_tumkategoriler.json dosyasını okuma ve içerisindeki linkleri linkler listesine ekleme
        with open('hepsiburada_tumkategoriler.json',encoding='utf-8') as file:
            veriler = json.load(file)
            for veri in veriler:
                for j in veri.values():
                    for i in j.values():
                        self.linkler.append(i)

    def start_requests(self):
        #linkler listesindeki her bir linke request yapmak
        for link in self.linkler:
            self.count = 0
            yield scrapy.Request(
                url = link,
                headers=self.user_agent
            ) 
    def parse(self, response):
        urun_kategorisi = response.xpath("//span[@itemprop='name']/text()").extract()
        urun_kategorisi = urun_kategorisi[len(urun_kategorisi)-1:][0]
        
        # urunleri liste olarak almak
        urunler = response.xpath("//*[@class='productListContent-item']")

        for urun in urunler:
            urun_link = urun.xpath(".//div/a/@href").extract_first()
            yield scrapy.Request(
                    url = urun_link,
                    headers=self.user_agent,
                    callback=self.parse_page,
                    meta = {
                    'urun_link':urun_link,
                    'urun_kategorisi':urun_kategorisi
                    }
                )
        self.count +=1
        next_page = response.urljoin(f"?sayfa={self.count}")
        yield scrapy.Request(
            url=next_page,
            headers = self.user_agent,
            callback=self.parse
        )
    def save_file(self,veri,dosyaAdi):
        with open(dosyaAdi+".json","a+", encoding='utf8') as file:
            file.write(json.dumps(veri,indent=2, ensure_ascii=False))

    def parse_page(self,response):
        urun_link = response.meta.get("urun_link")
        urun_kategorisi = response.meta.get("urun_kategorisi")

        title = response.xpath("//h1[@itemprop='name']/text()").extract_first().strip()
        price = response.xpath("//span[@class='price']/span[1]/text()").extract_first()
        images = response.xpath("//img[@itemprop='image']/@data-src").extract()
        
        try:
            rating_star = response.xpath("//span[@class='rating-star']/text()").extract_first().strip()
            extra_discount_price = response.xpath("//*[@class='extra-discount-price']/span/text()").extract_first()
        except:
            # değerlendirme yapılmamış ürünleri None yapıyoruz
            rating_star = None
            # ekstra fiyat yoksa None yapıyoruz
            extra_discount_price = None
        
        # ürün değerlendirme sayısı
        comment_count = response.xpath("//*[@id='comments-container']/a/span/text()").extract_first()
        
        # satıcı adı ve puanı
        seller_name = response.xpath("//span[@class='seller']/span[2]/a/text()").extract_first().strip()
        seller_rating = response.xpath("//*[@id='merchantRatingTopPrice']/span[2]/text()").extract_first().strip()
        
        # tüm özellikler tablosu
        all_features_th = response.xpath("//table[@class='data-list tech-spec']").xpath(".//th/text()").extract()
        all_features_td = response.xpath("//table[@class='data-list tech-spec']").xpath(".//td/text()").extract()
        all_features = list(zip(all_features_th,all_features_td))
        all_features_items = dict()
        for th,td in all_features:
            all_features_items[th] = td
        # 
        items = dict()
        items['category'] = urun_kategorisi
        items['title'] = title
        items['urun_link']= urun_link
        items['price'] = price
        items['images'] = images
        items['rating_star'] = rating_star
        items['extra_discount_price'] = extra_discount_price
        items['comment_count'] = comment_count
        items['seller_name'] = seller_name
        items['seller_rating'] = seller_rating
        items['all_features_items'] = all_features_items
        #yield items
        self.save_file(items,"tüm_ürünler")
crw = CrawlerProcess()
crw.crawl(HepsiburadaCrawlSpider)
#crw.crawl(Kategoriler)
crw.start()



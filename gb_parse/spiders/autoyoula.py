import scrapy
import pymongo
import re
import base64


class AutoyoulaSpider(scrapy.Spider):
    name = 'autoyoula'
    allowed_domains = ['auto.youla.ru']
    start_urls = ['https://auto.youla.ru/']

    ccs_query = {
        'brands': 'div.ColumnItemList_container__5gTrc div.ColumnItemList_column__5gjdt a.blackLink',
        'pagination': '.Paginator_block__2XAPy a.Paginator_button__u1e7D',
        'ads': 'article.SerpSnippet_snippet__3O1t2 a.SerpSnippet_name__3F7Yu'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db = pymongo.MongoClient()['parse_gb_youla'][self.name]

    def parse(self, response):
        for brand in response.css(self.ccs_query['brands']):
            yield response.follow(brand.attrib.get('href'), callback=self.brand_page_parse)

    def brand_page_parse(self, response):
        for pag_page in response.css(self.ccs_query['pagination']):
            yield response.follow(pag_page.attrib.get('href'), callback=self.brand_page_parse)

        for ads_page in response.css(self.ccs_query['ads']):
            yield response.follow(ads_page.attrib.get('href'), callback=self.ads_parse)

    def ads_parse(self, response):
        data = {
            'title': response.css('.AdvertCard_advertTitle__1S1Ak::text').get(),
            'images': [img.attrib.get('src') for img in response.css('figure.PhotoGallery_photo__36e_r img')],
            'description': response.css('div.AdvertCard_descriptionInner__KnuRi::text').get(),
            'url': response.url,
            'author': self.parse_author(response),
            'specification': self.parse_specification(response),
            'phone': self.parse_phone(response),
        }

        self.db.insert_one(data)

    def parse_phone(self, response):
        result = None
        enc_phone = re.findall(r"%2C%22phone%22%2C%22(.{34})%3D%3D%22%2C", response.text)
        if enc_phone:
            result = base64.b64decode(base64.b64decode(enc_phone[0] + '==')).decode('utf-8')

        return result

    def parse_author(self, response):
        youla_id = re.findall(r"youlaId%22%2C%22(.{24})%22%2C%22avatar", response.text)
        return f'https://youla.ru/user/{youla_id[0]}' if youla_id else None

    def parse_specification(self, response):
        result = []
        selectors = response.css('.AdvertSpecs_row__ljPcX')
        for el in selectors:
            if el.css('.AdvertSpecs_data__xK2Qx a::text').get():
                val = el.css('.AdvertSpecs_data__xK2Qx a::text').get()
            else:
                val = el.css('.AdvertSpecs_data__xK2Qx::text').get()
            result.append({el.css('.AdvertSpecs_label__2JHnS::text').get(): val})

        return result
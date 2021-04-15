import scrapy
from gb_parse.loaders import AvitoLoader
from gb_parse.spiders.xpath import AVITO_PAGE_XPATH, AVITO_OBJECT_XPATH


class AvitoParseSpider(scrapy.Spider):
    name = 'avito'
    allowed_domains = ['avito.ru']
    start_urls = ['https://www.avito.ru/krasnodar/kvartiry/prodam']
    current_page = 1

    def _get_ad_xpath(self, response, xpath, callback):
        for url in response.xpath(xpath):
            yield response.follow(url, callback=callback)

    def parse(self, response):
        if self.current_page == 1:
            max_page = int(response.xpath(AVITO_PAGE_XPATH['pagination']).extract()[-1].
                           split('(')[-1].replace(')', ''))
            while self.current_page <= max_page:
                    self.current_page += 1
                    yield response.follow(
                        f'?p={self.current_page}',
                        callback=self.parse
                    )
        yield from self._get_ad_xpath(response, AVITO_PAGE_XPATH['advert'], self.advert_parse)

    def advert_parse(self, response):
        loader = AvitoLoader(response=response)
        loader.add_value("url", response.url)
        for key, xpath in AVITO_OBJECT_XPATH.items():
            loader.add_xpath(key, xpath)

        yield loader.load_item()
import scrapy
from ..loaders import HHVacancyLoader, HHCompanyLoader


class HeadSpider(scrapy.Spider):
    name = 'head'
    allowed_domains = ['hh.ru']
    start_urls = ['https://hh.ru/search/vacancy?schedule=remote&L_profession_id=0&area=113']
    _xpath = {
        'pagination': '//div[@data-qa="pager-block"]//a[@data-qa="pager-page"]/@href',
        'vacancy_urls': '//a[@data-qa="vacancy-serp__vacancy-title"]/@href',
    }
    vacancy_xpath = {
        "title": '//h1[@data-qa="vacancy-title"]/text()',
        "salary": '//p[@class="vacancy-salary"]//text()',
        "description": '//div[@data-qa="vacancy-description"]//text()',
        "skills": '//div[@class="bloko-tag-list"]//span[@data-qa="bloko-tag__text"]/text()',
        "company_url": '//a[@data-qa="vacancy-company-name"]/@href',
    }

    company_xpath = {
        'name': '//h1/span[contains(@data-qa, "company-header-title-name")]/text()',
        'web_site': '//a[contains(@data-qa, "company-site")]/@href',
        'description': '//div[contains(@data-qa, "company-description")]//text()',
        'fields_of_activity': '//div[contains(@class, "employer-sidebar-block")]//p/text()',

    }

    def parse(self, response, **kwargs):
        for pag_page in response.xpath(self._xpath['pagination']):
            yield response.follow(pag_page, callback=self.parse)

        for vacancy_page in response.xpath(self._xpath['vacancy_urls']):
            yield response.follow(vacancy_page, callback=self.vacancy_parse)

    def vacancy_parse(self, response):
        loader = HHVacancyLoader(response=response)
        loader.add_value('url', response.url)
        for key, value in self.vacancy_xpath.items():
            loader.add_xpath(key, value)

        yield loader.load_item()
        yield response.follow(response.xpath(self.vacancy_xpath['company_url']).get(), callback=self.company_parse)

    def company_parse(self, response):
        loader = HHCompanyLoader(response=response)
        loader.add_value('url', response.url)
        for key, value in self.company_xpath.items():
            loader.add_xpath(key, value)

        yield loader.load_item()
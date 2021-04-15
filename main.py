from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from gb_parse.spiders.avito_parse import AvitoParseSpider

if __name__ == "__main__":
    crawler_settings = Settings()
    crawler_settings.setmodule("gb_parse.settings")
    crawler_proc = CrawlerProcess(settings=crawler_settings)
    crawler_proc.crawl(AvitoParseSpider)
    crawler_proc.start()
# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GbParseItem(scrapy.Item):
    _id = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
    params = scrapy.Field()
    images = scrapy.Field()
    date_parsed = scrapy.Field()
    url = scrapy.Field()
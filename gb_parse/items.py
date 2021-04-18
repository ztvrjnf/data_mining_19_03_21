# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class GbParseItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class InstagramTagItem(scrapy.Item):
    _id = scrapy.Field()
    instagram_id = scrapy.Field()
    name = scrapy.Field()
    picture_url = scrapy.Field()
    image_info = scrapy.Field()


class InstagramPostItem(scrapy.Item):
    _id = scrapy.Field()
    data = scrapy.Field()
    picture_url = scrapy.Field()
    date_parse = scrapy.Field()
    image_info = scrapy.Field()
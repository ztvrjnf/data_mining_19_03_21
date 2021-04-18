import scrapy
import json
from datetime import datetime as dt
from ..items import InstagramTagItem, InstagramPostItem


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    allowed_domains = ['www.instagram.com']
    start_urls = ['https://www.instagram.com/']
    query_hash = {
        'tag_paginate': '9b498c08113f1e09617a1703c22b2f32'
    }
    tag_list = ['python']

    def __init__(self, login, password, *args, **kwargs):
        self.login = login
        self.password = password
        super(InstagramSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        try:
            js_data = self.js_data_extract(response)
            yield scrapy.FormRequest(
                self.login_url,
                method='POST',
                callback=self.parse,
                formdata={
                    'username': self.login,
                    'enc_password': self.password,
                },
                headers={'X-CSRFToken': js_data['config']['csrf_token']}
            )
        except AttributeError as e:
            if response.json().get('authenticated'):
                for tag in self.tag_list:
                    yield response.follow(f'/explore/tags/{tag}', callback=self.tag_parse)

    def js_data_extract(self, response):
        script = response.xpath('//script[contains(text(), "window._sharedData = ")]/text()').get()
        return json.loads(script.replace('window._sharedData = ', '')[:-1])

    def tag_parse(self, response):
        data = self.js_data_extract(response)
        graphql = data['entry_data']['TagPage'][0]['graphql']

        hashtag_instagram_id = graphql['hashtag']['id']
        hashtag_name = graphql['hashtag']['name']
        hashtag_profile_pic_url = graphql['hashtag']['profile_pic_url']
        item = InstagramTagItem(
            instagram_id=hashtag_instagram_id,
            name=hashtag_name,
            picture_url=hashtag_profile_pic_url,
        )
        yield item

        yield from self.instagram_posts_page_parse(response)

    def instagram_posts_page_parse(self, response):
        try:
            data = self.js_data_extract(response)
            graphql = data['entry_data']['TagPage'][0]['graphql']
        except AttributeError as e:
            data = json.loads(response.text)
            graphql = data['data']

        hashtag_name = graphql['hashtag']['name']
        edge_hashtag_to_media = graphql['hashtag']['edge_hashtag_to_media']
        edges = edge_hashtag_to_media['edges']
        for el in edges:
            node = el['node']
            display_url = node['display_url']
            item_post = InstagramPostItem(
                data=node,
                picture_url=display_url,
                date_parse=dt.now(),
            )
            yield item_post

        page_info = edge_hashtag_to_media['page_info']
        if page_info['has_next_page']:
            end_cursor = page_info['end_cursor']
            url_begin = 'https://www.instagram.com/graphql/query/?'
            param_query_hash = f'query_hash={self.query_hash["tag_paginate"]}'
            var_tag_name = f'"tag_name"%3A"{hashtag_name}"'
            var_first = f'"first"%3A100'
            var_after = f'"after"%3A"{end_cursor}"'
            url = f'{url_begin}{param_query_hash}&variables=%7B{var_tag_name},{var_first},{var_after}%7D'
            yield response.follow(url, callback=self.instagram_posts_page_parse)

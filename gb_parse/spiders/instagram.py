
# 2) scrapy settings: (чтобы паук шел с двух концов)
#     DEPTH_PRIORITY = 1
#     SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
#     SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'

import scrapy
import json
from json import JSONDecodeError
from datetime import datetime as dt
from ..items import InstagramTagItem, InstagramPostItem, InstagramUserItem, InstagramUserFollowingItem, \
    InstagramUserFollowedByItem
from collections import defaultdict
from anytree import Node, RenderTree, LevelOrderIter, find_by_attr
from scrapy.exceptions import CloseSpider


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    allowed_domains = ['www.instagram.com']
    start_urls = ['https://www.instagram.com/']
    query_hash = {
        'tag_paginate': '9b498c08113f1e09617a1703c22b2f32',
        'edge_follow': 'd04b0a864b4b54837c0d870b0e77e076',
        'edge_followed_by': 'c76146de99bb02f6415203be841dd25a',
    }
    user_list = [
        'nevzorov_junior',
        'volky_volky',
    ]
    friends = defaultdict(lambda: defaultdict(set))
    tree = {0: {}, 1: {}}

    def __init__(self, login, password, *args, **kwargs):
        self.login = login
        self.password = password
        super(InstagramSpider, self).__init__(*args, **kwargs)

    def parse(self, response, **kwargs):
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
                for idx, user in enumerate(self.user_list):
                    yield response.follow(f'/{user}/', callback=self.user_parse, cb_kwargs={'tree_id': idx})

    @staticmethod
    def js_data_extract(response):
        script = response.xpath('//script[contains(text(), "window._sharedData = ")]/text()').get()
        return json.loads(script.replace('window._sharedData = ', '')[:-1])

    @staticmethod
    def url_get(user_id, query_hash, end_cursor=None):
        url_begin = 'https://www.instagram.com/graphql/query/?'
        param_query_hash = f'query_hash={query_hash}'
        variables = {
            'id': user_id,
            'first': 100,
        }
        if end_cursor is not None:
            variables['after'] = end_cursor

        return f'{url_begin}{param_query_hash}&variables={json.dumps(variables)}'

    def user_parse(self, response, tree_id):
        try:
            data = self.js_data_extract(response)
        except ValueError:
            raise CloseSpider('cannot decode json. closing spider')

        user_data = data['entry_data']['ProfilePage'][0]['graphql']['user']
        user_id = user_data['id']

        self.friends[user_id]['username'] = user_data['username']
        self.tree[tree_id][user_id] = Node(user_id)
        self.friends[f'root_node_{tree_id}'] = self.tree[tree_id][user_id]

        yield response.follow(self.url_get(user_id, self.query_hash['edge_follow'], end_cursor=None),
                              callback=self.get_mutual_friends,
                              cb_kwargs={'user_id': user_id,
                                         'follow_type': 'edge_follow',
                                         'tree_id': tree_id})

        yield response.follow(self.url_get(user_id, self.query_hash['edge_followed_by'], end_cursor=None),
                              callback=self.get_mutual_friends,
                              cb_kwargs={'user_id': user_id,
                                         'follow_type': 'edge_followed_by',
                                         'tree_id': tree_id})

    def get_mutual_friends(self, response, user_id, follow_type, tree_id):
        try:
            data = response.json()
        except JSONDecodeError:
            raise CloseSpider('cannot decode json. closing spider')

        self.friends[user_id][f'{follow_type}_count'] = data['data']['user'][follow_type]['count']

        page_info = data['data']['user'][follow_type]['page_info']
        if page_info['has_next_page']:
            yield response.follow(self.url_get(user_id,
                                               self.query_hash[follow_type],
                                               end_cursor=page_info['end_cursor']),
                                  callback=self.get_mutual_friends,
                                  cb_kwargs={'user_id': user_id,
                                             'follow_type': follow_type,
                                             'tree_id': tree_id})

        for el in data['data']['user'][follow_type]['edges']:
            self.friends[user_id][follow_type].add(el['node']['id'])
            self.friends[el['node']['id']]['username'] = el['node']['username']

        followed_by_fetched = (len(self.friends[user_id]['edge_followed_by']) ==
                               self.friends[user_id]['edge_followed_by_count'])
        follow_fetched = (len(self.friends[user_id]['edge_follow']) ==
                          self.friends[user_id]['edge_follow_count'])
        if followed_by_fetched and follow_fetched:
            mutual_friends = set.intersection(self.friends[user_id]['edge_follow'],
                                              self.friends[user_id]['edge_followed_by'])
            for u_id in mutual_friends:
                if u_id not in self.tree[tree_id].keys():
                    self.tree[tree_id][u_id] = Node(u_id, parent=self.tree[tree_id][user_id])
                    self.find_user()
                    yield response.follow(self.url_get(u_id, self.query_hash['edge_follow'], end_cursor=None),
                                          callback=self.get_mutual_friends,
                                          cb_kwargs={'user_id': u_id,
                                                     'follow_type': 'edge_follow',
                                                     'tree_id': tree_id})

                    yield response.follow(self.url_get(u_id, self.query_hash['edge_followed_by'], end_cursor=None),
                                          callback=self.get_mutual_friends,
                                          cb_kwargs={'user_id': u_id,
                                                     'follow_type': 'edge_followed_by',
                                                     'tree_id': tree_id})

    def find_user(self):
        for node in LevelOrderIter(self.friends['root_node_0']):
            tree_1_node = find_by_attr(self.friends['root_node_1'], node.name)
            if tree_1_node is not None:
                part_0 = [inode.name for inode in node.path]
                part_1 = [inode.name for inode in self.tree[1][tree_1_node.name].iter_path_reverse() if
                          inode.name != node.name]
                id_path = part_0 + part_1
                print('Found!')
                print('ID path:')
                print('->'.join([uid for uid in id_path]))
                print('username path:')
                print(' -> '.join([str(self.friends[uid]['username']) for uid in id_path]))
                print(f'link length: {len(id_path)}')
                raise CloseSpider('closing spider')

    def print_tree(self, tree_id):
        print(RenderTree(self.friends[f'root_node_{tree_id}']))("Que is empty. Can't find connection between users")
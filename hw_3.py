from typing import Tuple, Set
import bs4
import requests
from urllib.parse import urljoin
from database.db import Database


class GbBlogParse:

    def __init__(self, start_url, database: Database):
        self.db = database
        self.start_url = start_url
        self.page_done = set()

    def _get(self, url):
        response = requests.get(url)
        self.page_done.add(url)
        return bs4.BeautifulSoup(response.text, 'lxml')

    def run(self, url=None):
        if not url:
            url = self.start_url

        if url not in self.page_done:
            soup = self._get(url)
            posts, pagination = self.parse(soup)
            for post_url in posts:
                page_data = self.page_parse(self._get(post_url), post_url)
                self.save(page_data)

            for pag_url in pagination:
                self.run(pag_url)

    def parse(self, soup) -> Tuple[Set[str], Set[str]]:
        pag_ul = soup.find('ul', attrs={'class': 'gb__pagination'})
        paginations = set(
            urljoin(self.start_url, p_url.get('href')) for p_url in pag_ul.find_all('a') if p_url.get('href')
        )
        posts_wrapper = soup.find('div', attrs={'class': 'post-items-wrapper'})

        posts = set(
            urljoin(self.start_url, post_url.get('href')) for post_url in
            posts_wrapper.find_all('a', attrs={'class': 'post-item__title'})
        )

        return posts, paginations

    def page_parse(self, soup, url) -> dict:
        return {
            'post': {
                'url': url,
                'title': soup.find('h1', attrs={'class': 'blogpost-title'}).text,
                'date': soup.find('div', attrs={'class': 'blogpost-date-views'}).find('time').get('datetime'),
                'image': soup.find('div', attrs={'class': 'blogpost-content'}).find('img').get('src') if soup.find(
                    'div', attrs={'class': 'blogpost-content'}).find('img') else 0,
            },
            'writer': {
                'name': soup.find('div', attrs={'itemprop': 'author'}).text,
                'url': urljoin(self.start_url, soup.find('div', attrs={'itemprop': 'author'}).parent.get('href'))
            },
            'tags':
                self.get_tags(soup),
            'comments':
                self.get_comments(requests.get(
                    f'https://geekbrains.ru/api/v2/comments?commentable_type=Post&commentable_id='
                    f'{soup.find("comments").get("commentable-id")}'
                    f'&order=desc').json())
        }

    def get_tags(self, soup):
        result = []
        tags_data = soup.find_all('a', attrs={'class': "small"})
        for tag_data in tags_data:
            result.append({'name': tag_data.text,
                           'url': urljoin(self.start_url, tag_data.get('href')),
                           })

        return result

    def get_comments(self, comments):
        result = []
        for el in comments:
            comment = el['comment']
            result.append({'author': comment['user']['full_name'],
                           'comment': comment['body'],
                           })
            children = comment['children']
            if len(children) > 0:
                result.extend(self.get_comments(children))

        return result

    def save(self, post_data: dict):
        self.db.create_post(post_data)


if __name__ == '__main__':
    database = Database("sqlite:///gb_blog.db")
    parser = GbBlogParse("https://geekbrains.ru/posts", database)
    parser.run()

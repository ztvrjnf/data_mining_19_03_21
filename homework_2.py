import requests
from urllib.parse import urljoin
import bs4
import pymongo
import datetime
import time

months_dict = {
    'января': 1,
    'февраля': 2,
    'марта': 3,
    'апреля': 4,
    'мая': 5,
    'июня': 6,
    'июля': 7,
    'августа': 8,
    'сентября': 9,
    'октября': 10,
    'ноября': 11,
    'декабря': 12,
}


class MagnitParse:

    def __init__(self, start_url, db_client):
        self.start_url = start_url
        self.db = db_client['gb_data_mining_2021_02_26']

    def get_response(self, url, *args, **kwargs):
        for _ in range(15):
            response = requests.get(url, *args, **kwargs)
            if response.status_code == 200:
                return response
            time.sleep(1)
        raise ValueError("URL NOT ALIVE")

    def _get_soup(self, url, *args, **kwargs) -> bs4.BeautifulSoup:
        soup = bs4.BeautifulSoup(self.get_response(url, *args, **kwargs).text, "lxml")
        return soup

    def _template(self):
        return {
            'url': lambda a: str(urljoin(self.start_url, a.attrs.get('href'))),
            'promo_name': lambda a: str(a.find('div', attrs={'class': 'card-sale__name'}).text),
            'product_name': lambda a: str(a.find('div', attrs={'class': 'card-sale__title'}).text),
            'old_price': lambda a: float(
                a.find('div', attrs={'class': 'label__price label__price_old'}).find('span', attrs={'class',
                'label__price-integer'}).text +
                '.' +
                a.find('div', attrs={'class': 'label__price label__price_old'}).find('span', attrs={'class',
                'label__price-integer'}).text),
                'new_price': lambda a: float(
                a.find('div', attrs={'class': 'label__price label__price_new'}).find('span', attrs={'class',
                'label__price-integer'}).text +
                '.' +
                a.find('div', attrs={'class': 'label__price label__price_new'}).find('span', attrs={'class',
                'label__price-integer'}).text),
            'image_url': lambda a: str(urljoin(self.start_url, a.find("source").attrs.get("data-srcset"))),
            'date_from': lambda a: self.to_datetime(
                a.find('div', attrs={'class': 'card-sale__date'}).text.split()[0:3]),
            'date_to': lambda a: self.to_datetime(a.find('div', attrs={'class': 'card-sale__date'}).text.split()[3:6]),
        }

    def to_datetime(self, date_list):
        return datetime.datetime(
            year=datetime.datetime.now().year,
            day=int(date_list[1]),
            month=months_dict[date_list[2]],
        )

    def run(self):
        soup = self._get_soup(self.start_url)
        catalog = soup.find("div", attrs={"class": "сatalogue__main"})
        for product_a in catalog.find_all('a', recursive=False):
            product_data = self._parse(product_a)
            self.save(product_data)

    def _parse(self, product_a: bs4.Tag):
        product_data = {}
        for key, func in self._template().items():
            try:
                product_data[key] = func(product_a)
            except AttributeError:
                pass
            except ValueError:
                pass
            except IndexError:
                pass

        return product_data

    def save(self, data: dict):
        collection = self.db['magnit']
        collection.insert_one(data)


if __name__ == '__main__':
    url = 'https://magnit.ru/promo/?geo=moskva'
    db_client = pymongo.MongoClient()
    parser = MagnitParse(url, db_client)
    parser.run()
    print('done')
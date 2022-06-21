import scrapy
import re
from datetime import datetime, timedelta


class RealiticaSpider(scrapy.Spider):
    name = 'realitica'
    allowed_domains = ['realitica.com']

    # any url specified in this file will be skipped
    excluded_urls_file = 'excluded_urls.txt'

    # list of start urls
    start_urls = [
        'https://www.realitica.com/?cur_page=1&for=DuziNajam&opa=Podgorica&type%5B%5D=Apartment&price-min=330&price-max=600&lng=hr',
    ]

    # item will be skipped if description contains at least one word (case insensitive)
    blacklist = [
        'nenamješten', 'nenamjesten',
    ]

    # item will be skipped if description DOESN'T contain at least one word (case insensitive)
    search_phrases = [
        '2 sobe', '3 sobe', 'dvosoban', 'trosoban'
    ]

    def is_url_excluded(self, url):
        with open(self.excluded_urls_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if line.strip() == url.strip():
                    return True

        return False

    def contains_required_phrase(self, html):
        html = html.lower()
        for phrase in self.search_phrases:
            if phrase.lower() in html:
                return True

        return False

    def contains_blacklist_words(self, html):
        html = html.lower()

        for word in self.blacklist:
            if word.lower() in html:
                return True

        return False

    def parse(self, response, **kwargs):
        for el in response.xpath('//*[@id="left_column_holder"]/div/div[3]'):
            if not self.contains_required_phrase(el.get()) or \
                    self.contains_blacklist_words(el.get()) or \
                    self.is_url_excluded(el.xpath('a/@href').get()):
                continue

            yield response.follow(el.xpath('a/@href').get(), callback=self.parse_item)

        next_page = response.css('.bt_pages')[-1].xpath('@href').get()
        if next_page is not None and 'cur_page=100&' not in next_page:
            yield response.follow(next_page, callback=self.parse)

    def get_updated_at(self, html):
        # <strong>Zadnja Promjena</strong>: 3 Feb, 2022
        match = re.search("<strong>Zadnja Promjena</strong>: (\d+ \w+, \d+)", html)
        return datetime.strptime(match.group(1), '%d %b, %Y') if match else None

    def is_new(self, html):
        updated_at = self.get_updated_at(html)
        return updated_at >= datetime.now() - timedelta(days=30) if updated_at else False

    def get_location(self, html):
        match = re.search("<strong>Lokacija</strong>: (.*?)<br />", html)
        return None if match is None else match.group(1)

    def get_price(self, html):
        # <strong>Cijena</strong>: &euro;400<br />
        match = re.search("<strong>Cijena</strong>: .*?(\d+)<br />", html)
        return match.group(1) + ' EUR' if match else None

    def clean_description(self, description):
        return description\
            .replace("<br />", '')\
            .replace("\r\n", '') \
            .replace("\n", '') \
            .replace('<!-- margin left needed because left div collapses when empty -->', '')

    def get_description(self, html):
        # <strong>Opis</strong>
        match = re.search("<strong>Opis</strong>: (.*?)<div id=\"aboutAuthor\">", html, re.DOTALL)
        return self.clean_description(match.group(1)) if match else None

    def parse_item(self, response):
        if not self.is_new(response.text) or self.contains_blacklist_words(response.text):
            return

        updated_at = self.get_updated_at(response.text)

        yield {
            'url': response.request.url,
            'location': self.get_location(response.text),
            'price': self.get_price(response.text),
            'updated_at': updated_at.strftime('%Y-%m-%d %H:%M:%S') if updated_at else None,
            'title': response.css('h2::text').get(),
            'description': self.get_description(response.text),
        }

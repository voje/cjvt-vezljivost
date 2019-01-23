# Deprecated!

import requests
from bs4 import BeautifulSoup
from time import time
from valency import k_utils

SSKJ_BASE = "http://bos.zrc-sazu.si/cgi/a03.exe?name=sskj_testa&expression="


class SskjScraper:
    def __init__(self):
        self.base_url = SSKJ_BASE

    def scrape(self, word):
        # returns unique set of words
        soup = BeautifulSoup(
            requests.get(self.base_url + word).content,
            "html.parser"
        )
        # Check for failure.
        h2 = soup.find_all("h2")
        if len(h2) >= 2:
            # <h2>Zadetkov ni bilo: ...</h2>
            return []
        li_elements = soup.find_all('li', class_="nounderline")
        if len(li_elements) == 0:
            return []
        li = li_elements[0]
        # It was horrible...
        # <li> ... <li> ... <li> ...</li></li></li>
        # Parse sequence until you find a sedond <li>
        txts = []
        for el in li.find_all():
            if el.name == "li":
                break
            txts.append(el.get_text())
        print("sskj scraped {}.".format(word))
        return k_utils.tokenize(txts)


if __name__ == "__main__":
    sskjScr = SskjScraper()

    word = "tek"
    tp = sskjScr.scrape("čaj")
    print(tp)

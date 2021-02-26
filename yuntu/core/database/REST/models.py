from abc import ABC
from abc import abstractmethod

class as_object:
    def __init__(self, datum):
        for key in datum:
            setattr(self, key, datum["key"])

    def to_dict(self):
        return self.__dict__

class RESTModel(ABC):

    def __init__(self, target_url, target_attr="results", page_size=1, auth=None):
        self.target_url = target_url
        self.target_attr = target_attr
        self._auth = auth
        self._page_size = page_size

    @property
    def page_size(self):
        return self._page_size

    @property
    def auth(self):
        return self._auth

    def set_page_size(self, page_size):
        self._page_size = page_size

    def set_auth(self, auth):
        self._auth = auth

    def select(self, query=None, limit=None, offset=None):
        """Request results and return"""
        # Add limits to request and traverse pages
        count = 0
        for page in self.iter_pages(query, limit, offset):
            meta_arr = []
            meta_arr = page[self.target_attr]
            for meta in meta_arr:
                if count < limit:
                    parsed = self.parse(meta)
                    count += 1
                    yield as_object(parsed)
                else:
                    break

    @abstractmethod
    def iter_pages(self, query=None, limit=None, offset=None):
        """Iterate rest pages and return json response"""

    @abstractmethod
    def count(self, query=None):
        """Request results count"""

    @abstractmethod
    def parse(self, datum):
        """Parse incoming data to a common format"""
try:
    from ruamel.yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from ruamel.yaml import Loader, Dumper
from ruamel.yaml import YAML

class YAMLParserFactory:
    def __init__(self):
        pass

    def create_parser(self):
        return YAMLParser()

class YAMLParser(YAML):

    def __init__(self):
        self.data = []
        super(YAMLParser, self).__init__(typ="safe")
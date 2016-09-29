# Standard library
from logging import getLogger
from os import path
from sys import modules
# Third party library
from tornado import template, gen
# Local library
from warehouse.server import config


class BaseModule:
    db = None
    ws = None
    title = None
    log = getLogger(__name__)
    try:
        super_js = open(__file__.replace(".py", ".js")).read()
    except FileNotFoundError:
        raise NotImplementedError(str(path.split(__file__.replace(".py", ".js"))[-1]) + " does not exist. This javascript file is essential to the program, and the program will now exit.")
    sub_js = {}

    @gen.coroutine
    def __init__(self, db_instance, websocket):
        self.db = db_instance
        self.ws = websocket
        self.templates = template.Loader(path.join(config.BASE_DIR, "modules", self.__class__.__name__.lower(), "templates"))
        yield self.db.async_query("update_user_data", "last", self.__class__.__name__, self.ws.current_user, module=self)

    def process_request(self, message):
        raise NotImplementedError("process_request was not implemented in sub module: " + self.__class__.__name__)

    def send_data(self, data):
        self.ws.send_data(data)

    def send_raw_msg(self, msg):
        self.ws.send_msg(msg)

    def display_msg(self, message, msg_type, debug_info=""):
        self.ws.display_msg(message, msg_type, debug_info=debug_info)

    @classmethod
    def get_javascript(cls):
        if cls.__name__ in BaseModule.sub_js:
            final_javascript = BaseModule.sub_js[cls.__name__]
            cls.log.debug("Sub javascript loaded from dict")
        else:
            final_javascript = BaseModule.super_js.replace("//<module_name>", cls.__name__, 1)
            try:
                sub_javascript = open(modules[cls.__module__].__file__.replace(".py", ".js")).read()
                cls.log.debug("Sub javascript file loaded: " + modules[cls.__module__].__file__.replace(".py", ".js"))
            except FileNotFoundError:
                cls.log.debug("Silently ignored missing sub javascript file: " + modules[cls.__module__].__file__.replace(".py", ".js"))
            except Exception as e:
                cls.log.exception(e)
            else:
                final_javascript = final_javascript.replace("//<module_code>", sub_javascript, 1)
            BaseModule.sub_js[cls.__name__] = final_javascript

        return final_javascript

    @classmethod
    def get_title(cls):
        if cls.title is None:
            raise NotImplementedError("`title` variable was not set in sub module: " + cls.__name__)
        return cls.title

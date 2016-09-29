# Standard library
# Third party library
from tornado import web
# Local library


class MaslineStatic(web.StaticFileHandler):
    def set_extra_headers(self, _):
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')

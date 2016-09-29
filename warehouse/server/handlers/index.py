# Standard library
from logging import getLogger
# Third party library
from tornado import web
# Local library
from warehouse.server.config.globals import M
from warehouse.server.util import decode_cookie, is_authentic_connection


class MaslineApp(web.RequestHandler):

    def initialize(self):
        self.log = getLogger(__name__)
        self.extra = {"ip": self.request.remote_ip, "user": self.current_user}

    def get_current_user(self):
        uuid_dict = M.users.get(self)
        if uuid_dict is None or "username" not in uuid_dict or uuid_dict["username"] == "":
            return None
        else:
            return uuid_dict["username"]

    def get(self, *args, **kwargs):
        self.log.info("User connected", extra=self.extra)
        uuid = decode_cookie(self)
        self.log.debug("Cookie decoded, {0}".format(uuid), extra=self.extra)
        handoff = M.websocket_handoff.get(uuid, None)
        if handoff is None:
            self.log.warning("UUID is not found in handoff. Redirecting to login", extra=self.extra)
            self.redirect("/login")
        elif not is_authentic_connection(self, handoff):
            self.log.warning("Non-authenticated index page request. Redirecting to login", extra=self.extra)
            M.websocket_handoff.pop(uuid, None)
            self.redirect("/login")
        else:
            menu_dict = {}
            try:
                for mod in handoff["authorized"]:
                    menu_dict[mod] = M.mods[mod].get_title()
                self.log.debug("Loaded modules into menu, {0}".format(str(menu_dict)), extra=self.extra)
            except NotImplementedError:
                self.log.exception("Error loading modules for user", extra=self.extra)
                M.websocket_handoff.pop(uuid, None)
                self.redirect("/login?msg=Error%20Loading%20Modules")
                self.log.debug("Redirecting to login", extra=self.extra)
            else:
                self.render("masline.html", icon_type=M.icon_type, menu_dict=sorted(menu_dict.items(), key=lambda x: x[1]))
                self.log.debug("Index page rendered", extra=self.extra)

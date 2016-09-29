# Standard library
from datetime import datetime
from logging import getLogger
from uuid import uuid1
# Third party library
from tornado import web, gen
# Local library
from warehouse.server.config.globals import M
from warehouse.server.util import decode_cookie


class MaslineLogin(web.RequestHandler):

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
        if uuid in M.websocket_handoff.keys() and M.websocket_handoff[uuid]["authorized"] is not None and M.websocket_handoff[uuid]["username"] is not None:
            self.redirect("/")
            self.log.debug("Redirecting to index because user already has websocket connection", extra=self.extra)
        else:
            M.websocket_handoff.pop(uuid, None)
            self.clear_all_cookies()
            self.render("login.html", icon_type=M.icon_type, err_msg=self.get_argument("msg", None))
            self.log.debug("Login page rendered with 'msg', {0!s}".format(self.get_argument("msg", None)), extra=self.extra)

    @gen.coroutine
    def post(self, *args, **kwargs):
        badge_id = self.get_argument("badge-id", None)
        self.log.info("User sent {0}".format(badge_id), extra=self.extra)
        if badge_id is None:
            self.set_status(400, "No data received.")
            self.log.debug("Post request sent without 'badge-id'", extra=self.extra)
        else:
            username_dict = yield M.db.async_query("get_user_name", badge_id)
            username = username_dict['response']
            if username == "":
                self.set_status(401, "Access Denied")
                self.log.debug("Badge-id not found in database", extra=self.extra)
                return
            self.log.debug("User, {0}, found".format(username), extra=self.extra)
            authorized_mods_dict = yield M.db.async_query("get_user_data", "mods", username)
            authorized_mods = authorized_mods_dict["response"].replace(" ", "").split(",")
            if len(authorized_mods) == 1 and authorized_mods[0] == "":
                self.set_status(401, "No Modules Available")
                self.log.debug("User does not have any modules assigned", extra=self.extra)
                return
            self.log.debug("User has {0} modules assigned: {1}".format(len(authorized_mods), str(authorized_mods)), extra=self.extra)
            uuid = str(uuid1())
            M.websocket_handoff[uuid] = M.user_sub.copy()
            M.websocket_handoff[uuid]["username"] = username
            M.websocket_handoff[uuid]["authorized"] = authorized_mods
            M.websocket_handoff[uuid]["timestamp"] = datetime.now()
            M.websocket_handoff[uuid]["originating"] = self.request.remote_ip
            self.set_secure_cookie("session", uuid, expires_days=1)
            self.log.debug("Secure cookie set, {0}, javascript is handling the redirect to index".format(uuid), extra=self.extra)

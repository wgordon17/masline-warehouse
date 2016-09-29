# Standard library
from json import loads
from logging import getLogger
# Third party library
from tornado import websocket, gen
# Local library
from warehouse.server.config.globals import M
from warehouse.server import config
from warehouse.server.util import decode_cookie, is_authentic_connection


class MaslineSocket(websocket.WebSocketHandler):

    def initialize(self):
        self.log = getLogger(__name__)
        self.extra = {"ip": self.request.remote_ip, "user": self.current_user}

    def get_current_user(self):
        uuid_dict = M.users.get(self)
        if uuid_dict is None or "username" not in uuid_dict or uuid_dict["username"] == "":
            return None
        else:
            return uuid_dict["username"]

    def send_data(self, data):
        self.send_msg({"action": "module", "data": data})

    def display_msg(self, message, msg_type, debug_info=""):
        self.send_msg({"action": "message", "data": {"type": msg_type,
                                                     "message": message,
                                                     "buttons": "Ok",
                                                     "debug-log": debug_info}}, debug_info)

    def send_msg(self, message, log_info=None):
        # This is intended as a wrapper around the web_socket.write_message() method in order to ensure all
        # information sent is a Dictionary so that it is parsed as JSON
        if not isinstance(message, dict) or "action" not in message or "data" not in message or not isinstance(message["data"], dict):
            self.send_msg({"action": "message", "data": {"type": "error",
                                                         "message": "The server is incorrectly sending malformed data",
                                                         "buttons": "Ok",
                                                         "debug-log": str(message)}}, message)
        else:
            if message["action"] == "message" and message["data"]["type"] == "error":
                log_info = "; " + str(log_info) if log_info else ""
                if "unauthorized" in message["data"]["message"].lower():
                    self.log.warning("{0!s} {1!s}".format(message["data"]["message"], log_info), extra=self.extra)
                else:
                    self.log.error("{0!s} {1!s}".format(message["data"]["message"], log_info), extra=self.extra)
            if "module-js" in message["data"] and not config.DEBUG:
                message["data"]["module-js"] = message["data"]["module-js"].replace("\t", "").replace("\n", "")
            elif "module-html" in message["data"] and not config.DEBUG:
                message["data"]["module-html"] = message["data"]["module-html"].replace("\t", "").replace("\n", "")
            if message["action"] == "message" and "debug-log" in message["data"]:
                message["data"]["debug-log"] = str(message["data"]["debug-log"])
            self.write_message(message)

    def open(self):
        self.log.info("Initiating websocket connection", extra=self.extra)
        ws_handoff = M.websocket_handoff.pop(decode_cookie(self), None)
        if ws_handoff is None:
            self.log.warning("UUID is not found in handoff. Refusing websocket connection", extra=self.extra)
            self.close(4001, "connection refused")
        elif not is_authentic_connection(self, ws_handoff):
            self.log.warning("Non-authenticated websocket request. Refusing websocket connection", extra=self.extra)
            self.close(4001, "connection refused")
        else:
            M.users[self] = ws_handoff
            self.set_nodelay(True)
            self.current_user = self.get_current_user()
            self.log.info("Socket connected", extra=self.extra)
            self.switch_to_last_module()

    def close(self, code=None, reason=None):
        # Overridden from Tornado to force calling on_close() when calling self.close()
        if code is None:
            code = 1011
        if reason is None and code == 1011:
            reason = M.ws_reasons[code]
        if self.ws_connection:
            self.on_close(True)
            self.close_code = code
            self.close_reason = reason
            self.ws_connection.close(code, reason)
            self.ws_connection = None

    def on_close(self, client_initiated=False):
        close_reason = M.ws_reasons[self.close_code] if self.close_reason is None else "{0!s} & {1!s}".format(self.close_reason, M.ws_reasons[self.close_code])
        self.log.info("Socket closed. Code: {0!s}; Reason: {1!s}".format(self.close_code, close_reason), extra=self.extra)
        M.users.pop(self, None)

    def on_message(self, message):
        message = loads(message)
        self.log.debug("Received websocket message: " + str(message), extra=self.extra)
        if not isinstance(message, dict) or "action" not in message or "data" not in message or not isinstance(message["data"], dict):
            self.send_msg({"action": "message", "data": {"type": "error",
                                                         "message": "The server received incorrectly formatted data.",
                                                         "buttons": "Ok",
                                                         "debug-log": message}}, message)
        else:
            msg_data = message["data"]
            if message["action"] == "kill":
                raise IOError("Big problem")
            if message["action"] == "request-module":
                if "module" in msg_data:
                    self.switch_module(msg_data["module"])
                    return
            elif message["action"] == "print":
                if "label" in msg_data and "value" in msg_data:
                    pass
                    return
            elif message["action"] == "module":
                if "action" in msg_data and "data" in msg_data and isinstance(msg_data["data"], dict):
                    self.process_request(msg_data)
                    return
            self.send_msg({"action": "message", "data": {"type": "error",
                                                         "message": "The server received an unknown action",
                                                         "buttons": "Ok",
                                                         "debug-log": message}}, message)

    def switch_module(self, module_name):
        try:
            curr_dict = M.users[self]
        except KeyError:
            self.log.debug("Closing socket; Socket not found in dictionary", extra=self.extra)
            self.close(4002, "connection not found")
        else:
            if module_name in curr_dict["authorized"]:
                old_module = curr_dict.get("module", None)
                # noinspection PyCallingNonCallable
                curr_dict["module"] = M.mods[module_name](M.db, self)
                try:
                    module_js = curr_dict["module"].get_javascript()
                except NotImplementedError as e:
                    curr_dict["module"] = old_module
                    self.send_msg({"action": "message", "data": {"type": "error",
                                                                 "message": "This module is not fully implemented",
                                                                 "buttons": "Ok",
                                                                 "debug-log": e}}, e)
                else:
                    self.send_msg({"action": "switch-module", "data": {"module-js": module_js}})
            else:
                self.send_msg({"action": "message", "data": {"type": "error",
                                                             "message": "Unauthorized module: '" + str(module_name) + "'. This has been logged",
                                                             "buttons": "Ok"}})

    def process_request(self, message):
        try:
            curr_dict = M.users[self]
        except KeyError:
            self.log.debug("Closing socket; Socket not found in dictionary", extra=self.extra)
            self.close(4002, "connection not found")
        else:
            curr_module = curr_dict["module"]
            if curr_module is None:
                self.switch_to_last_module()
            else:
                try:
                    curr_module.process_request(message)
                except NotImplementedError as e:
                    self.send_msg({"action": "message", "data": {"type": "error",
                                                                 "message": "This module is not fully implemented",
                                                                 "buttons": "Ok",
                                                                 "debug-log": e}}, e)

    @gen.coroutine
    def switch_to_last_module(self):
        try:
            curr_dict = M.users[self]
        except KeyError:
            self.log.debug("Closing socket; Socket not found in dictionary", extra=self.extra)
            self.close(4002, "connection not found")
        else:
            last_mod_dict = yield M.db.async_query("get_user_data", "last", self.current_user, module=self)
            last_mod = last_mod_dict["response"]
            if last_mod == "":
                last_mod = curr_dict["authorized"][0]
                yield M.db.async_query("insert_user_data", "last", last_mod, self.current_user, module=self)
                yield M.db.async_query("update_user_data", "last", last_mod, self.current_user, module=self)
            last_data = last_mod.replace(" ", "").split(",", maxsplit=2)
            last_dict = dict(zip(["module", "action", "data"], last_data))
            self.switch_module(last_dict["module"])

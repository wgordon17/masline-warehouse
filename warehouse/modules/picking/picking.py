# Standard library
from itertools import chain
# Third party library
from tornado import gen
# Local library
from ..base import BaseModule
from warehouse.server.config.globals import M


class Picking(BaseModule):
    # Class required variables
    # Used for identifying the class as a whole or for module specific information
    title = "Pick Shipment"

    # Instance specific variables
    # Used for keeping information saved as well as allowing for others to see what current modules are doing
    curr_ship_no = None
    lot_list = []

    # Workflow indication variables
    waiting_for_qty = False
    waiting_for_type = False
    last_value = None

    def __init__(self, db_instance, websocket):
        super().__init__(db_instance, websocket)

    @gen.coroutine
    def process_request(self, message):
        self.log.debug("Processing module request: " + str(message))
        if not isinstance(message, dict) or "action" not in message or "data" not in message or not isinstance(message["data"], dict):
            self.display_msg("The module received incorrectly formatted data.", "error", message)
        else:
            yield self.db.async_query("update_user_data", "last",
                                      ",".join([self.__class__.__name__, message["action"]] + list(chain.from_iterable(zip(message["data"].keys(), message["data"].values())))),
                                      self.ws.current_user, module=self)
            msg_data = message["data"]
            if message["action"] == "question-response":
                if "response" in msg_data:
                    response = msg_data["response"]
                    if self.waiting_for_type and self.last_value is not None:
                        if response == "shipment":
                            self.process_request({"action": "ship-no", "data": {"ship-no": self.last_value}})
                        elif response == "lot":
                            self.process_request({"action": "lot-no", "data": {"lot-no": self.last_value}})
                        else:
                            self.display_msg("Unknown response.", "error", message)
                        self.waiting_for_type = False
                        self.last_value = None
                    elif self.waiting_for_qty and self.last_value is not None:
                        print('qty!: ' + str(response))
                    else:
                        self.display_msg("Server was not waiting for a response", "info")
                return
            elif message["action"] == "process-qty":
                if "qty" in msg_data:
                    qty = msg_data["qty"]
                    if self.waiting_for_qty and self.last_value is not None:
                        item_dict = yield self.db.async_query("get_item_no", self.last_value, module=self)
                        item, manu = item_dict["response"]
                        lines_dict = yield self.db.async_query("get_item_detail", item, manu, module=self)
                        lines = lines_dict["response"]
                        picked_line = [line for line in lines if line.lot_no == self.last_value][0]
                        yield self.db.async_query("insert_picked_lot", picked_line.location, self.last_value, self.curr_ship_no, picked_line.line, qty, self.ws.get_current_user(), module=self)
                        self.send_data({"action": "qty-received", "data": {"lot-no": self.last_value}})
                    return
            elif message["action"] == "reset-module":
                self.curr_ship_no = None
                self.lot_list = []
                self.waiting_for_qty = False
                self.waiting_for_type = False
                self.send_raw_msg({"action": "reset-module", "data": {}})
                return
            elif message["action"] == "unknown-value":
                if "value" in msg_data:
                    self.process_unknown(msg_data["value"])
                    return
            elif message["action"] == "ship-no":
                if "ship-no" in msg_data:
                    self.curr_ship_no = msg_data["ship-no"]
                    self.render_item_list()
                    return
            elif message["action"] == "lot-no":
                if "lot-no" in msg_data:
                    item_dict = yield self.db.async_query("get_item_no", msg_data["lot-no"], module=self)
                    item, manu = item_dict["response"]
                    # Ensure lot data is shown if not currently, before asking for qty confirmation
                    if not self.lot_list or msg_data["lot-no"] not in self.lot_list:
                        self.render_item_detail(item, manu)
                    else:
                        item_detail_dict = yield self.db.async_query("get_item_detail", item, manu, module=self)
                        item_detail = item_detail_dict["response"]
                        shipment_line = [line.line for line in item_detail if str(line.ship_no) == self.curr_ship_no and line.lot_no == msg_data["lot-no"]][0]
                        # Don't allow re-picking if already picked
                        is_lot_picked_dict = yield self.db.async_query("test_if_picked", self.curr_ship_no, shipment_line, msg_data["lot-no"], module=self)
                        if is_lot_picked_dict["response"]:
                            self.display_msg("Lot already picked. Please move on", "info", "scanned lot: " + str(msg_data["lot-no"]))
                            return
                        self.display_msg('Confirm qty picked', 'request_number')
                        self.waiting_for_qty = True
                        self.last_value = msg_data["lot-no"]
                    return
            elif message["action"] == "item-no":
                if "item-no" in msg_data and "manu-no" in msg_data:
                    self.render_item_detail(msg_data["item-no"], msg_data["manu-no"])
                    return
            self.display_msg("The module received an unknown action", "error", message)

    @gen.coroutine
    def render_item_list(self):
        self.lot_list = []
        if self.curr_ship_no is None:
            self.display_msg("No active shipment number", "error")
        else:
            item_list_dict = yield self.db.async_query("get_item_list", self.curr_ship_no, module=self)
            item_list = item_list_dict["response"]
            ship_note_dict = yield self.db.async_query("get_shipment_notes", self.curr_ship_no, module=self)
            ship_note = ship_note_dict["response"]
            self.send_data({"action": "load-data", "data": {"type": "ticket",
                "module-html": self.templates.load("picking-items.html").generate(item_list=item_list).decode("utf-8"),
                "data-title": self.curr_ship_no,
                "header-note": ship_note}})

    @gen.coroutine
    def render_item_detail(self, item_no, manu_no):
        lines_dict = yield self.db.async_query("get_item_detail", item_no, manu_no, module=self)
        lines = lines_dict["response"]
        imgs_dict = yield self.db.async_query("get_item_pic_urls", item_no, manu_no, module=self)
        item_imgs = imgs_dict["response"]
        self.lot_list = [ship_line.lot_no for ship_line in lines]
        if self.curr_ship_no is None:
            self.curr_ship_no = str(lines[0].ship_no)
        self.send_data({"action": "load-data", "data": {
            "type": "item",
            "module-html": self.templates.load("picking-lots.html").generate(lines=lines, item_imgs=item_imgs).decode("utf-8"),
            "data-title": item_no,
            "header-note": manu_no}})

    @gen.coroutine
    def process_unknown(self, unknown_value):
        self.log.debug("Processing unknown value: " + unknown_value)
        is_open_shipment_dict = yield self.db.async_query("test_if_shipment_open", unknown_value, module=self)
        is_open_shipment = is_open_shipment_dict["response"]
        is_lot_dict = yield self.db.async_query("test_if_lot", unknown_value, module=self)
        is_lot = is_lot_dict["response"]

        if is_open_shipment is True and is_lot is True:
            # Wait for user interaction
            self.ws.send_msg({"action": "message", "data": {"type": "ask", "message": "Unable to guess what you scanned. Help me out.", "buttons": ["Shipment", "Lot"]}})
            self.waiting_for_type = True
            self.last_value = unknown_value
        elif is_open_shipment is True:
            if not self.check_value_in_progress(unknown_value, "ship-no"):
                # Re-process with known value
                self.process_request({"action": "ship-no", "data": {"ship-no": unknown_value}})
        elif is_lot is True:
            if not self.check_value_in_progress(unknown_value, "lot-no"):
                # Re-process with known value
                self.process_request({"action": "lot-no", "data": {"lot-no": unknown_value}})
        else:
            # Check remaining domain, shipments other than printed and display appropriate message
            is_any_shipment_dict = yield self.db.async_query("test_if_shipment_any", unknown_value, module=self)
            is_any_shipment = is_any_shipment_dict["response"]
            if is_any_shipment:
                ship_status_dict = yield self.db.async_query("get_shipment_status", unknown_value, module=self)
                ship_status = ship_status_dict["response"]
                if ship_status == "Open":
                    self.display_msg("Shipment, " + unknown_value + ", is stuck 'Open'. Contact your system administrator", "error", unknown_value + "is 'Open'")
                elif ship_status == "Pulled" or ship_status == "Packed" or ship_status == "Shipped":
                    self.display_msg("Shipment, " + unknown_value + ", has already been picked fully and is being processed", "info")
                else:
                    self.display_msg("Shipment, " + unknown_value + ", is " + ship_status + " and cannot be picked", "info")
            else:
                # Nothing left to test, value is truly unknown
                self.display_msg("Unknown value scanned, try again.", "error", unknown_value)

    def get_current_ship_no(self):
        return self.curr_ship_no

    def get_current_lot_list(self):
        return self.lot_list

    def check_value_in_progress(self, value, val_type):
        for uuid, users in M.users.items():
            # Check for same module type
            if users["module"].get_title() == self.title:
                # Make sure not testing against self
                if not users["module"] == self:
                    # Compare values
                    if val_type == "ship-no":
                        if users["module"].get_current_ship_no() == value:
                            self.display_msg(users["username"] + ", is already working on this shipment", "info")
                            return True
                    elif val_type == "lot-no":
                        if value in users["module"].get_current_lot_list():
                            self.display_msg(users["username"] + ", is already working on this part number", "info")
                            return True
                    else:
                        self.display_msg("Unknown type comparison when checking if value is in progress", "error", type)
                        return True
        return False

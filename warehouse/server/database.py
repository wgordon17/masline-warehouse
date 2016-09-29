# Standard library
from concurrent.futures import ProcessPoolExecutor
from inspect import stack
from logging import getLogger
from platform import system
from sys import exc_info
import os
from urllib import parse
# Third party library
from pyodbc import connect, DatabaseError
from tornado import gen
# Local library
from warehouse.server import config

class DbManager:
    db_pool = None
    valid_user_data = ["MODS", "PASS", "LAST"]
    """ Valid Queries and their inputs and outputs
        + Denotes only for internal use

    test_if_shipment_any        ship_no                             bool(True/False)
    test_if_shipment_open       ship_no                             bool(True/False)
    test_if_lot                 lot_no                              bool(True/False)
    test_if_picked              ship_no, lin_no, lot_no             bool(True/False)
    get_user_name               unique_token                        str(user_name)
    get_user_data               data_id (exclude TAB_), user_id     str(data_value)
                                        Valid data_ids:
                                            PASS - Password
                                            MODS - Authorized modules (comma separated)
                                            LAST - The last module used, also contains last data (comma separated)
    get_item_list               ship_no                             list(item, manu, location, status)
    get_item_detail             item_no, manu_no                    list(ship_no, line, location, note, qty, lot_no, ship_status, line_status)
    get_item_hist               item_no, manu_no                    list(location)
    get_item_pic_urls           item_no, manu_no                    list(pic_url) (http://www.masline.com/sites/default/files/styles/medium/public/item_pics/___.JPG)
    get_item_no                 lot_no                              item, manu
    get_shipment_notes          ship_no                             str(whse_note) (\n chars stripped)
    get_alternate_lots          ship_no, lot_no                     list(line, lot_no, status)
    get_shipment_status         ship_no                             str(status)
    get_loc_int_id              location                            int(loc_int_id)

    insert_picked_wrong_lot     location, wrong_lot, correct_lot, ship_no, lin_no, qty, user_id
    insert_picked_lot           location, lot_no, ship_no, lin_no, qty, user_id
    +insert_all_lots_pulled     ship_no, user_id
    insert_user_data            data_id (exclude TAB_), data_value, user_id

    set_shipment_scanned        ship_no, user_id
    set_shipment_pulled         ship_no, user_id
    update_user_data            data_id (exclude TAB_), data_value, user_id
    """
    valid_queries = {
            ##################
            # SELECT queries #
            ##################

        "test_if_shipment_any":  # language="SQL server"
            """SELECT ship_no
                FROM shp_hedr
                WHERE ship_no = ?""",

        "test_if_shipment_open":  # language="SQL server"
            """SELECT ship_no
                FROM shp_hedr
                WHERE ship_no = ? AND (ship_status = 'P' OR ship_status = 'A')""",

        "test_if_lot":  # language="SQL server"
            """SELECT lot_no
                FROM lot_hedr
                WHERE lot_no = ?""",

        "test_if_picked":  # language="SQL server"
            """SELECT pc.description AS status
                FROM loc_trx
                LEFT JOIN create_proc_codes AS pc ON loc_trx.create_proc = pc.code
                WHERE ship_no = ? AND ship_lin_no = ? AND int_lot_no = ?""",

        "get_user_name":  # language="SQL server"
            """SELECT RTRIM(opr_id) AS user_name
                FROM opr_pref
                WHERE pref_id = 'TAB_PASS' AND pref_data = ?""",

        "get_user_data":  # language="SQL server"
            """SELECT pref_data AS data_value
                FROM opr_pref
                WHERE pref_id = 'TAB_' || ? AND opr_id = ?""",

        "get_item_list":  # language="SQL server"
            """SELECT RTRIM(sd.item_no) AS item, RTRIM(sd.manu_no) AS manu, s_list.loc_id AS location, RTRIM(IFNULL(create_proc_codes.description, '')) AS status
                FROM shp_detl AS sd
                    INNER JOIN (
                        SELECT lot_hedr.item_no, lot_hedr.manu_no, location.loc_id, loc_trx.create_proc
                        FROM shp_hedr
                            INNER JOIN shp_lot ON shp_hedr.ship_no = shp_lot.ship_no
                            INNER JOIN lot_hedr ON shp_lot.lot_no = lot_hedr.lot_no
                            INNER JOIN location ON lot_hedr.loc_int_id = location.loc_int_id
                            LEFT JOIN loc_trx ON shp_lot.ship_no = loc_trx.ship_no AND shp_lot.lin_no = loc_trx.ship_lin_no AND shp_lot.lot_no = loc_trx.int_lot_no
                        WHERE (shp_hedr.ship_status = 'P' OR shp_hedr.ship_status = 'A')
                        GROUP BY lot_hedr.item_no, lot_hedr.manu_no, location.loc_id, loc_trx.create_proc
                        ) as s_list ON sd.item_no = s_list.item_no AND sd.manu_no = s_list.manu_no
                    LEFT JOIN create_proc_codes ON s_list.create_proc = create_proc_codes.code
                WHERE sd.ship_no = ?
                ORDER BY sd.item_no, sd.manu_no""",

        "get_item_detail":  # language="SQL server"
            """SELECT sdetl.ship_no, sdetl.lin_no AS line, RTRIM(loc.loc_id) AS location, sdetl.od_ord_com AS note,
                    CASE slot.qty_to_shp WHEN 0 THEN slot.from_lot ELSE slot.qty_to_shp END AS qty,
                    RTRIM(slot.lot_no) AS lot_no, RTRIM(sstat.description) AS ship_status, RTRIM(IFNULL(pc.description, '')) AS line_status
                FROM shp_hedr AS shedr
                    INNER JOIN shp_status AS sstat ON shedr.ship_status = sstat.ship_status
                    INNER JOIN shp_detl AS sdetl ON shedr.ship_no = sdetl.ship_no
                    INNER JOIN shp_lot AS slot ON sdetl.ship_no = slot.ship_no AND sdetl.lin_no = slot.lin_no
                    INNER JOIN lot_hedr AS lot ON slot.lot_no = lot.lot_no
                    INNER JOIN location AS loc ON lot.loc_int_id = loc.loc_int_id
                    LEFT JOIN loc_trx AS trx ON sdetl.ship_no = trx.ship_no AND sdetl.lin_no = trx.ship_lin_no
                        AND slot.lot_no = trx.int_lot_no AND trx.loc_trx_int_id IN
                            (SELECT MAX(loc_trx_int_id)
                            FROM loc_trx
                            WHERE ship_no = sdetl.ship_no AND ship_lin_no = sdetl.lin_no AND int_lot_no = slot.lot_no)
                    LEFT JOIN create_proc_codes AS pc ON trx.create_proc = pc.code
                WHERE shedr.ship_status <> 'C' AND shedr.ship_status <> 'V' AND
                    sdetl.item_no = ? AND sdetl.manu_no = ?""",

        "get_item_hist":  # language="SQL Server"
            """exec item_loc_hist ?, ?""",

        "get_item_pic_urls":  # language="SQL Server"
            """SELECT RTRIM(item_pic2) AS picA, RTRIM(item_pic3) AS picB, RTRIM(item_pic4) AS picC
                FROM item
                WHERE item.item_no = ? AND item.manu_no = ?""",

        "get_item_no":  # language="SQL Server"
            """SELECT RTRIM(item_no) AS item, RTRIM(manu_no) AS manu
                FROM lot_hedr
                WHERE lot_no = ?""",

        "get_shipment_notes":  # language="SQL Server"
            """SELECT oh_ord_com AS whse_note
                FROM shp_hedr
                WHERE shp_hedr.ship_no = ?""",

        "get_alternate_lots":  # language="SQL server"
            """SELECT s.lin_no AS line, RTRIM(s.lot_no) AS lot_no, RTRIM(pc.description) AS status
                FROM lot_hedr AS l
                    INNER JOIN shp_detl AS shp ON l.item_no = shp.item_no AND l.manu_no = shp.manu_no
                    INNER JOIN shp_lot AS s ON shp.ship_no = s.ship_no AND shp.lin_no = s.lin_no
                    LEFT JOIN loc_trx AS trx ON shp.ship_no = trx.ship_no AND shp.lin_no = trx.ship_lin_no
                        AND s.lot_no = trx.int_lot_no AND trx.loc_trx_int_id IN
                            (SELECT MAX(loc_trx_int_id)
                            FROM loc_trx
                            WHERE ship_no = shp.ship_no AND ship_lin_no = shp.lin_no AND int_lot_no = s.lot_no)
                    LEFT JOIN create_proc_codes AS pc ON trx.create_proc = pc.code
                WHERE shp.ship_no = ? AND l.lot_no = ?""",

        "get_shipment_status":  # language="SQL server"
            """SELECT RTRIM(stat.description) AS status
                FROM shp_hedr AS shp
                    INNER JOIN shp_status AS stat ON shp.ship_status =  stat.ship_status
                WHERE shp.ship_no = ?""",

        "get_loc_int_id":  # language="SQL server"
            """SELECT loc_int_id
                FROM location
                WHERE loc_id = ?""",

            ##################
            # INSERT queries #
            ##################

        "insert_picked_wrong_lot":  # language="SQL server"
            """INSERT INTO loc_trx
                    (loc_int_id, create_dt, create_id, qty_from_loc, create_proc, int_lot_no, prg_id)
                VALUES (?, date('now'), ?, ?, 'D', ?, 'TAB_PICK')""",

        "insert_picked_lot":  # language="SQL server"
            """INSERT INTO loc_trx
                    (loc_int_id, create_dt, create_id, qty_from_loc, create_proc, int_lot_no, ship_no, ship_lin_no, prg_id)
                VALUES (?, date('now'), ?, ?, 'A', ?, ?, ?, 'TAB_PICK')""",

        "+insert_all_lots_pulled":  # language="SQL server"
            """INSERT INTO loc_trx
                    (loc_int_id, create_dt, create_id, qty_from_loc, create_proc, int_lot_no, ship_no, ship_lin_no, prg_id)
                SELECT l.loc_int_id, date('now'), ?, 0, 'U', s.lot_no, s.ship_no, s.lin_no, 'TAB_PICK'
                FROM shp_lot AS s
                    INNER JOIN lot_hedr AS l ON s.lot_no = l.lot_no
                WHERE s.ship_no = ?""",

        "insert_user_data":  # language="SQL server"
            """INSERT INTO opr_pref
                    (opr_id, pref_id, pref_data, create_dt, create_id, updt_dt, updt_id)
                VALUES (?, 'TAB_' + UPPER(?), ?, date('now'), 'TABLET', date('now'), 'TABLET')""",

            ##################
            # UPDATE queries #
            ##################

        "set_shipment_scanned":  # language="SQL server"
            """UPDATE shp_hedr
                SET ship_status = 'A', updt_id = ?, updt_dt = date('now')
                WHERE ship_no = ?""",

        "set_shipment_pulled":  # language="SQL server"
            """UPDATE shp_hedr
                SET ship_status = 'U', updt_id = ?, updt_dt = date('now')
                WHERE ship_no = ?""",

        "update_user_data":  # language="SQL server"
            """UPDATE opr_pref
                SET pref_data = ?, updt_dt = date('now'), updt_id = 'TABLET'
                WHERE opr_id = ? AND pref_id = 'TAB_' + UPPER(?)"""
    }

    def __init__(self, username, password, database, appname, num_db_processes=3):
        # ODBC Connection string used in production
        #self.conn_str = "DSN=epds;UID={0};PWD={1};DATABASE={2};APP={3}".format(username, password, database, appname)
        # ODBC Connection string for accessing local SQLite preview
        if system() == "Linux":
            self.conn_str = "DRIVER={{SQLite3}};SERVER=localhost;DATABASE={db}".format(db=os.path.join(config.BASE_DIR, "test.db"))
        elif system() == "Windows":
            self.conn_str = "DRIVER={{SQLite3 ODBC Driver}};SERVER=localhost;DATABASE{db}".format(db=os.path.join(config.BASE_DIR, "test.db"))
        DbManager.db_pool = ProcessPoolExecutor(max_workers=num_db_processes)

    def shutdown(self):
        DbManager.db_pool.shutdown(True)

    @gen.coroutine
    def async_query(self, *args, module=None):
        result = {"response": "", "args": ""}
        log = getLogger(__name__)
        pool_future = DbManager.db_pool.submit(self._init_query, args)
        try:
            result = yield pool_future
        except DatabaseError as e:
            if module is None:
                log.error(e)
            else:
                module.display_msg("Database error!", "error", debug_info=str(e))
        except Exception as e:
            log.exception(e)
        finally:
            return result

    def _init_query(self, args):
        if len(args) < 2:
            raise DatabaseError("Error in database.query: Not enough arguments in query_db:" + str(args))
        if args[0] not in self.valid_queries:
            raise DatabaseError("Error in database.query: Requested query is not a valid query:" + str(args[0]))
        query_name = args[0]
        query_args = args[1:]
        db_connection = connect(self.conn_str, autocommit=True)
        query = self.valid_queries[query_name]
        rows = getattr(self, "_" + query_name)(db_connection, query, *query_args)
        return {"response": rows, "args": query_args}

    def _exec_query(self, db_object, qry_str, args):
        rows = ""
        try:
            cursor = db_object.cursor()
            cursor.execute(qry_str, args)
        except Exception as e:
            raise DatabaseError(str(exc_info()[0].__name__) + " in database._exec_query: " + str(e) +
                                    "\n\t" + str(qry_str).replace("\n", " ").replace("\t", " ") + "\n\t" + str(args))
        else:
            if qry_str.split(" ", 1)[0].upper() in "SELECT":
                rows = cursor.fetchall()
            elif qry_str.split(" ", 1)[0].upper() in "EXEC":
                rows = True
                while rows and cursor.rowcount >= 0:
                    rows = cursor.nextset()
                if rows:
                    rows = cursor.fetchall()
            cursor.close()
        return rows

    def _test_if_shipment_any(self, db_connection, query_str, ship_no):
        rows = self._exec_query(db_connection, query_str, ship_no)
        if len(rows) > 0:
            return True

        return False

    def _test_if_shipment_open(self, db_connection, query_str, ship_no):
        rows = self._exec_query(db_connection, query_str, ship_no)
        if len(rows) > 0:
            return True

        return False

    def _test_if_lot(self, db_connection, query_str, lot_no):
        rows = self._exec_query(db_connection, query_str, lot_no)
        if len(rows) > 0:
            return True

        return False

    def _test_if_picked(self, db_connection, query_str, ship_no, lin_no, lot_no):
        rows = self._exec_query(db_connection, query_str, (ship_no, lin_no, lot_no))
        if len(rows) > 0:
            status = rows[0].status
            if status in ["Scanned", "Pulled", "Found"]:
                return True

            return False
        else:
            return False

    def _get_user_name(self, db_connection, query_str, unique_token):
        rows = self._exec_query(db_connection, query_str, unique_token)
        if len(rows) == 1:
            return rows[0].user_name

        if len(rows) == 0:
            raise DatabaseError("Error in database._get_user_name: No users found for token:" + str(unique_token))

        raise DatabaseError("Error in database._get_user_name: Too many users found for token:" + str(unique_token))

    def _get_user_data(self, db_connection, query_str, data_id, user_id):
        value = data_id.upper()
        if value not in self.valid_user_data:
            raise DatabaseError("Error in database._get_user_data:data_id not available: " + str(data_id))

        rows = self._exec_query(db_connection, query_str, (value, user_id))
        if len(rows) == 1:
            return rows[0].data_value

        if len(rows) == 0:
            raise DatabaseError("Error in database._get_user_data: No data found for user:" +
                                    str(user_id) + "; value:" + str(data_id))

        raise DatabaseError("Error in database._get_user_data: Too much data found for user:" +
                                str(user_id) + "; value:" + str(data_id))

    def _get_item_list(self, db_connection, query_str, ship_no):
        rows = self._exec_query(db_connection, query_str, ship_no)
        if len(rows) > 0:
            return rows

        raise DatabaseError("Error in database._get_item_list: Unable to find item list for shipment:" + str(ship_no))

    def _get_item_detail(self, db_connection, query_str, item_no, manu_no):
        rows = self._exec_query(db_connection, query_str, (item_no, manu_no))
        if len(rows) > 0:
            return rows
        elif len(rows) == 0:
            return None

        raise DatabaseError("Error in database._get_item_detail: Unable to find item details for part:" + str(item_no) + " and manu:" + str(manu_no))

    def _get_item_hist(self, db_connection, query_str, item_no, manu_no):
        rows = self._exec_query(db_connection, query_str, (item_no, manu_no))
        if len(rows) == 1:
            return rows[0][0].split(",")
        elif len(rows) == 0:
            return None

        raise DatabaseError("Error in database._get_item_hist: Too many history columns found for part:" + str(item_no) + " and manu:" + str(manu_no))

    def _get_item_pic_urls(self, db_connection, query_str, item_no, manu_no):
        rows = self._exec_query(db_connection, query_str, (item_no, manu_no))
        if len(rows) > 0:
            return ["http://www.masline.com/sites/default/files/styles/medium/public/item_pics/" + parse.quote(pic, safe="")
                        for row in rows for pic in row if pic != ""]
        else:
            return None

    def _get_item_no(self, db_connection, query_str, lot_no):
        rows = self._exec_query(db_connection, query_str, lot_no)
        if len(rows) == 1:
            return rows[0].item, rows[0].manu
        elif len(rows) == 0:
            return None

        raise DatabaseError("Error in database._get_item_no: Too many parts found for lot no:" + str(lot_no))

    def _get_shipment_notes(self, db_connection, query_str, ship_no):
        rows = self._exec_query(db_connection, query_str, ship_no)
        if len(rows) == 1:
            return rows[0].whse_note.replace("\n", " ")
        elif len(rows) == 0:
            return None

        raise DatabaseError("Error in database._get_shipment_notes: Too many notes found for shipment:" + str(ship_no))

    def _get_alternate_lots(self, db_connection, query_str, ship_no, lot_no):
        rows = self._exec_query(db_connection, query_str, (ship_no, lot_no))
        if len(rows) > 0:
            return rows

        raise DatabaseError("Error in database._get_alternate_lots: Unable to find alternate lots on shipment:" + str(ship_no) + "; lot_no:" + str(lot_no))

    def _get_shipment_status(self, db_connection, query_str, ship_no):
        rows = self._exec_query(db_connection, query_str, ship_no)
        if len(rows) == 1:
            return rows[0].status

        raise DatabaseError("Error in database._get_shipment_status: Unable to find status for shipment:" + str(ship_no))

    def _get_loc_int_id(self, db_connection, query_str, location):
        rows = self._exec_query(db_connection, query_str, location)
        if len(rows) != 1:
            return False
        return rows[0].loc_int_id

    def _insert_picked_wrong_lot(self, db_connection, query_str, location, wrong_lot, correct_lot, ship_no, lin_no, qty_from_loc, user_id):
        loc_int_id = self._get_loc_int_id(db_connection, self.valid_queries["get_loc_int_id"], location)
        if not loc_int_id:
            raise DatabaseError("Error in database._insert_picked_wrong_lot: Location doesn't exist:" + str(location))
        self._exec_query(db_connection, query_str, (loc_int_id, user_id, qty_from_loc, wrong_lot))
        self._insert_picked_lot(db_connection, self.valid_queries["insert_picked_lot"], loc_int_id, correct_lot, ship_no, lin_no, qty_from_loc, user_id)

    def _insert_picked_lot(self, db_connection, query_str, location, lot_no, ship_no, lin_no, qty_from_loc, user_id):
        if stack()[1][3] != "_insert_picked_wrong_lot":
            loc_int_id = self._get_loc_int_id(db_connection, self.valid_queries["get_loc_int_id"], location)
            if not loc_int_id:
                raise DatabaseError("Error in database._insert_picked_lot: Location doesn't exist:" + str(location))
        else:
            loc_int_id = location
        self._exec_query(db_connection, query_str, (loc_int_id, user_id, qty_from_loc, lot_no, ship_no, lin_no))

    def _insert_user_data(self, db_connection, query_str, data_id, data_value, user_id):
        self._exec_query(db_connection, query_str, (user_id, data_id, data_value))

    def _set_shipment_scanned(self, db_connection, query_str, ship_no, user_id):
        self._exec_query(db_connection, query_str, (user_id, ship_no))

    def _set_shipment_pulled(self, db_connection, query_str, ship_no, user_id):
        self._exec_query(db_connection, self.valid_queries["+insert_all_lots_pulled"], (user_id, ship_no))
        self._exec_query(db_connection, query_str, (user_id, ship_no))

    def _update_user_data(self, db_connection, query_str, data_id, data_value, user_id):
        self._exec_query(db_connection, query_str, (data_value, user_id, data_id))

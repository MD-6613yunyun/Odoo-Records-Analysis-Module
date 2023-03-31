from odoo import fields,models,api
from datetime import datetime
import xmlrpc.client
import random
from datetime import date, timedelta
###########################
##############################################################

#### Data extraction for records creation
# importing the required modules
import xmlrpc.client
import time
from datetime import date, timedelta


class LineTracker:
    BI_tracker = {}
    ID_create = {}

    def __init__(self, db, username, pwd):
        self.db = db
        self.username = username
        self.pwd = pwd
        self.uid = 0
        self.total_record_creations = 0

    def authenticate_server(self, server):
        common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(server))
        uid = common.authenticate(self.db, self.username, self.pwd, {})
        if uid:
            print(f"Authenticated with the unique ID - {uid}")
            self.uid = uid
        else:
            print("Invalid credentials or login..")
            print("Try again with valid credentials")
        return uid

    def initialize_objects_in_server(self, server: str):
        models = xmlrpc.client.ServerProxy("{}/xmlrpc/2/object".format(server))
        return models

    def track_lines(self, obj_models: object, model: str,department:bool = True):
        domain = [('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)]
        if department:
            results = obj_models.execute_kw(self.db, self.uid, self.pwd, model, 'search_read',
                                            [domain], {"fields": ['id', 'unit_id', 'create_uid']})
        else:
            results = obj_models.execute_kw(self.db, self.uid, self.pwd, model, 'search_read',
                                            [domain], {"fields": ['id', 'unit_id']})
        for data in results:
            # Department Trackers  ##############
            if department:
                if data['create_uid'][0] not in self.ID_create:
                    self.ID_create[data['create_uid'][0]] = 1
                else:
                    self.ID_create[data['create_uid'][0]] += 1
            # Business Unit Trackers ############
            unit = data['unit_id'][1]
            if unit not in self.BI_tracker:
                self.BI_tracker[unit] = 1
            else:
                self.BI_tracker[unit] += 1
        self.total_record_creations += len(results)
        return len(results)

    def track_lines_for_accountant(self, obj_models: object,department:bool = True):
        domain = [
            [('cash_type', '=', 'pay'), ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('cash_type', '=', 'receive'), ('create_date', '>=', self.start_date),
             ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'supplier'), ('payment_type', '=', 'inbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'supplier'), ('payment_type', '=', 'outbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'customer'), ('payment_type', '=', 'inbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)],
            [('partner_type', '=', 'customer'), ('payment_type', '=', 'outbound'),
             ('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date)]]
        acc_results = []
        for i in range(6):
            if 0 <= i < 2:
                model = 'account.cashbook'
                name = 'tree_unit'
            else:
                model = 'account.payment'
                name = 'unit_id'
            if department:
                results = obj_models.execute_kw(self.db, self.uid, self.pwd, model, 'search_read',
                                            [domain[i]], {"fields": ['id', name, 'create_uid']})
            else:
                results = obj_models.execute_kw(self.db, self.uid, self.pwd, model, 'search_read',
                                                [domain[i]], {"fields": ['id', name]})
            for data in results:
                if department:
                    if data['create_uid'][0] not in self.ID_create:
                        self.ID_create[data['create_uid'][0]] = 1
                    else:
                        self.ID_create[data['create_uid'][0]] += 1
                unit = data[name][1] if 'unit_id' in data else data[name]
                if unit not in self.BI_tracker:
                    self.BI_tracker[unit] = 1
                else:
                    self.BI_tracker[unit] += 1
            acc_results.append(len(results))
        self.total_record_creations += sum(acc_results)
        return acc_results

    def department_counts(self, obj_models: object):
        results = obj_models.execute_kw(self.db, self.uid, self.pwd, 'res.users', 'read',
                                        [list(self.ID_create.keys())], {"fields": ['department_id']})
        depart_count = {}

        for i, (key, value) in enumerate(self.ID_create.items()):
            if results[i]['department_id'][1] not in depart_count:
                depart_count[results[i]['department_id'][1]] = value
            else:
                depart_count[results[i]['department_id'][1]] += value
        return depart_count

    def set_date(self, month, day, year, auto=True):
        if auto:
            self.end_date = date.today().strftime('%Y-%m-%d') + " 17:29:59"
            self.start_date = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d') + " 17:30:13"
        else:
            self.start_date = f"{str(year)}-0{str(month)}-{str(day - 1)} 17:30:13"
            self.end_date = f"{str(year)}-0{str(month)}-{str(day)} 17:29:59"


def internal_calculations():
    # requirements for authentication
    server, db = "http://ec2-18-139-153-219.ap-southeast-1.compute.amazonaws.com", "mmm_uat"
    username, pwd = "MD-6613", "MD-6613"
    #  models used to check in
    models_check_in = ["sale.order", 'purchase.order', 'purchase.requisition', 'stock.inventory.adjustment',
                       'expense.prepaid', 'hr.expense','duty.process.line']
    ## Data processing
    # create an instance of our line tracker object
    mmm = LineTracker(db, username, pwd)
    # authentication
    uid = mmm.authenticate_server(server)
    # objects intialization to process datas within models
    models_obj = mmm.initialize_objects_in_server(server)
    # setting up the date when records were created
    mmm.set_date(3, 27, 2023)
    mmm.BI_tracker = {}
    ## a list to store values
    # key_modules = ["sale_module", "purchase_module", "inventory_requisition_module", "inventory_adjustment_module", "advance_expenses_module", "general_expenses_module"
    # ,"cashbook_payment_module", "cashbook_receipt_module", "customer_payment_module", "customer_receipt_module","duty_process_module"]
    key_units = {
          "Agriculture Unit (Machine)": "agri_m", "Agriculture Unit (Plantation)": "agir_p", "Construction Project Unit" : "construct_Project",
          "Construction MMM": "construct_mmm" , "Mining":"mining"  , "Machinery Rental Service" : "machinery_rents",
          "Logistics": "logistics", "Machinery Service & Parts":"machine_services", "Hydropower Unit": "hydropower","Head Office":"ho_unit",
          "Construction TMS": "ho_tms", "Gold Mining": "ho_gold", "Toyota MDMM": "ho_toyota", "Auto Parts Unit": "autoparts_unit",
          "Auto Parts Unit_PYAY": "autoparts_pyay","Auto Parts Unit_MDY": "autoparts_mdy"}
    # looping through the declared model and process the retrieval
    for i in range(7):
        # write the result and model name to the file
        mmm.track_lines(models_obj,models_check_in[i])
    # data retrival from account module
    account = mmm.track_lines_for_accountant(models_obj)  # account
    result_dct = dict((key_units[name],mmm.BI_tracker[name])for name in key_units if name in mmm.BI_tracker)
    # return dict(zip(key_modules,lst))
    return result_dct

#############################
##########################
###############################
### My Custom Module

class RecCounts(models.Model):
    _name = "rec.counts"
    _description = "Records Creation Analysis"

    # sale_module = fields.Integer(string="Sales Module")
    # purchase_module = fields.Integer(string="Purchase Module")
    # inventory_requisition_module = fields.Integer(string="Inventory Requisition Module")
    # inventory_adjustment_module = fields.Integer(string="Inventory Adjsutment Module")
    # advance_expenses_module = fields.Integer(string="Advance Expenses Module")
    # general_expenses_module = fields.Integer(string="General Expenses  Module")
    # cashbook_payment_module = fields.Integer(string="Cashbook Payment Module")
    # cashbook_receipt_module = fields.Integer(string="Cashbook Receipt  Module")
    # customer_payment_module = fields.Integer(string="Customer Payment Module")
    # customer_receipt_module = fields.Integer(string="Customer Receipt Module")

    agri_m = fields.Integer(string="Agriculture Unit(Machine)")
    agir_p = fields.Integer(string="Agriculture Unit(Plantation)")
    construct_Project = fields.Integer(string="Construction Project Unit")
    construct_mmm = fields.Integer(string="Construction MMM Unit")
    mining = fields.Integer(string="Mining Unit")
    machinery_rents = fields.Integer(string="Machinery Rental service Unit")
    logistics = fields.Integer(string="Logistics")
    machine_services = fields.Integer(string="Machinery Services & Parts Unit")
    hydropower = fields.Integer(string="Hydropower Unit")
    ho_unit = fields.Integer(string="Head Office Unit")
    ho_tms = fields.Integer(string="HO - Construction TMS")
    ho_gold = fields.Integer(string="HO - Gold Mining")
    ho_toyota = fields.Integer(string="HO - Toyota MDMM")
    autoparts_unit = fields.Integer(string="Autoparts Unit")
    autoparts_pyay = fields.Integer(string="Autoparts Unit_Pyay")
    autoparts_mdy = fields.Integer(string="Autoparts Unit_MDY")
    total_records = fields.Integer(string="Total Records Counts",compute="_compute_total_records",store=True)
    add_date = fields.Char(string="Date",default=datetime.today().strftime("%Y-%m-%d"))
    display_field = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    @api.depends("agri_m","agir_p","construct_Project","construct_mmm","mining","machinery_rents","logistics","machine_services","hydropower","ho_unit","ho_tms","ho_gold","ho_toyota","autoparts_unit","autoparts_pyay")
    def _compute_total_records(self):
        # for record in self:
        #     record.total_records = sum([record.sale_module , record.purchase_module , record.inventory_requisition_module
        #     , record.inventory_adjustment_module , record.advance_expenses_module , record.general_expenses_module
        #     , record.cashbook_payment_module , record.cashbook_receipt_module , record.customer_payment_module , record.customer_receipt_module])
        for record in self:
            record.total_records = sum([record.agri_m, record.agir_p, record.construct_Project, record.construct_mmm, record.mining
            , record.machinery_rents, record.logistics, record.machine_services, record.hydropower, record.ho_unit
            , record.ho_tms, record.ho_gold, record.ho_toyota, record.autoparts_unit, record.autoparts_pyay,record.autoparts_mdy])

    @api.depends('add_date')
    def _compute_display_name(self):
        latest_record = self.env['rec.counts'].search([], order='create_date desc', limit=1)
        latest_record_id = latest_record.id
        for record in self:
            record.display_name = f"{record.add_date} - {latest_record_id}"

    @api.model
    def import_rec_counts(self):
        values = internal_calculations()
        self.env['rec.counts'].create(values)

    @api.model
    def automate_create_records(self):
        self.import_rec_counts()

    @api.model
    def action_send_mail(self):
        template = self.env.ref('upcoming_record_counts.template_records_email')
        last_id = self.env['rec.counts'].search([], limit=1, order='id desc').id
        template.send_mail(last_id,force_send=True)


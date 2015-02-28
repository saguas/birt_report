from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe.model.document import Document

from frappe import _
import frappe

import logging
from io import BytesIO
import uuid

import birt_report.utils.utils as utils
from birt_report.utils.file import get_query

_logger = logging.getLogger(frappe.__name__)

birt_fields_not_supported = ["parent", "owner", "modified_by", "parenttype", "parentfield", "docstatus", "doctype", "name", "idx"]

class BirtBase(object):
	def __init__(self, doc={}):
		if isinstance(doc, Document):
			self.doc = frappe._dict(doc.as_dict())
		else:
			self.doc = frappe._dict(doc)
		self.user = frappe.local.session["user"]
		self.sid = frappe.local.session["sid"]
		self.reset_data_session()
		self.resume()

	def reset_data_session(self):
		self.data = frappe._dict({'data': frappe._dict({})})

	def get_birtconfig_from_db(self):
		from frappe.utils import pprint_dict
		self.doc = frappe.db.get_value('Birt Setup Report', None, "*", ignore=True, as_dict=True)
		print "getting from db birtconfig!!! doc {}".format(pprint_dict(self.doc))

	def resume(self):
		if self.data['data']:
			return
		data = self.get_birt_session_data()
		if data:
			self.data = frappe._dict({'data': data, 'user':data.get("user")})
		else:
			#if data session expire or not exist get from db the data, in this case no cookies!
			self.get_birtconfig_from_db()
			#self.data = frappe._dict({'data': data, 'user':data.get("user")})

		if not self.doc:
			self.doc = self.data['data']

	def get_birt_session_data(self):
		data = utils.get_birt_data("birtsession")
		if not data:
			self.delete_birt_session()
		return data

	def createBirtSession(self):
		if self.user!="Guest":
			self.update_data_cache()
			self.data['data']['session_expiry'] = utils.get_expiry_period()
			self.insert_birt_session_record()
			frappe.db.commit()

	def update_data_cache(self):
		self.data['data'] = {letter: i for letter,i in self.doc.iteritems() if letter not in birt_fields_not_supported}
		#self.data['data']['cookie'] = frappe.local.jasper_session.session.getSessionId() if frappe.local.jasper_session.session else {}
		self.data['user'] = self.user
		self.data['data']['last_updated'] = frappe.utils.now()
		print "update_data_cache {}".format(self.data)

	def insert_birt_session_record(self):
		frappe.db.sql("""insert into tabBirtSessions
			(sessiondata, user, lastupdate, status)
			values (%s , %s, NOW(), 'Active')""",
				(str(self.data['data']), self.data['user']))
		# also add to memcache
		utils.birtsession_set_value("birtsession", self.data)
		utils.birtsession_set_value("last_db_birt_session_update", frappe.utils.now())

	def delete_birt_session(self):
		utils.delete_birt_session("birtsession")

	def update(self, force_cache=False, force_db=False):
		"""extend session expiry"""
		if (frappe.session['user'] == "Guest"):
			return

		now = frappe.utils.now()

		if force_cache:
			self.update_data_cache()
		else:
			self.data['data']['last_updated'] = now

		# update session in db
		last_updated = utils.birtsession_get_value("last_db_birt_session_update")
		time_diff = frappe.utils.time_diff_in_seconds(now, last_updated) if last_updated else None

		# database persistence is secondary, don't update it too often
		updated_in_db = False
		if force_db or (time_diff==None) or (time_diff > 300):
		#if force_db:
			frappe.db.sql("""update tabBirtSessions set sessiondata=%s,
				lastupdate=NOW() where TIMEDIFF(NOW(), lastupdate) < TIME(%s) and status='Active'""" , (str(self.data['data']), utils.get_expiry_period()))
			utils.birtsession_set_value("last_db_birt_session_update", now)
			updated_in_db = True
			frappe.db.commit()

		# set in memcache
		utils.birtsession_set_value("birtsession", self.data)

		return updated_in_db

	def get_ask_params(self, data):
		pram = []
		params = data.get("params", None) or {}
		for k,v in params.iteritems():
			pram.append({"name":k, 'value':[v]})
		return pram

	def get_reports_list_from_db(self, filters_report={}, filters_param={}):
		return utils.birt_report_names_from_db(filters_report=filters_report, filters_param=filters_param)

	def get_query_rptdesignFile_from_server(self, file_content):
		query = ""
		list_query = get_query(BytesIO(file_content))
		if list_query:
			query = list_query[0].text
		return query

	def check_ids_in_hooks(self, doc, data, params):
		pram_server = [{"name": "name_ids", "attrs": params, "value": data.get('name_ids', [])}]
		res = utils.call_hook_for_param(doc, data, pram_server)
		print "res on hooks 2 {}".format(res)
		if res:
			data['name_ids'] = res[0].get('value')
		return res[0]

	def update_birt_reqid_record(self, reqId, data):
		#print "reqID update db {}".format(str(data['data']))
		frappe.db.sql("""update tabBirtReqids set data=%s, lastupdate=NOW()
			where reqid=%s""",(str(data['data']), reqId))
		# also add to memcache
		print "inserting reqId {0} data {1}".format(reqId, data['data'])
		utils.birtsession_set_value(reqId, data)
		frappe.db.commit()

	def insert_birt_reqid_record(self, reqId, data):
			frappe.db.sql("""insert into tabBirtReqids
				(reqid, data, lastupdate)
				values (%s , %s, NOW())""",
					(reqId, str(data['data'])))
			# also add to memcache
			print "inserting reqId {0} data {1}".format(reqId, data['data'])
			utils.birtsession_set_value(reqId, data)
			frappe.db.commit()

	def get_birt_report_list_from_db(self, tab="tabBirtReportListAll"):
		rec = frappe.db.sql("""select name, data
			from {0} where
			TIMEDIFF(NOW(), lastupdate) < TIME("{1}")""".format(tab, utils.get_expiry_period("report_list_all")))
		return rec

	def prepareResponse(self, detail, reqId):
		res = {"requestId": reqId, "uri":detail.get("reportURI"), "reqtime": frappe.utils.now()}
		if detail.get("status") == "ready":
			ids = []
			for i in detail.get("exports"):
				if i.get("status") == "ready":
					id = i.get("id")
					outr = i.get("outputResource")
					ids.append({"id":id, "fileName": outr.get("fileName")})
				else:
					res['status'] = "not ready"
					break
			res["ids"] = ids
		return res

	def prepareCollectResponse(self, resps):
		reqids = []
		status = "ready"
		for resp in reversed(resps):
			ncopies = []
			for r in resp:
				requestId = r.get('requestId')
				ncopies.append(requestId)
				#print "r is {}".format(r)
				#insert_jasper_reqid_record(requestId, {"data":r})
				if r.get('status') == "ready":
					continue
				status = "not ready"
			reqids.append(ncopies)
			#print "ncopies is {}".format(ncopies)
		res = self.make_internal_reqId(reqids, status)

		return res

	def make_internal_reqId(self, reqids, status):
		intern_reqId = "intern_reqid_" + uuid.uuid4().hex
		reqtime = frappe.utils.now()
		reqDbObj = {"data":{"reqids": reqids, "last_updated": reqtime,'session_expiry': utils.get_expiry_period(intern_reqId)}}
		self.insert_birt_reqid_record(intern_reqId, reqDbObj)
		res = {"requestId": intern_reqId, "reqtime": reqtime, "status": status}
		return res

	def get_birt_reqid_data(self, reqId):
		data = utils.get_birt_data(reqId, get_from_db=self.get_birt_reqid_data_from_db, args=[reqId])
		if not data:
			utils.delete_birt_session(reqId, "tabBirtReqids where reqid='%s'" % reqId)
		return frappe._dict({'data': data})

	def get_birt_reqid_data_from_db(self, *reqId):
		rec = frappe.db.sql("""select reqid, data
			from tabBirtReqids where
			TIMEDIFF(NOW(), lastupdate) < TIME(%s) and reqid=%s""", (utils.get_expiry_period(reqId),reqId))
		return rec

	#def run_report_async(self, path, doc, data={}, params=[], async=True, pformat="pdf", ncopies=1, for_all_sites=1):
	def run_report_async(self, doc, data={}, params=[]):
		#resps = []
		print "Parameters is list {} name_ids {}".format(params, data.get('name_ids', []))
		if not doc.birt_report_type == "General":
			#get the ids for this report from hooks. Return a list of ids
			if doc.birt_report_type == "Server Hooks":
				self.check_ids_in_hooks(doc, data, params)

			name_ids = data.get('name_ids', [])
			if params or name_ids:
				if not name_ids:
					res = self.check_ids_in_hooks(doc, data, params)
					print "hooks res {}".format(res)
					if not res:
						frappe.throw(_("Report {} input params error. This report is of type {} and needs at least one name.".format(doc.get('name'),doc.birt_report_type)))
						return
				#print "name_ids from hooks {}".format(data.get('name_ids'))
				if doc.birt_report_type == "Form":
					if not data.get('ids', None):
						data['ids'] = []
					for elem in data.get('name_ids', []):
						data['ids'].append(elem)
					#data['ids'] = [data.get('name_ids', [])[0]]
						#resps.append(self._run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
				elif doc.birt_report_type == "List":
					data['ids'] = data.get('name_ids', [])
					#resps.append(self._run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
			#else:
				#resps.append(self._run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		#else:
		#resps.append(self._run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))

		#return resps
		return data

	def report_polling_base(self, reqId):
		result = []
		req = [{}]
		data = self.get_birt_reqid_data(reqId)
		if data:
			d = data['data']
			print "polling {}".format(d)
			for ids in d.get('reqids'):
				for id in ids:
					res = self.polling(id)
					if res.get('status') != "ready":
						result = []
						break
					result.append(res)
				if not result:
					break
			for r in result:
				new_data = {"data":{"result": r, "last_updated": frappe.utils.now(), 'session_expiry': d.get('session_expiry')}}
				self.update_birt_reqid_record(r.get('requestId'), new_data)
			if result:
				req = [{"requestId": reqId, "reqtime": frappe.utils.now(), "status": "ready"}]
		else:
			print "Report Not Found."
			frappe.throw(_("Report Not Found!!!"))
		print "result in polling local {}".format(result)
		return req

	def filter_perm_roles(self, data):
		removed = 0
		count = 0
		toremove = []
		for k,v in data.iteritems():
			if isinstance(v, dict):
				#found = False
				count += 1
				perms = v.pop("perms", None)
				print "perms {}".format(perms)
				found = utils.check_birt_perm(perms)
				if not found:
					toremove.append(k)
					removed = removed + 1
		for k in toremove:
			data.pop(k, None)
		data['size'] = count - removed

	#check if exist at least one docname in data
	def check_docname(self, data, doctype):
		ret = False
		if not data:
			return ret
		for k,v in data.iteritems():
			if isinstance(v, dict):
				if v.get("Doctype name") == doctype:
					ret = True
					break
		return ret

	def validate_ticket(self, data):
		last_timeout = utils.birtsession_get_value("last_birt_session_timeout")
		request_time = data.get("reqtime")
		time_diff = frappe.utils.time_diff_in_seconds(request_time, last_timeout) if last_timeout else None
		if time_diff and time_diff < 0:
			frappe.throw("RequestID not Valid!!!")

from __future__ import unicode_literals
__author__ = 'luissaguas'

from frappe import _
import frappe

from birt_report.utils.file import get_birt_path
import birt_report.utils.utils as utils

import logging
import uuid
import thread
import os

import birt_report.birt_reports as br

import BirtBase as Bb

_logger = logging.getLogger(frappe.__name__)

print_format = ["docx", "ods", "odt", "rtf", "xls", "xlsx", "pptx", "xhtml", "pdf"]

class BirtLocal(Bb.BirtBase):
	def __init__(self, doc={}):
		super(BirtLocal, self).__init__(doc)

	def run_local_report_async(self, path, doc, data={}, params=[], async=True, pformat="pdf", ncopies=1, for_all_sites=1):
		resps = []
		#data = self.run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites)
		data = self.run_report_async(doc, data=data, params=params)
		if doc.birt_report_type == "Form":
			ids = data.get('ids')
			for id in ids:
				data['ids'] = [id]
				resps.append(self._run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		else:
			resps.append(self._run_report_async(path, doc, data=data, params=params, async=async, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites))
		cresp = self.prepareCollectResponse(resps)
		#return resp[len(resp) - 1]
		cresp["origin"] = "local"
		return [cresp]

	def _run_report_async(self, path, doc, data={}, params=[], async=True, pformat="pdf", ncopies=1, for_all_sites=1):
	#_logger.info("jasper_compile jrxml dir {0} destFileName {1}".format(jrxml, destFileName))
		pram_server = []
		hashmap = br.HashMap()
		pram_copy_name = ""
		pram_copy_page_name = ""
		for param in params:
			is_copy = param.is_copy.lower()
			p = param.birt_param_name
			value = ""
			if is_copy == _("is for where clause"):
				#value = data.get('name_ids')
				value = data.get('ids')
				if value:
					a = ["'%s'" % t for t in value]
				else:
					value = utils.get_value_param_for_hook(param)
					if not isinstance(value, basestring):
						a = ["'%s'" % t for t in list(value)]
					else:
						a = list(a)
				#a = ["'%s'" % t for t in data.get('name_ids')]
				value = "where name %s (%s)" % (param.param_expression, ",".join(a))
			elif is_copy == _("Is for copies"):
				#set the number of copies
				#indicate the index of param is for copies
				pram_copy_name = p
			elif is_copy == _("is for page number"):
				pram_copy_page_name = p
			elif is_copy == _("is for server hook"):
				#to alter like server reports
				#value = data.get('name_ids')
				value = data.get('ids')
				if not value:
					#if not data and not entered value then get default
					value = utils.get_value_param_for_hook(param)
				pram_server.append({"name":p, 'value':value, "attrs": param})
				continue
				#value = call_hook_for_param(doc, data, param)
			else:
				#p = param.jasper_param_name
				#value sent take precedence from value in doctype jasper_param_value
				value = data.get(p) or param.birt_param_value
			print "hashmap put param {} value {}".format(p, value)
			hashmap.put(p, value)
		path_join = os.path.join
		resp = []
		params = utils.call_hook_for_param(doc, data, pram_server) if pram_server else []
		print "params in local {}".format(params)
		for param in params:
			p = param.get('name')
			value = param.get('value')
			hashmap.put(p, value)
		copies = [_("Single"), _("Duplicated"), _("Triplicate")]
		conn = "jdbc:mysql://" + (frappe.conf.db_host or 'localhost') + ":3306/" + frappe.local.site + "?user="+ frappe.conf.db_name +\
				"&password=" + frappe.conf.db_password
		reportName = self.getFileName(path)#data.get("report_name")
		birt_path = get_birt_path()
		outtype = print_format.index(pformat)
		for m in range(ncopies):
			if pram_copy_name:
				hashmap.put(pram_copy_name, copies[m])
				#print "hashmap 2 put param {} value {}".format(pram_copy_name, copies[m])
			if pram_copy_page_name:
				hashmap.put(pram_copy_page_name, str(m) + _(" of ") + str(ncopies))
				#print "hashmap 3 put param {} value {}".format(pram_copy_page_name, str(m) + _(" of ") + str(ncopies))
			reqId = uuid.uuid4().hex
			outputPath = path_join(compiled_path, reqId)
			frappe.create_folder(outputPath)
			sessionId = "local_report_" + reqId
			res = self.prepareResponse({"reportURI": os.path.relpath(outputPath, birt_path) + os.sep + reportName + "." + pformat}, sessionId)
			#resp.append(res)
			res["status"] = None
			resp.append(res)#{"requestId":sessionId, "status": None}
			try:
				for pram in self.get_ask_params(data):
					hashmap.put(pram.get("name"), pram.get("value"))
				result = {"fileName": reportName + "." + pformat, "uri":outputPath + os.sep + reportName + "." + pformat, "last_updated": res.get("reqtime"), 'session_expiry': utils.get_expiry_period(sessionId)}
				self.insert_birt_reqid_record(sessionId, {"data":{"result":result, "last_updated": frappe.utils.now(),'session_expiry': utils.get_expiry_period()}})
				thread.start_new_thread(self._export_report, (compiled_path + os.sep, reportName, outputPath + os.sep, hashmap, conn, outtype, ) )
			except Exception as e:
				frappe.throw(_("Error in report %s, error is: %s!!!" % (doc.birt_report_name, e)))
				#print "Error: unable to start thread"
		return resp

	def _export_report(self, compiled_path, reportName, outputPath, hashmap, conn, outtype):
		export_report = br.ExportReport()
		print "making 3 report compiled path {} reportName {} outputPath {} conn {} outtype {} hashmap {}".format(compiled_path, reportName, outputPath, conn, outtype, hashmap)
		export_report.export(compiled_path, reportName, outputPath, hashmap, conn, outtype)

	def polling(self, reqId):
		data = self.get_birt_reqid_data(reqId)
		if not data['data']:
			frappe.throw(_("No report for this reqid %s !!" % reqId[13:]))
		output_path = data['data']['result'].get("uri")
		print "output_path {0} rid {1} data {2}".format(output_path, reqId, data)
		if os.path.exists(output_path):
			res = self.prepareResponse({"reportURI": data['data']['result'].get("uri"), "status":"ready", "exports":[{"status":"ready", "id":reqId, "outputResource":{"fileName": data['data']['result'].get("fileName")}}]}, reqId)
			res["status"] = "ready"
			print "local report exists {}".format(res)
		else:
			res = self.prepareResponse({}, reqId)
		return res

	def getLocalReport(self, reqId):
		data = self.get_birt_reqid_data(reqId)
		if not data['data']:
			frappe.throw(_("No report for this reqid %s !!" % reqId))
		print "local file {}".format(data)
		output_path = data['data']['result'].get("uri")
		with open(output_path, mode='rb') as file:
			content = file.read()
		return content

	def getFileName(self, file):
		index = file.rfind(os.sep) + 1
		name_ext = file[index:]
		return name_ext.split(".")[0]
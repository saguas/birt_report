from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe import _
import frappe

import logging, json, os

import birt_report.utils.utils as utils
import BirtBase as Bb

from io import BytesIO
from PyPDF2 import PdfFileMerger
import cStringIO
import zipfile

_logger = logging.getLogger(frappe.__name__)

class BirtRoot(Bb.BirtBase):
	def __init__(self, doc={}):
		self.jps = None
		self.jpl = None
		super(BirtRoot, self).__init__(doc)

	#called in jasperserverconfig.py at the save button was pushed. Just save the data
	def config(self):
		_logger.info("Birt update_cache self.doc {}".format(self.doc))
		if not self.doc:
			frappe.throw(_("Something was wrong, no doc!!!" ))

		if self.data["data"]:
			self.update(force_cache=True, force_db=True)
		else:
			#delete all db old sessions if exist
			self.delete_birt_session()

		return

	def _get_reports_list(self, filters_report={}, filters_param={}, force=False, cachename="report_list_all", tab="tabBirtReportListAll", update=False):
		ret = self.get_reports_list_from_db(filters_report=filters_report, filters_param=filters_param)
		#check to see if there is any report by now. If there are reports don't check the server
		if ret is None:
			#called from client. Don't let him change old reports attributes
			import_only_new = self.data['data'].get('import_only_new')
			self.data['data']['import_only_new'] = 1
			print "data: {}".format(self.data['data'])
			self.jps.import_all_birt_reports(self.data['data'], force=force)
			self.data['data']['import_only_new'] = import_only_new
			#could be recursive but there is no need for resume again because decorator
			ret = self.get_reports_list_from_db(filters_report=filters_report, filters_param=filters_param)
		ptime = self.data['data'].get('birt_polling_time')
		if ret:
			ret['birt_polling_time'] = ptime
		if ret and not update:
			utils.insert_list_all_memcache_db(ret, cachename=cachename, tab=tab)
		elif ret:
			utils.update_list_all_memcache_db(ret, cachename=cachename, tab=tab)
		return ret

	def get_reports_list_for_all(self):
		if self.sid == 'Guest':
			return None
		data = {}
		dirt = utils.birtsession_get_value("report_list_dirt_all")
		print "dirty!! {}".format(dirt)
		#dirt = False
		if not dirt:
			data = utils.get_birt_data("report_list_all", get_from_db=self.get_birt_report_list_from_db)

		if not data:
			utils.delete_birt_session("report_list_all", "tabBirtReportListAll")
			r_filters=["`tabBirt Reports`.birt_doctype is NULL", "`tabBirt Reports`.birt_report is NULL"]
			data = self._get_reports_list(filters_report=r_filters)
			print "data new {}".format(data)
		if data:
			utils.birtsession_set_value("report_list_dirt_all", False)
			data.pop('session_expiry',None)
			data.pop('last_updated', None)
			#if frappe.local.session['user'] != "Administrator":
			self.filter_perm_roles(data)

		return data

	def remove_server_docs(self, data):
		toremove = []
		removed = 0
		for k,v in data.iteritems():
			if isinstance(v, dict):
				origin = v.pop("birt_report_origin", None)
				if origin == "JasperServer":
					toremove.append(k)
					removed = removed + 1
		for k in toremove:
			data.pop(k, None)
		data['size'] = data['size'] - removed

	def get_reports_list(self, doctype, docnames):
		if not doctype:
			frappe.throw(_("You need to provide the doctype name!!!"))
		if docnames:
			docnames = json.loads(docnames)
		else:
			docnames = []

		new_data = {}
		added = 0
		if frappe.local.session['sid'] == 'Guest':
			return None

		dirt = utils.birtsession_get_value("report_list_dirt_doc")
		data = {}
		#dirt = False
		if not dirt:
			data = utils.get_birt_data("report_list_doctype", get_from_db=self.get_birt_report_list_from_db, tab="tabBirtReportListDoctype")

		if not data or not self.check_docname(data, doctype):
			utils.delete_birt_session("report_list_doctype", "tabBirtReportListDoctype")
			r_filters={"birt_doctype": doctype}
			update = False if not data else True
			data = self._get_reports_list(filters_report=r_filters, cachename="report_list_doctype", tab="tabBirtReportListDoctype", update=update)

		if data and self.check_docname(data, doctype):
			utils.birtsession_set_value("report_list_dirt_doc", False)
			data.pop('session_expiry',None)
			data.pop('last_updated', None)
			for k,v in data.iteritems():
				if isinstance(v, dict):
					if v.get("Doctype name") == doctype:
						if docnames and v.get('birt_report_type') == "List":
							continue
						if frappe.local.session['user'] != "Administrator":
							for docname in docnames:
								for ptype in ("read", "print"):
									if not frappe.has_permission(doctype, ptype=ptype, doc=docname, user=frappe.local.session['user']):
										print "No {0} permission for doc {1}".format(ptype, docname)
										continue
							rdoc = frappe.get_doc("Birt Reports", k)
							print "rdoc for list reports {}".format(rdoc.birt_roles)
							if not utils.check_birt_doc_perm(rdoc.birt_roles):
								print "No {0} permission!".format("read")
								continue
						new_data[k] = v
						added = added + 1
		new_data['size'] = added

		if not self.check_server_status():
			print "a remover {}".format(new_data)
			self.remove_server_docs(new_data)

		return new_data

	def run_report(self, data, docdata=None, rtype="Form"):
		doctype = data.get('doctype')
		rdoc = frappe.get_doc(doctype, data.get('report_name'))
		if data.get("fortype").lower() == "doctype" and rtype in ("List", "Form"):
			for docname in data.get('name_ids'):
				for ptype in ("read", "print"):
					if not frappe.has_permission(rdoc.birt_doctype, ptype=ptype, doc=docname, user=frappe.local.session['user']):
						raise frappe.PermissionError(_("No {0} permission for doc {1} in doctype {3}!").format(ptype, docname, rdoc.birt_doctype))
			#if user can read doc it is possible that can't print it! Just uncheck Read permission in doctype Jasper Reports
			if not utils.check_birt_doc_perm(rdoc.birt_roles):
				raise frappe.PermissionError(_("No print permission!"))
		else:
			if not utils.check_birt_perm(rdoc.birt_roles):
				raise frappe.PermissionError(_("No print permission!"))
		params = rdoc.birt_parameters
		origin = rdoc.birt_report_origin.lower()
		result = []
		pformat = data.get('pformat')
		#copies = [_("Single"), _("Duplicated"), _("Triplicate")]
		try:
			#ncopies = copies.index(rdoc.jasper_report_number_copies) + 1 if pformat == "pdf" else 1
			ncopies = get_copies(rdoc, pformat)
			if origin == "localserver":
				path = rdoc.birt_upload_rptdesign
				self.get_server("local")
				if not path:
					frappe.throw(_("%s: Import first a rptdesign file!!!" % rdoc.name))
				for_all_sites = rdoc.birt_all_sites_report
				result = self.jpl.run_local_report_async(path, rdoc, data=data, params=params, async=True, pformat=pformat, ncopies=ncopies, for_all_sites=for_all_sites)
			else:
				path = rdoc.birt_report_path
				self.get_server("server")
				if not self.jps.is_login:
					frappe.msgprint(_("Birt login error"))
					return

				result = self.jps.run_remote_report_async(path, rdoc, data=data, params=params, async=True, pformat=pformat, ncopies=ncopies)
			result[0]["pformat"] = pformat
		except ValueError:
			frappe.throw(_("Report number of copies error %s!!!" % rdoc.name))

		return result

	def get_report_server(self, data):
		#check if this requestId is older than last timeout
		self.validate_ticket(data)
		d = self.get_birt_reqid_data(data.get('requestId'))
		if not d:
			frappe.throw(_("Report Not Found!!!"))
		reqids = d['data'].get('reqids')
		print "new reqids {}".format(d)
		content = []
		fileName = None
		try:
			for ids in reqids:
				for id in ids:
					report = self.get_birt_reqid_data(id)
					print "new report {}".format(report)
					rdata = report['data'].get('result')
					reqId = [rdata.get("requestId")]
					expId = rdata.get("ids")
					pformat = data.get("pformat")
					print "expID array {}".format(expId)
					fileName = expId[0].get("fileName", None)
					rid_len = 1
					print "before get report local {}".format(reqId)
					if not any("local_report" in r for r in reqId):
						eid_len = len(expId)
						self.get_server("server")
						if not self.jps.is_login:
							frappe.msgprint(_("Birt login error"))
							return
						#if lens not equal then process only the first
						if rid_len == eid_len:
							for i in range(rid_len):
								content.append(self.jps.getReport(reqId[i], expId[i].get('id')))
						else:
							content.append(self.jps.getReport(reqId[0], expId[0].get('id')))
					else:
						self.get_server("local")
						for i in range(rid_len):
							print "get report local {}".format(reqId[i])
							content.append(self.jpl.getLocalReport(reqId[i]))
		except Exception as e:
			return frappe.msgprint(_("There is no report, try again later. Error: {}".format(e)))

		return fileName, content
	#pages is an array of pages ex. [2,4,5]
	def make_pdf(self, fileName, content, pformat, merge_all=True, pages=None):
		if fileName:
			fileName = fileName[fileName.rfind(os.sep) + 1:]
			output = cStringIO.StringIO()
			file_name = fileName.replace(" ", "-").replace("/", "-")
			if pformat=="pdf" and merge_all == True:
				merger = PdfFileMerger()
				for n in range(len(content)):
					merger.append(BytesIO(content[n]))
				merger.write(output)
			elif pformat=="pdf":
				merger = PdfFileMerger()
				for page in pages:
					merger.append(BytesIO(content[page]))
				merger.write(output)
			else:
				fname = file_name.split(".")
				myzip = zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED)
				try:
					pgs = range(len(content)) if pages is None else pages
					for n in pgs:
						myzip.writestr(fname[0] + "_" + str(n) + "." + fname[1], content[n])
				finally:
					myzip.close()
				file_name = fname[0] + ".zip"
			return file_name, output
		else:
			#frappe.throw(_("Report must have a path!!!"))
			frappe.msgprint(_("There is no report."))

	def prepare_file_to_client(self, file_name, output):
		frappe.local.response.filename = "{name}".format(name=file_name)
		frappe.local.response.filecontent = output
		frappe.local.response.type = "download"

def get_copies(rdoc, pformat):
	copies = [_("Single"), _("Duplicated"), _("Triplicate")]
	return copies.index(rdoc.birt_report_number_copies) + 1 if pformat == "pdf" else 1
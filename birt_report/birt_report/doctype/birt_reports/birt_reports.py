# Copyright (c) 2013, Luis Fernandes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

import birt_report.utils
from birt_report.utils.file import get_birt_path, get_rptdesign_path, get_params, get_query, remove_directory
from birt_report.utils.utils import check_queryString_param, birtsession_set_value
#import logging, os

class BirtReports(Document):
	def on_update(self, method=None):
		birtsession_set_value("report_list_dirt_all", True)
		birtsession_set_value("report_list_dirt_doc", True)
		if self.birt_upload_rptdesign:
			return

		frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Birt Parameter", "parent", '%s'),(self.name), auto_commit=1)
		self.query = ""

	def before_save(self, method=None):
		if not self.birt_param_message:
			self.birt_param_message = frappe.db.get_values_from_single(["birt_param_message"], None, "Birt Setup Report")[0][0].format(report=self.birt_report_name, user=frappe.local.session['user'])
		if self.birt_upload_rptdesign:
			#give feedback to the user shown related params
			query = get_query_from_xml(self)
			for q in query:
				print "query**************** {}".format(q.text)
				if q.text:
					self.query = q.text
			params = get_params_from_xml(self)
			#get total number of parameters to concatenate with name of parameter
			idx = frappe.db.sql("""select count(*) from `tabBirt Parameter`""")[0][0] + 1
			is_copy = "Is for copies"
			action_type = "Ask"
			ptype = "String"
			defaultValue = None
			description = None
			displayName = None
			allowblank = 1
			allowNull = 1
			controlType = "text-box"
			for param in params:
				pname = param.xpath('./@name')
				for c in param.xpath('./*'):
					name = c.xpath('./@name')[0]
					if name == "dataType":
						ptype = c.text
						if ptype.lower() == "decimal":
							ptype = "Float"
					if name == "defaultValue":
						defaultValue = c.text
					if name == "helpText":
						description = str(c.text).replace('\"', "").replace("\'","")
					if name == "displayName":
						displayName = str(c.text).replace('\"', "").replace("\'","")
					if name == "allowBlank":
						al = c.text
						if al == "false":
							allowblank = 0
					if name == "controlType":
						controlType = c.text
					if name == "allowNull":
						an = c.text
						if an == "false":
							allowNull = 0
				if check_param_exists(self, pname[0]):
					break
				if check_queryString_param(query, pname[0]):
					is_copy = "Is for where clause"
					action_type = "Automatic"
				self.append("birt_parameters", {"__islocal": True, "birt_param_name":pname[0], "birt_param_type":ptype.lower().capitalize(),\
						"birt_param_action": action_type, "param_expression":"In", "is_copy":is_copy, "name":pname[0] + ":" + str(idx), "birt_param_value": defaultValue,
						"birt_param_description": description, "birt_param_displayname": displayName, "birt_param_allowblank": allowblank, "birt_param_controltype": controlType,
						"birt_param_allownull": allowNull})
				idx = idx + 1
			return
		#if rptdesign file was removed then prepare to remove all associated images and params given feedback to the user
		self.jasper_parameters = []
		self.jasper_report_images = []
		return

	def on_birt_params(self, data=[], params=[]):
		print "new params hooks {}".format(data)
		for param in params:
			if param.get('name') != "name_ids":
				pname = param.get("name")
				attrs = param.get("attrs")
				default_value = param.get("value")
				print "birt_params hook: doc {0} data {1} pname {2} param {3} default_value {4}".format(self, data, pname, attrs.param_expression, default_value)
				a = ["'%s'" % t for t in default_value]
				value = "where name %s (%s)" % (attrs.param_expression, ",".join(a))
				if not default_value:
					default_value.append(value)
				else:
					param['value'] = value
				print "old_value {0} {1}".format(default_value, param.get('value'))
			else:
				param['value'].append('Administrator')

		return params


def _get_rptdesign_path(doc):
	birt_path = get_birt_path()
	rptdesign_path = get_rptdesign_path(birt_path, doc.birt_upload_rptdesign[1:])
	return rptdesign_path

def get_params_from_xml(doc):
	rptdesign_path = _get_rptdesign_path(doc)
	return get_params(rptdesign_path)

def get_query_from_xml(doc):
	rptdesign_path = _get_rptdesign_path(doc)
	return get_query(rptdesign_path)


#jasper docs have the same params spread so don't let them repeat in doc parameter
def check_param_exists(doc, pname):
	exist = False
	idx_pname = pname.rfind(":")
	if idx_pname != -1:
		pname = pname[0:idx_pname]
	for p in doc.birt_parameters:
		if p.birt_param_name == pname:
			exist = True
			break
	return exist


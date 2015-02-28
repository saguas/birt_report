from __future__ import unicode_literals
__author__ = 'luissaguas'
from frappe import _
import frappe
import json
from urllib2 import unquote
import logging, time
from frappe.utils import cint

from frappe.core.doctype.communication.communication import make

import BirtRoot as Br
from birt_report import birt_session_obj
from birt_report.utils.birt_email import sendmail
from birt_report.core.BirtRoot import get_copies

from birt_report.utils.utils import set_birt_email_doctype
from birt_report.utils.birt_email import birt_save_email, get_sender
from birt_report.utils.file import get_file

_logger = logging.getLogger(frappe.__name__)


def boot_session(bootinfo):
	#bootinfo['jasper_server_info'] = get_server_info()
	bootinfo['birt_reports_list'] = get_reports_list_for_all()

@frappe.whitelist()
def get_reports_list_for_all():
	jsr = birt_session_obj or Br.BirtRoot()
	return jsr.get_reports_list_for_all()

@frappe.whitelist()
def get_reports_list(doctype, docnames):
	return
	jsr = birt_session_obj or Br.BirtRoot()
	return jsr.get_reports_list(doctype, docnames)


@frappe.whitelist()
def get_report(data):
	#print "data get_reportssss {}".format(unquote(data))
	if not data:
		frappe.throw(_("No data for this Report!!!"))
	if isinstance(data, basestring):
		data = json.loads(unquote(data))
	pformat = data.get("pformat")
	fileName, content = _get_report(data)
	make_pdf(fileName, content, pformat)

#def _get_report(data, merge_all=True, pages=None, email=False):
def _get_report(data):
	jsr = birt_session_obj or Br.BirtRoot()
	fileName, content = jsr.get_report_server(data)

	return fileName, content

def make_pdf(fileName, content, pformat, merge_all=True, pages=None, email=False):
	jsr = birt_session_obj or Br.BirtRoot()
	file_name, output = jsr.make_pdf(fileName, content, pformat, merge_all, pages)
	if not email:
		jsr.prepare_file_to_client(file_name, output.getvalue())
		return

	return file_name, output

@frappe.whitelist()
def run_report(data, docdata=None, rtype="Form"):
	from frappe.utils import pprint_dict
	if not data:
		frappe.throw("No data for this Report!!!")
	if isinstance(data, basestring):
		data = json.loads(data)
	jsr = birt_session_obj or Br.BirtRoot()
	print "params in run_report 2 {}".format(pprint_dict(data))
	return jsr.run_report(data, docdata=docdata, rtype=rtype)


@frappe.whitelist()
def get_doc(doctype, docname):
	import birt_report.utils.utils as utils
	data = {}
	doc = frappe.get_doc(doctype, docname)
	if utils.check_birt_perm(doc.get("birt_roles", None)):
		data = {"data": doc}
	frappe.local.response.update(data)

@frappe.whitelist()
def birt_make(doctype=None, name=None, content=None, subject=None, sent_or_received = "Sent",
	sender=None, recipients=None, communication_medium="Email", send_email=False,
	print_html=None, print_format=None, attachments='[]', send_me_a_copy=False, set_lead=True, date=None,
	birt_doc=None, docdata=None, rtype="Form"):

	data = json.loads(birt_doc)
	result = run_report(data, docdata, rtype)

	#we have to remove the original and send only duplicate
	if result[0].get("status", "not ready") == "ready":
		pformat = data.get("pformat")
		rdoc = frappe.get_doc(data.get("doctype"), data.get('report_name'))
		ncopies = get_copies(rdoc, pformat)
		fileName, birt_content = _get_report(result[0])
		merge_all = True
		pages = None
		if pformat == "pdf" and ncopies > 1:
			merge_all = False
			pages = get_pages(ncopies, len(birt_content))

		file_name, output = make_pdf(fileName, birt_content, pformat, merge_all=merge_all, pages=pages, email=True)

	else:
		print "not sent by email... {}".format(result)
		frappe.throw(_("Error generating PDF, try again later"))
		frappe.errprint(frappe.get_traceback())
		return

	#attach = jasper_make_attach(data, file_name, output, attachments, result)

	make(doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
		sender=sender, recipients=recipients, communication_medium=communication_medium, send_email=False,
		print_html=print_html, print_format=print_format, attachments=attachments, send_me_a_copy=send_me_a_copy, set_lead=set_lead,
		date=date)

	sendmail(file_name, output, doctype=doctype, name=name, content=content, subject=subject, sent_or_received=sent_or_received,
		sender=sender, recipients=recipients, print_html=print_html, print_format=print_format, attachments=attachments,
		send_me_a_copy=send_me_a_copy)

	filepath = birt_save_email(data, file_name, output, result[0].get("requestId"), sender)
	print "birt email filepath {}".format(filepath)

	sender = get_sender(sender)
	set_birt_email_doctype(data.get('report_name'), recipients, sender, frappe.utils.now(), filepath, file_name)


def get_pages(ncopies, total_pages):
	pages = []
	clientes = total_pages/ncopies
	for n in range(clientes):
		pages.append(n*ncopies)

	return pages

@frappe.whitelist()
def get_birt_email_report(data):
	if not data:
		frappe.throw(_("No data for this Report!!!"))
	data = json.loads(unquote(data))
	file_name = data.get("filename")
	file_path = data.get("filepath")
	print "get_birt_email_report 2 {} {}".format(file_path, file_name)
	jsr = birt_session_obj or Br.BirtRoot()
	output = get_file(file_path, modes="rb")
	jsr.prepare_file_to_client(file_name, output)




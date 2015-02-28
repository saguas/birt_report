__author__ = 'luissaguas'
import os, logging
import frappe
from frappe import _
#from utils import update_doctype_doc
#from frappe.utils import get_site_path, get_site_base_path
from frappe.utils.file_manager import save_file_on_filesystem, delete_file_from_filesystem
#from jasperserver.report import Report
from xml.etree import ElementTree as ET
from lxml import etree
#import birt_report
from birt_report.utils.utils import set_birt_parameters
from frappe.modules.import_file import import_doc


birt_ext_supported = ["rptdesign"]
_logger = logging.getLogger(frappe.__name__)


def get_xml_elem(xmlfile, elem_name):
	tree = etree.parse(xmlfile) #.replace('\\', '/'))
	root = tree.getroot()
	print "root: {}".format(root.tag)
	nameSpace = root.tag.split('report')[0]
	if nameSpace:
		c = len(nameSpace) - 1
		elems = root.findall(".//b:" + elem_name, namespaces={'b':nameSpace[1:c]})
	else:
		elems = root.findall(".//" + elem_name)

	return elems

def get_params(xmlfile):

	params = get_xml_elem(xmlfile, "scalar-parameter")

	return params

def get_query(xmlfile):

	query = get_xml_elem(xmlfile, "property[@name='queryText']")
	return query

def _insert_params(pname, c_idx, parent, param_type):
	mydict = {"updateDate":frappe.utils.now()}
	doc = set_birt_parameters(pname, parent, c_idx, mydict, param_type)
	print "Doc param {}".format(doc)
	import_doc(doc)

def insert_params(xmlfile, dn):
	params = get_params(xmlfile)
	c_idx = 0
	for param in params:
		pname = param.xpath('./@name')
		pclass = param.xpath('./@class')
		c_idx = c_idx + 1
		print "params: {}".format(dn)
		ptype = pclass[0].split(".")
		c = len(ptype) - 1
		_insert_params(pname[0], c_idx, dn, ptype[c].lower())

	return params


def get_rptdesign_path(dir_path, dn):
	path_join = os.path.join
	rptdesign_path = path_join(dir_path, dn)
	return rptdesign_path

def get_birt_path():
	path = frappe.db.get_value('Birt Setup Report', None, "birt_report_path", ignore=True, as_dict=True)
	return path.get("birt_report_path", None)

def write_StringIO_to_file(file_path, output):
	write_file(output.getvalue(), file_path, modes="wb")

def write_file(content, file_path, modes="w+"):
	# write the file
	with open(file_path, modes) as f:
		f.write(content)
	return file_path

def check_extension(fname):
	ext = get_extension(fname)
	if ext and ext.lower() not in birt_ext_supported:
		frappe.msgprint(_("Please select a file with extension rptdesign"),
			raise_exception=True)
	return ext.lower()

def get_extension(fname):
	ext = fname.split(".")
	if len(ext) > 1:
		return ext[1]
	return None

def write_file_rptdesign(fname, content, content_type):
	path_join = os.path.join
	dt = frappe.form_dict.doctype
	if dt == "Birt Reports":
		ext = check_extension(fname)
		dn = frappe.form_dict.docname
		birt_report_path = get_birt_path()
		if ext != "rptdesign":
			frappe.msgprint(_("Add a report file for this report first with extension rptdesign"), raise_exception=True)
		else:
			rname = check_if_rptdesign_exists_db(dt, dn)
			print "rname {}".format(rname)
			if rname:
				frappe.msgprint(_("Remove first the report file (%s) associated with this doc!" % (rname)), raise_exception=True)

		rptdesign_path = get_rptdesign_path(birt_report_path, dn)
		frappe.create_folder(rptdesign_path)
		file_path = path_join(rptdesign_path, fname)
		fpath = write_file(content, file_path)
		path =  os.path.relpath(fpath, birt_report_path)

		return {
			'file_name': os.path.basename(path),
			'file_url': os.sep + path.replace('\\','/')
		}
	else:
		return save_file_on_filesystem(fname, content, content_type)


def check_if_rptdesign_exists_db(dt, dn):
	fname = None
	docs = frappe.get_all("File Data", fields=["file_name"], filters={"attached_to_name": dn, "attached_to_doctype": dt})
	for doc in docs:
		rptdesign_ext = get_extension(doc.file_name)
		if rptdesign_ext == "rptdesign":
			fname = doc.file_name
			break
	return fname

def delete_file_rptdesign(doc):
	dt = doc.attached_to_doctype
	if dt == "Birt Reports":
		dn = doc.attached_to_name
		ext = get_extension(doc.file_name)
		file_path = os.path.join(get_birt_path(), doc.file_url[1:])
		if os.path.exists(file_path) and ext == "rptdesign":
			print "deleteing rptdesign {}".format(file_path)
			os.remove(file_path)
			frappe.db.sql("""delete from `tab%s` where %s=%s """ % ("Birt Parameter", "parent", '%s'),(dn), auto_commit=1)
			frappe.db.set_value(dt, dn, 'query', "")
	else:
		delete_file_from_filesystem(doc)

def remove_from_doc(dt, dn, field, where_field = "name"):
	frappe.db.sql("""update `tab%s` set %s=NULL where %s=%s""" % (dt, field, where_field, '%s'),(dn))

def delete_from_doc(dt, dn, field, value, where_field):
	#print """delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, value,  where_field,dn)
	frappe.db.sql("""delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, '%s',  where_field,'%s'),(value, dn), auto_commit=1)

def delete_from_FileData(dt, dn, file_url):
	#print """delete from `tab%s` where %s=%s and %s=%s""" % (dt, field, value,  where_field,dn)
	frappe.db.sql("""delete from `tabFile Data` where attached_to_doctype=%s and attached_to_name=%s and file_url=%s""",(dt, dn, file_url), auto_commit=1)

def remove_directory(path):
	import shutil
	print "remove directory???"
	shutil.rmtree(path)

def get_file(path, modes="r"):
	with open(path, modes) as f:
		content = f.read()
	return content


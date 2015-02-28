app_name = "birt_report"
app_title = "Birt Report"
app_publisher = "Luis Fernandes"
app_description = "Create Reports"
app_icon = "birt-logo.svg"
app_color = "#66CCFF"
app_email = "luisfmfernandes@gmail.com"
app_version = "0.0.1"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/birt_report/css/birt_report.css"
# app_include_js = "/assets/birt_report/js/birt_report.js"

# include js, css files in header of web template
# web_include_css = "/assets/birt_report/css/birt_report.css"
#web_include_js = "/assets/birt_report/js/birt_report.js"

app_include_css = "/assets/birt_report/css/callouts.css"
app_include_js = ["/assets/birt_report/js/birt_comm.js", "/assets/birt_report/js/birt_report.js"]

boot_session = "birt_report.core.BirtWhitelist.boot_session"
write_file = "birt_report.utils.file.write_file_rptdesign"
delete_file_data_content = "birt_report.utils.file.delete_file_rptdesign"
# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

before_install = "birt_report.utils.utils.before_install"
# before_install = "birt_report.install.before_install"
# after_install = "birt_report.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "birt_report.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.core.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.core.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"birt_report.tasks.all"
# 	],
# 	"daily": [
# 		"birt_report.tasks.daily"
# 	],
# 	"hourly": [
# 		"birt_report.tasks.hourly"
# 	],
# 	"weekly": [
# 		"birt_report.tasks.weekly"
# 	]
# 	"monthly": [
# 		"birt_report.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "birt_report.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.core.doctype.event.event.get_events": "birt_report.event.get_events"
# }


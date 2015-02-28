frappe.provide("birt");

birt.CommunicationComposer = Class.extend({
	init: function(opts) {
		$.extend(this, opts)
        var rname = this.birt_doc.report_name
        this.birt_formats = this.list[rname].formats;
		this.make();
	},
	make: function() {
		var me = this;
		this.dialog = new frappe.ui.Dialog({
			title: __("Add Reply") + ": " + (this.subject || ""),
			no_submit_on_enter: true,
			fields: [
				{label:__("To"), fieldtype:"Data", reqd: 1, fieldname:"recipients",
					description:__("Email addresses, separted by commas")},
				{label:__("Subject"), fieldtype:"Data", reqd: 1,
					fieldname:"subject"},
				{label:__("Standard Reply"), fieldtype:"Link", options:"Standard Reply",
					fieldname:"standard_reply"},
				{label:__("Message"), fieldtype:"Text Editor", reqd: 1,
					fieldname:"content"},
				{label:__("Send As Email"), fieldtype:"Check",
					fieldname:"send_email"},
				{label:__("Communication Medium"), fieldtype:"Select",
					options: ["Phone", "Chat", "Email", "SMS", "Visit", "Other"],
					fieldname:"communication_medium"},
                {label:__("Format"), fieldtype:"Select", options: this.birt_formats, fieldname: "birt_format"},
				{label:__("Sent or Received"), fieldtype:"Select",
					options: ["Received", "Sent"],
					fieldname:"sent_or_received"},
				{label:__("Send"), fieldtype:"Button",
					fieldname:"send"},
				{label:__("Send Me A Copy"), fieldtype:"Check",
					fieldname:"send_me_a_copy"},
				{label:__("Attach Document Print"), fieldtype:"Check",
					fieldname:"attach_document_print"},
				{label:__("Select Print Format"), fieldtype:"Select",
					fieldname:"select_print_format"},
				{label:__("Select Attachments"), fieldtype:"HTML",
					fieldname:"select_attachments"}
			]
		});

		this.dialog.$wrapper.find("[data-edit='outdent']").remove();
		this.dialog.get_input("send").addClass("btn-primary");


		$(document).on("upload_complete", function(event, attachment) {
			if(me.dialog.display) {
				var wrapper = $(me.dialog.fields_dict.select_attachments.wrapper);

				// find already checked items
				var checked_items = wrapper.find('[data-file-name]:checked').map(function() {
					return $(this).attr("data-file-name");
				});

				// reset attachment list
				me.setup_attach();

				// check latest added
				checked_items.push(attachment.file_name);

				$.each(checked_items, function(i, filename) {
					wrapper.find('[data-file-name="'+ filename +'"]').prop("checked", true);
				});
			}
		})
		this.prepare();
		this.dialog.show();

	},
	prepare: function() {
		this.setup_print();
		this.setup_attach();
		this.setup_email();
		this.setup_autosuggest();
		this.setup_last_edited_communication();
		this.setup_standard_reply();
		$(this.dialog.fields_dict.recipients.input).val(this.recipients || "").change();
		$(this.dialog.fields_dict.subject.input).val(this.subject || "").change();
		this.setup_earlier_reply();
	},

	setup_standard_reply: function() {
		var me = this;
		this.dialog.get_input("standard_reply").on("change", function() {
			var standard_reply = $(this).val();
			var prepend_reply = function() {
				var content_field = me.dialog.fields_dict.content;
				var content = content_field.get_value() || "";
				content_field.set_input(
					frappe.standard_replies[standard_reply]
						+ "<br><br>" + content);
			}
			if(frappe.standard_replies[standard_reply]) {
				prepend_reply();
			} else {
				$.ajax({
					url:"/api/resource/Standard Reply/" + standard_reply,
					statusCode: {
						200: function(data) {
							frappe.standard_replies[standard_reply] = data.data.response;
							prepend_reply();
						}
					}
				});
			}
		});
	},

	setup_last_edited_communication: function() {
		var me = this;
		this.dialog.onhide = function() {
			if(cur_frm && cur_frm.docname) {
				if (!frappe.last_edited_communication[cur_frm.doctype]) {
					frappe.last_edited_communication[cur_frm.doctype] = {};
				}
				frappe.last_edited_communication[cur_frm.doctype][cur_frm.docname] = {
					recipients: me.dialog.get_value("recipients"),
					subject: me.dialog.get_value("subject"),
					content: me.dialog.get_value("content"),
				}
			}
		}

		this.dialog.onshow = function() {
			if (cur_frm && cur_frm.docname &&
				(frappe.last_edited_communication[cur_frm.doctype] || {})[cur_frm.docname]) {

				c = frappe.last_edited_communication[cur_frm.doctype][cur_frm.docname];
				me.dialog.set_value("subject", c.subject || "");
				me.dialog.set_value("recipients", c.recipients || "");
				me.dialog.set_value("content", c.content || "");
			}
		}

	},
	setup_print: function() {
		// print formats
		var fields = this.dialog.fields_dict;

		// toggle print format
		$(fields.attach_document_print.input).click(function() {
			$(fields.select_print_format.wrapper).toggle($(this).prop("checked"));
		});

		// select print format
		$(fields.select_print_format.wrapper).toggle(false);

		if (cur_frm) {
			$(fields.select_print_format.input)
				.empty()
				.add_options(cur_frm.print_preview.print_formats)
				.val(cur_frm.print_preview.print_formats[0]);
		} else {
			$(fields.attach_document_print.wrapper).toggle(false);
		}

	},
	setup_attach: function() {
		if (!cur_frm) return;

		var fields = this.dialog.fields_dict;
		var attach = $(fields.select_attachments.wrapper);

		var files = cur_frm.get_files();
		if(files.length) {
			$("<p><b>"+__("Add Attachments")+":</b></p>").appendTo(attach.empty());
			$.each(files, function(i, f) {
				if (!f.file_name) return;

				$(repl("<p class='checkbox'><label style='margin-right: 3px;'><input type='checkbox' \
					data-file-name='%(name)s'> %(file_name)s</label> <a href='%(file_url)s' target='_blank' class='text-muted'> <i class='icon-share'></i></p>", f))
					.appendTo(attach)
			});
		}
	},
	setup_email: function() {
		// email
		var me = this;
		var fields = this.dialog.fields_dict;

		if(this.attach_document_print) {
			$(fields.send_me_a_copy.input).click();
			$(fields.attach_document_print.input).click();
			$(fields.select_print_format.wrapper).toggle(true);
		}

		$(fields.send_email.input).prop("checked", true)

		// toggle print format
		$(fields.send_email.input).click(function() {
			$(fields.communication_medium.wrapper).toggle(!!!$(this).prop("checked"));
			$(fields.sent_or_received.wrapper).toggle(!!!$(this).prop("checked"));
			$(fields.send.input).html($(this).prop("checked") ? "Send" : "Add Communication");
		});

		// select print format
		$(fields.communication_medium.wrapper).toggle(false);
		$(fields.sent_or_received.wrapper).toggle(false);

		$(fields.send.input).click(function() {
			var btn = this;
			var form_values = me.dialog.get_values();
			if(!form_values) return;

			var selected_attachments = $.map($(me.dialog.wrapper)
				.find("[data-file-name]:checked"), function(element) {
					return $(element).attr("data-file-name");
				})

			if(form_values.attach_document_print) {
				if (cur_frm && cur_frm.print_preview.is_old_style(form_values.select_print_format || "")) {
					cur_frm.print_preview.with_old_style({
						format: form_values.select_print_format,
						callback: function(print_html) {
							me.send_email(btn, form_values, selected_attachments, print_html);
						}
					});
				} else {
					me.send_email(btn, form_values, selected_attachments, null, form_values.select_print_format || "");
				}

			} else {
				me.send_email(btn, form_values, selected_attachments);
			}
		});
	},

	send_email: function(btn, form_values, selected_attachments, print_html, print_format) {
		var me = this;
        this.birt_doc.pformat = form_values.birt_format;
        
		if(!form_values.attach_document_print) {
			print_html = null;
			print_format = null;
		}

		if(form_values.send_email) {
			if(cur_frm && !frappe.model.can_email(me.doc.doctype, cur_frm)) {
				msgprint(__("You are not allowed to send emails related to this document"));
				return;
			}

			form_values.communication_medium = "Email";
			form_values.sent_or_received = "Sent";
		};

		return frappe.call({
			method:"birt_report.core.BirtWhitelist.birt_make",
			args: {
				sender: [frappe.user_info(user).fullname, frappe.boot.user.email],
				recipients: form_values.recipients,
				subject: form_values.subject,
				content: form_values.content,
				doctype: me.doc.doctype,
				name: me.doc.name,
				send_me_a_copy: form_values.send_me_a_copy,
				send_email: form_values.send_email,
				print_html: print_html,
				print_format: print_format,
				communication_medium: form_values.communication_medium,
				sent_or_received: form_values.sent_or_received,
				attachments: selected_attachments,
                birt_doc: me.birt_doc,
                docdata: me.docdata,
                rtype: me.rtype
			},
			btn: btn,
			callback: function(r) {
				if(!r.exc) {
					if(form_values.send_email)
						msgprint(__("Email sent to {0}", [form_values.recipients]));
					me.dialog.hide();

					if (cur_frm) {
						if (cur_frm.docname && (frappe.last_edited_communication[cur_frm.doctype] || {})[cur_frm.docname]) {
							delete frappe.last_edited_communication[cur_frm.doctype][cur_frm.docname];
						}
						cur_frm.reload_doc();
					}
				} else {
					msgprint(__("There were errors while sending email. Please try again."));
				}
			}
		});
	},

	setup_earlier_reply: function() {
		var fields = this.dialog.fields_dict;
		var comm_list = (cur_frm && cur_frm.communication_view)
			? cur_frm.communication_view.list
			: [];
		var signature = frappe.boot.user.email_signature || "";

		if(!frappe.utils.is_html(signature)) {
			signature = signature.replace(/\n/g, "<br>");
		}

		if(this.real_name) {
			this.message = '<p>'+__('Dear') +' ' + this.real_name + ",</p>" + (this.message || "");
		}

		var reply = (this.message || "")
			+ "<p></p>"	+ signature;

		if(comm_list.length > 0) {
			fields.content.set_input(reply
				+ "<p></p>"
				+"-----"+__("In response to")+"-----"
				+"<p style='font-size: 11px; color: #888'>"+__("Please reply above this line or remove it if you are replying below it")+"</p><br><br>"
				+ comm_list[0].content);
		} else {
			fields.content.set_input(reply);
		}
	},
	setup_autosuggest: function() {
		var me = this;

		function split( val ) {
			return val.split( /,\s*/ );
		}
		function extractLast( term ) {
			return split(term).pop();
		}

		$(this.dialog.fields_dict.recipients.input)
			.bind( "keydown", function(event) {
				if (event.keyCode === $.ui.keyCode.TAB &&
						$(this).data( "autocomplete" ).menu.active ) {
					event.preventDefault();
				}
			})
			.autocomplete({
				source: function(request, response) {
					return frappe.call({
						method:'frappe.utils.email_lib.get_contact_list',
						args: {
							'select': "email_id",
							'from': "Contact",
							'where': "email_id",
							'txt': extractLast(request.term).value || '%'
						},
						callback: function(r) {
							response($.ui.autocomplete.filter(
								r.cl || [], extractLast(request.term)));
						}
					});
				},
				appendTo: this.dialog.$wrapper,
				focus: function() {
					// prevent value inserted on focus
					return false;
				},
				select: function( event, ui ) {
					var terms = split( this.value );
					// remove the current input
					terms.pop();
					// add the selected item
					terms.push( ui.item.value );
					// add placeholder to get the comma-and-space at the end
					terms.push( "" );
					this.value = terms.join( ", " );
					return false;
				}
			});
	}
});


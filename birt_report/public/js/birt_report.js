frappe.provide("birt");

birt.pending_reports = [];

birt.poll_count = 0;

birt.pages = {};

birt_report_formats = {pdf:"icon-file-pdf", "docx": "icon-file-word", doc: "icon-file-word", xls:"icon-file-excel", xlsx:"icon-file-excel",
						/*ppt:"icon-file-powerpoint", pptx:"icon-file-powerpoint",*/ odt: "icon-file-openoffice", ods: "icon-libreoffice",
	 					rtf:"fontello-icon-doc-text", email: "icon-envelope-alt", submenu:"icon-grid"};

birt.download = function(url, data, method){
    //url and data options required
    if( url && data ){
        //data can be string of parameters or array/object
        data = typeof data == 'string' ? data : jQuery.param(data);
        //split params into form inputs
        var inputs = '';
        jQuery.each(data.split('&'), function(){
            var pair = this.split('=');
            inputs+='<input type="hidden" name="'+ pair[0] +'" value="'+ pair[1] +'" />';
        });
        //send request
        jQuery('<form target="_blank" action="'+ url +'" method="'+ (method||'post') +'">'+inputs+'</form>')
        .appendTo('body').submit().remove();
        
        console.log("sented request %s %s args %s", url, inputs)
    };
};

//jasper.get_jasper_report = function(path, method, format, data){
birt.get_birt_report = function(method, data, doc, type){
    //var format = format || 'pdf';
    //var args = 'path='+ encodeURIComponent(path) +'&format='+ format;
    var args = "";
    if (data){
        args = args + 'data=' + encodeURIComponent(JSON.stringify(data));
        console.log("args ", args);
    };
    
    if (doc){
        args = args + '&doc=' + encodeURIComponent(JSON.stringify(doc));
    };
    
    if(type){
        args = args + '&type=' + type;
    };
    
	birt.download("/api/method/birt_report.core.BirtWhitelist." + method, args);
};

birt.run_birt_report = function(method, data, doc, type){
    //var format = format || 'pdf';
    //var args = 'path='+ encodeURIComponent(path) +'&format='+ format;
    var df = new $.Deferred();
    frappe.call({
	       "method": "birt_report.core.BirtWhitelist." + method,
	       args:{
               data: data,
	           docdata: doc,
               rtype: type
	       },
	       callback: function(response_data){
			   console.log("resolved ", response_data);
               if (response_data && response_data.message){
                   var msg = response_data.message;
                   if (msg[0].status === "ready"){
                       //var reqdata = {reqId: msg.requestId, expId: msg.ids[0].id, fileName: msg.ids[0].fileName};
                       //console.log("reqdata ", reqdata)
                       //jasper.get_jasper_report("get_report", reqdata, null, null);
                       //df.resolve(msg);
                       $banner = frappe.ui.toolbar.show_banner(__("Please wait while i'm processing your report. I will notify you when is ready!"))
                       timeout = setTimeout(birt.close_banner, 1000*15, $banner);
                       birt.pending_reports.push(msg);
                       console.log("setting timeout!!!");
                       //jasper.jasper_report_ready(msg, $banner, timeout)
                       setTimeout(birt.birt_report_ready, 1000*10, msg, $banner, timeout);
                       //jasper.print("get_report", reqdata);
                   }else{
                       console.log("polling_report!!!");
                       $banner = frappe.ui.toolbar.show_banner(__("Please wait while i'm processing your report. I will notify you when is ready!"))
                       timeout = setTimeout(birt.close_banner, 1000*15, $banner);
                       birt.polling_report(msg, $banner, timeout);
                   }
               }
		   }
     });
     
     return df;
};

//TODO: must be tested!!!
birt.polling_report = function(data, $banner, timeout){
    var reqids = [];
    for(var i=0; i<data.length; i++){
        reqids.push(data[i].requestId);
    };
    var poll_data = {reqIds: reqids, reqtime: data[0].reqtime, pformat: data[0].pformat, origin: data[0].origin}
    //check only one
    frappe.call({
	       "method": "birt_report.core.BirtWhitelist.report_polling",
	       args:{
               data: poll_data,
	       },
	       callback: function(response_data){
			   console.log("polling response ", response_data);
               console.log("local report ready!!! ", response_data.message[0].status);
               if (response_data && response_data.message){
                   var msg = response_data.message;
                   if (msg[0].status === "ready"){
					   birt.poll_count = 0;
                       birt.birt_report_ready(msg, $banner, timeout);
                   }else if (!msg[0].status){
                       //setTimeout(jasper.polling_report, 1000*5, data, $banner, timeout);
					   console.log("polling not ready count ", birt.poll_count);
					   if (birt.poll_count <= 9 ){
						   birt.poll_count++;
						   var ptime = parseInt(frappe.boot.birt_reports_list.birt_polling_time);
						   console.log("ptime ", ptime);
						   setTimeout(birt.polling_report, ptime, data, $banner, timeout);
						   return;
					   };
					   birt.poll_count = 0;
					   msgprint(msg[0].value, __("Report error! The report is taking too long... "));
                       //jasper.polling_report(data, $banner, timeout);
                   }else{
					   birt.poll_count = 0;
                       msgprint(msg[0].value, __("Report error "));
                   }
               }
		   }
     });
};

birt.close_banner = function($banner){
    $banner.find(".close").click();
};

birt.birt_report_ready = function(msg, $old_banner, timeout){
    //$old_banner = $('header .navbar').find(".toolbar-banner");
    $old_banner.find(".close").click();
    clearTimeout(timeout);
    $banner = frappe.ui.toolbar.show_banner(__("Your report is ready to download! Click to ") + '<a class="download_report">download</a>')
    $banner.css({background: "lightGreen", opacity: 0.9});
	$banner.find(".download_report").click(function() {
        birt.getReport(msg);
		birt.close_banner($banner);
	});
};

birt.getReport = function(msg){
    
    /*var reqIds = [];
    var expIds = [];
    for (var i =0; i<msg.length;i++){
        reqIds.push(msg[i].requestId);
        //assume reqids = expids
        if (msg[i].ids)
            expIds.push(msg[i].ids[0].id);
        else
            expIds.push("");
        
    };*/
    
    //var t = {reqId: reqIds, expId: expIds, fileName: msg[0].ids[0].fileName, reqtime: msg[0].reqtime, pformat: msg[0].pformat}
    //var reqdata = t;
	var reqdata = msg[0];
    console.log("this reqdata ", reqdata)
    
    var request = "/api/method/birt_report.core.BirtWhitelist.get_report?data="+encodeURIComponent(JSON.stringify(reqdata));
    console.log("request ", request)
    w = window.open(request);
	if(!w) {
		msgprint(__("Please enable pop-ups"));
	}
};

birt.getList = function(page, doctype, docnames){
	var jpage = frappe.pages[page];
	if(jpage && birt.pages[page]){
		list = birt.pages[page];
		//console.log("exist lista ", list);
		setBirtDropDown(list, birt.getOrphanReport);
	}else{
		method = "birt_report.core.BirtWhitelist.get_reports_list";
		data = {doctype: doctype, docnames: docnames};
		console.log("pedido for doctype %s docname %s ", doctype, docnames);
		birt.birt_make_request(method, data,function(response_data){
			console.log("resposta for doctype docname ", response_data, jpage, page);
			//frappe.pages[page]["jasper"] = response_data.message;
			birt.pages[page] = response_data.message;
			setBirtDropDown(response_data.message, birt.getOrphanReport);
		});
	};
};

$(window).on('hashchange', function() {
	var route = frappe.get_route();
	console.log("hashchange !!", route);
	var len = route.length;
	var doctype, docname;
	var list = {};
	var callback;
	
	console.log("route ", len)
	
	if (len > 2 && route[0] === "Form"){
		var method;
		var data;
		doctype = route[1];
		docname = route[2];
		doc_new = docname.search("New");
		if (doc_new === -1 || doc_new > 0){
			//var page = [route[0], doctype].join("/");
            var page = birt.get_page();
			birt.getList(page, doctype, [docname]);
			return;
		}
	}else if(len > 1 && route[0] === "List"){
		doctype = route[1];
		//var page = [route[0], doctype].join("/");
        var page = birt.get_page();
		//jasper.setEventClick(page);
		console.log("page ", page);
		//docnames = jasper.getCheckedNames(page);
		//if(docnames.length > 0){
		birt.getList(page, doctype, []);
		return;
		/*}else{
			msgprint(__("Please, select at list one name"), __("Jasper Report"));
		}*/
		
	}else if(route[0] === ""){
		list = frappe.boot.birt_reports_list;
		callback = birt.getOrphanReport;
		//setJasperDropDown(list);
	}
    
	setBirtDropDown(list, callback);
	
});

birt.get_page = function(){
    var route = frappe.get_route();
	var doctype = route[1];
	var page = [route[0], doctype].join("/");
    return page;
};

birt.get_doc = function(doctype, docname){
    var df = new $.Deferred();
    var doctype = doctype || "Birt Report"
	var method = "birt_report.core.BirtWhitelist.get_doc";
    var data = {doctype: doctype, docname: docname};
    birt.birt_make_request(method, data, function(response_data){
        console.log("resposta for doctype docname ", response_data);
        df.resolve(response_data['data']);
    });
    
    return df;
};


setBirtDropDown = function(list, callback){
	
	$("#birt_report_list").remove();
	
	if (list && !$.isEmptyObject(list) && list.size > 0){
		var size = list.size;
		
		var html = '<li class="dropdown" id="birt_report_list">'
			+ '<a class="dropdown-toggle" href="#" data-toggle="dropdown" title="Birt Report" onclick="return false;">'
				+ '<span><img src="assets/birt_report/images/birt-logo.svg" style="max-width: 32px; max-height: 32px; margin: -2px 0px;">  </img></span>'
		 + '<span> <span class="badge" id="brcount">' + size +'</span></span></span></a>'
			+ '<ul class="dropdown-menu" id="brmenu">';
	
			//var jq = $("#jrcount", html).text(size)
			//console.log("jq ", jq)
			var flen;
			var icon_file;
		    list = sortObject(list);
			for(var key in list){
				//if(key !== "size" || key !="jasper_polling_time"){
				if(list[key] !== null && typeof list[key] === "object"){
					flen = list[key].formats.length;
					var skey = shorten(key, 35);
					html = html + birt.make_menu(list, key, skey);
				};
			};
		
			html = html + '</ul></li>';
			//console.log("html ", html);
			
			function clicked(ev){
				ev.preventDefault();
				//ev.stopPropagation();
				/*if (last_menu_report){
					$(last_menu_report).popover('hide')
				};
				last_menu_report = ev.currentTarget;
				*/
				console.log("data from ev: ", ev.target);
				var data = $(ev.target).data();
				var br_format = data.br_format;
				var br_name = data.br_name;
				console.log("br_format ", br_format, br_name, list);
				//$(".nav.navbar-nav.navbar-right").popover({content:"teste content ", title:"popover jasper", placement:"left"});
				
				//$(ev.currentTarget).popover({content:"teste content ", title:"popover jasper", placement:"right"});
				//$(ev.currentTarget).popover('show');
				callback({br_format: data.br_format, br_name: data.br_name, list: list}, ev);
			};
			
			$(".nav.navbar-nav.navbar-right").append(html)
			//$(".nav.navbar-nav.navbar-right").prepend(html)
			$(".nav.navbar-nav.navbar-right .brreports").on("click", clicked);
	};
		
};

birt.check_for_ask_param = function(rname, callback){
    var robj = frappe.boot.birt_reports_list[rname];
    if (robj === undefined){
        var page = birt.get_page();
        robj = birt.pages[page];
    }
    if (robj === undefined)
        return;

    var ret;
    if (robj.params && robj.params.length > 0){
        ret = birt.make_dialog(robj, rname + " parameters", callback);
    }else{
        callback();
    }
    
    console.log("ret: ", ret);
};

birt.make_menu = function(list, key, skey){
	//jasper_report_formats[list[key].formats[0]]
	var f = list[key].formats;
    var email = list[key].email;
	//var t = list[key].formats.join(":");
	var icon_file = [];
	var html = "";
	for(var i=0; i < f.length; i++){
		var type = f[i];
		icon_file.push(repl('<i title="%(title)s" data-br_format="%(f)s" data-br_name="%(mykey)s" class="birt-%(type)s"></i>', {title:key + " - " + type, mykey:key, f:f[i], type: birt_report_formats[type]}));
	};
    if (email === 1){
        console.log("email ", email);
        icon_file.push(repl('<i title="%(title)s" data-br_format="%(f)s" data-br_name="%(mykey)s" class="%(type)s"></i>', {title: "send by email", mykey:key, f:"email", type: birt_report_formats["email"]}));
    }
	//data-jr_format='+ t + ' data-jr_name="'+ key + '" class="jrreports"
	html = html + '<li>'
 	   + repl('<a class="brreports" href="#" data-br_format="%(f)s" data-br_name="%(mykey)s"',{mykey:key, f:f[0]}) +' title="'+ key +' - pdf" >'+ icon_file.join(" ") + " " + skey  + '</a>'
 	   +'</li>';
	 
	return html;
};


birt.getOrphanReport = function(data, ev){
	var route = frappe.get_route();
	var len = route.length;
	var docnames;
	if (len > 1 && route[0] === "List"){
		var doctype = route[1];
		var page = [route[0], doctype].join("/");
		docnames = birt.getCheckedNames(page);
		if (docnames.length === 0)
		{
			msgprint(__("Please, select at list one name"), __("Birt Report"));
			return;
		};
	}else if(len > 2 && route[0] === "Form"){
		if (cur_frm){
			docnames = [cur_frm.doc.name];
		}else{
			msgprint(__("To print this doc you must be in a form."), __("Birt Report"));
			return;
		}
	}
    var params;
    birt.check_for_ask_param(data.jr_name, function(d){
    	console.log("docnames ", docnames);
        var jr_format = data.jr_format; 
    	var args = {fortype: "doctype", report_name: data.jr_name, doctype:"Birt Reports", name_ids: docnames, pformat: jr_format, params: d};
        if(jr_format === "email"){
            birt.email_doc("Birt Email Doc", cur_frm, args, data.list, route[0], route[0]);
        }else{
            birt.run_birt_report("run_report", args, route[0], route[0]);
        }
    });
};

function shorten(text, maxLength) {
    var ret = text;
    if (ret.length > maxLength) {
        ret = ret.substr(0,maxLength-3) + "...";
    }
    return ret;
}

function sortObject(o) {
    var sorted = {},
    key, a = [];

    for (key in o) {
    	if (o.hasOwnProperty(key)) {
    		a.push(key);
    	}
    }

    a.sort();

    for (key = 0; key < a.length; key++) {
    	sorted[a[key]] = o[a[key]];
    }
    return sorted;
};

birt.birt_make_request = function(method, data, callback){

    frappe.call({
	       method: method,
	       args: data,
	       callback: callback
     });
};

$(document).on( 'app_ready', function(){
    console.log("frappe is ready ", birt);
	$(window).trigger('hashchange');
    var list = frappe.boot.birt_reports_list;
	setBirtDropDown(list, function(data, ev){
		console.log("was clicked !! ", $(ev.target).data())
		birt.getOrphanReport(data, ev);
	});
	window.open("");
});

birt.make_dialog = function(doc, title, callback){
	function ifyes(d){
		console.log("ifyes return ", d.get_values());
        if (callback){
            callback(d.get_values());
        }
	};
	function ifno(){
		console.log("ifno return ");
        if (callback){
            callback();
        }
	};
	
    var fields = [];
	//var fields = [{label:"teste 1", fieldname:"teste 1", fieldtype:"Data"}, {label:"teste2", fieldname:"teste 2", fieldtype:"Check", description:"choose one"}];
	var params = doc.params;
	for (var i=0; i < params.length; i++){
		var param = doc.params[i];
		fields.push({label:param.name, fieldname:param.name, fieldtype:param.birt_param_type=="String"? "Data": param.birt_param_type,
		 	description:param.birt_param_description || "", default:param.birt_param_value});
	};
	var d = birt.ask_dialog(title, doc.message, fields, ifyes, ifno);
	return d;
}

birt.ask_dialog = function(title, message, fields, ifyes, ifno) {
	var html = {fieldtype:"HTML", options:"<p class='frappe-confirm-message'>" + message + "</p>"};
	fields.splice(0,0,html);
	var d = new frappe.ui.Dialog({
		title: __(title),
		fields: fields,
		primary_action: function() { d.hide(); ifyes(d); }
	});
	d.show();
	if(ifno) {
		d.$wrapper.find(".modal-footer .btn-default").click(ifno);
	}
	return d;
}

birt.getChecked = function(name){
	return $(frappe.pages[name]).find("input:checked");
}

birt.getCheckedNames = function(page){
	var names = [];
	var checked = birt.getChecked(page);
	var elems_a = checked.siblings("a");
	elems_a.each(function(i,el){
		var t = unescape($(el).attr("href")).slice(1);
		var s = t.split("/");
		names.push(s[s.length - 1]);
	});
	
	return names;
}


// jasper_doc
birt.email_doc = function(message, curfrm, birt_doc, list, route0, route1) {
    //var args = {fortype: "doctype", report_name: data.jr_name, doctype:"Jasper Reports", name_ids: docnames, pformat: data.jr_format, params: d};
    
    if (curfrm){
    	new birt.CommunicationComposer({
    		doc: curfrm.doc,
    		subject: __(curfrm.meta.name) + ': ' + curfrm.docname,
    		recipients: curfrm.doc.email || curfrm.doc.email_id || curfrm.doc.contact_email,
    		attach_document_print: true,
    		message: message,
    		real_name: curfrm.doc.real_name || curfrm.doc.contact_display || curfrm.doc.contact_name,
            birt_doc: birt_doc,
	        docdata: route0,
            rtype: route1,
            list: list
    	});
    }else{
    	new birt.CommunicationComposer({
    		doc: {doctype: birt_doc.doctype, name: birt_doc.report_name},
    		subject: birt_doc.doctype + ': ' + birt_doc.report_name,
    		recipients: undefined,
    		attach_document_print: false,
    		message: message,
    		real_name: "",
            birt_doc: birt_doc,
	        docdata: route0,
            rtype: route1,
            list: list
    	});
    }
}



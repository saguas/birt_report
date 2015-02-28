frappe.provide("birt");

cur_frm.cscript.refresh = function(doc){
    var cs = cur_frm.cscript;
    //$(cur_frm.get_field("query_html").wrapper).find('.query').text('luis')
    //this.set_value("query_html", "12234");
    //fortype can be "doctype" or "report"
    //var args = {fortype: "doctype", report_name:"Teste 1", doctype:"Jasper Reports", name_ids:["Administrator", "Guest"], pformat:"pdf"};
    //var df = jasper.run_jasper_report("run_report", args, null);
    
    //cur_frm.conn_test();
    
    cs.show_fields(doc);
    
    var query = doc.query != undefined? doc.query:""
    var code = '<div class="panel panel-default">'
                 + '<div class="panel-heading">'
                    + '<h3 class="panel-title">SQL</h3>'
                 + '</div>'
                 + '<div class="panel-body">'
                        + '<pre class="bs-callout-bg bs-callout-warning-bg">' + query + '</pre>'
                 + '</div>'
             + '</div>'

    //cur_frm.fields_dict.query_html.$wrapper.html("<div class='panel panel-primary'><pre class='bg-warning'>" + doc.query + "</pre></div>")
    cur_frm.fields_dict.query_html.$wrapper.html(code)
    console.log("query: ", code)
}

cur_frm.cscript.show_fields = function(doc){
    var origin = doc.jasper_report_origin;
   if(doc.__islocal){//never saved
        hide_field(["birt_upload_rptdesign"]);
        //cur_frm.refresh_field("jasper_report_path");
    }
    
};

cur_frm.cscript.onload = function(doc){
    //$('.query').text("luis filipe")
    //cur_frm.fields_dict.query_html.$wrapper.html("<p>Luis</p>")
    
}

//this is for testing liveupdates with threads, pubsub and queue
//must be ajax because green progress line in desk
cur_frm.conn_test = function(){
    var opts = {};
    var ajax_args = {
    	url: opts.url || frappe.request.url,
        data:{cmd: "birt_report.birt_reports.run_local_report.conn_test"},
    	type: 'POST',
    	dataType: opts.dataType || 'json',
    	async: opts.async
    };
    $.ajax(ajax_args).done(
        function(response_data){
            console.log("conn_test response ", response_data);
        }
    );
    
    /*frappe.call({
	       "method": "jasper_erpnext_report.jasper_reports.run_local_report.conn_test",
           args: {},
           progress_bar: 0,
           show_spinner: 1,
	       callback: function(response_data){
			   console.log("conn_test response ", response_data);
		   }
     });*/
    
};

cur_frm.cscript["get_report"] = function(doc, dt, dn){
    email_doc = frappe.get_doc("Birt Email Report", dn);
    console.log("get_reports ", doc, dt, dn);
    console.log("get_docs ", email_doc);
    birt.getBirtEmailReport(email_doc.birt_report_path, email_doc.birt_file_name);
};



birt.getBirtEmailReport = function(filepath, filename){
    
    var reqdata = {filepath: filepath, filename: filename};
    var request = "/api/method/birt_report.core.BirtWhitelist.get_birt_email_report?data="+encodeURIComponent(JSON.stringify(reqdata));
    console.log("request ", request)
    w = window.open(request);
	if(!w) {
		msgprint(__("Please enable pop-ups"));
	}
};


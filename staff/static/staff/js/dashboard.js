$(function() {
    toast = $(".toast");
    if (toast.length) {
	toast.toast({delay: 5000}).toast("show");
    }
});

$(function() {
    if ($("#id_hubspot_contact").length) {
	const hs_contact_link = $("#id_hubspot_contact");
	const contact_email = hs_contact_link.attr("data-email");
	const hs_apikey = hs_contact_link.attr("data-hubspot-apikey");
	const hs_url = "https://api.hubapi.com/contacts/v1/contact/email/" +
	      contact_email + "/profile";

	$.getJSON(hs_url, {
	    hapikey: hs_apikey,
	}).done(function(json) {
	    console.log(json);
	}).fail(function(xhr, status, errorThrown) {
	    console.log( "Error: " + errorThrown );
	    console.log( "Status: " + status );
	    console.dir( xhr );
	});
    }
});

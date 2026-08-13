var onSuccess = function (response) {
    $("#register-submit").removeClass("btn-loading");
    if (response.response.responseCode == 0) {
        notif({
            msg: "<b><i class='fa fa-check fs-20 mr-2'></i></b> You will receive an confirmation email at '" + $('#Email').val() + ".' Please check your inbox in a few minutes (spam/junk folder included). ",
            type: "success",
            position: "left",
        });
        window.location.href = '/account/login'
    }
    else {
        notif({
            msg: "<b><i class='fa fa-close fs-20 mr-2'></i></b> " + response.response.responseMessage,
            type: "error",
            position: "left",
        });
    }

};

var onFailed = function (response) {
    $("#register-submit").removeClass("btn-loading");
   
    notif({
        msg: "<b><i class='fa fa-close fs-20 mr-2'></i></b> " + response.response.responseMessage,
        type: "error",
        position: "left",
    });
};

var onBegin = function (response) {
    $("#register-submit").addClass("btn-loading");
};


$('#CountryId').change(function () {

    var selectedValue = this.value;

    $.ajax({
        type: "GET",
        url: "/generic/GetCountryById?countryId=" + selectedValue,
        cache: false,
        success: function (data) {
            $("#Code").val("+" + data.result.countryPhoneCode);
        },
    });

});

function GetCountries(target) {
    $.ajax({
        type: "GET",
        url: "/generic/GetCountries",
        cache: false,
        success: function (data) {
            $(target).empty()
            $(target).append('<option label="Select Country"></option>')
            for (var i = 0; i < data.result.length; i++) {
                $(target).append("<option value=" + data.result[i].countryId + ">" + data.result[i].countryName + "</option>")
            }
        },
    });
}

GetCountries("#CountryId");

function ShowPassword() {
    var type = $("#password").attr("type");
    if (type == 'password') {
        $("#password").attr("type", "text");
        $("#show_password i").removeClass("fa-eye-slash");
        $("#show_password i").addClass("fa-eye");
    } else {
        $("#show_password i").addClass("fa-eye-slash");
        $("#show_password i").removeClass("fa-eye");
        $("#password").attr("type", "password");
    }
}

function ShowConfirmPassword() {
    var type = $("#ConfirmPassword").attr("type");
    if (type == 'password') {
        $("#ConfirmPassword").attr("type", "text");
        $("#show_confirm_password i").removeClass("fa-eye-slash");
        $("#show_confirm_password i").addClass("fa-eye");
    } else {
        $("#show_confirm_password i").addClass("fa-eye-slash");
        $("#show_confirm_password i").removeClass("fa-eye");
        $("#ConfirmPassword").attr("type", "password");
    }
}

$('#FullName').on("paste", function (e) {
    if (e.originalEvent.clipboardData.getData('text').match(/[^\d]/))
        e.preventDefault();
});


//$('#phonea').on('change', function () {

//    var Code = $('#Code').val();
//    var phone = Code + $('#phonea').val();


//    // Regex to check valid
//    // International Phone Numbers
//    let regex = new RegExp(/^[+]{1}(?:[0-9\-\(\)\/\.]\s?){6, 15}[0-9]{1}$/);

//    // if phonenumber
//    // is empty return false
//    if (phone == null) {
//        return "false";
//    }

//    // Return true if the phonenumber
//    // matched the ReGex
//    if (regex.test(phone) == true) {
//        alert(true);
//        return "true";
//    }
//    else {
//        alert(false);
//        return "false";
//    }

//})
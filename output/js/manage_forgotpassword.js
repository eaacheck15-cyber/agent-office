var onSuccess = function (response) {
    $("#register-submit").removeClass("btn-loading");
    if (response.response.responseCode == 0) {
        notif({
            msg: "<b><i class='fa fa-check fs-20 mr-2'></i></b> " + response.response.responseMessage,
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
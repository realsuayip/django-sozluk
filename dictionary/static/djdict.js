$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie != '') {
                let cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    let cookie = jQuery.trim(cookies[i]);
                    // Does this cookie string begin with the name we want?
                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
            // Only send the token to relative URLs i.e. locally.
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});

Notify = (message) => {
    let notifiction = $("#notifications");
    notifiction.html(message);
    notifiction.fadeIn();
    $(notifiction).delay(1600).fadeOut();
};


$("ul#category_view li.nav-item, div#category_view_in a, a#category_view_ls").on('click', function () {
    localStorage.setItem("active_category_safe", $(this).attr("data-safename"));
    $("ul#category_view li").removeClass('active');
    $("div#category_view_in a").removeClass('active');
    $(this).addClass('active');
    localStorage.setItem("active_category", $(this).attr("data-category"));

});


$("ul#category_view li.nav-item, div#category_view_in a.nav-item, a#category_view_ls").on('click', function () {
    letframe_button_reset();
    leftframe_stick($(this).attr("data-category"));

});


$(function () {

    let notification = $("#notifications").attr("data-request-message");
    if (notification) {
        Notify(notification);
    }


    if (localStorage.getItem("active_category")) {
        let category = localStorage.getItem("active_category");
        const navigation_page = localStorage.getItem("navigation_page");
        let selector = $("li[data-category=" + category + "], a[data-category=" + category + "]");
        selector.addClass("active");
        if (selector.attr("data-category") === undefined) {
            // DEFAULT
            // YÜKLENİYOR.
        } else {
            $("#current_category_name").text(selector.attr("data-safename"));
            if (navigation_page) {
                leftframe_stick(category, true, parseInt(navigation_page));
                $("a#show_more").addClass("dj-hidden");
            } else {
                leftframe_stick(category);
            }


        }
    }


    $("#header_search").autocomplete({
        serviceUrl: '/autocomplete/general/',
        preserveInput: true,
        triggerSelectOnValidInput: false,

        onSelect: function (suggestion) {
            window.location.replace("/topic/?q=" + suggestion.value);

        }
    });


    $(".author-search").autocomplete({
        serviceUrl: '/autocomplete/general/',
        triggerSelectOnValidInput: false,
        paramName: "author",

        onSelect: function (suggestion) {
            $("input.author-search").val(suggestion.value);
        }


    });


    $(".send-message-trigger").on("click", ({currentTarget}) => {
        let recipient = $(currentTarget).attr("data-recipient");
        $("input.author-search").val(recipient);
        $("#sendMessageModal").modal('show');
    });
    $("#send_message_btn").on("click", () => {
        $.ajax({
            type: "POST",
            url: "/mesaj/gonder/",
            data: {
                message_body: $("textarea#message_body").val(),
                recipient: $("input.author-search").val()
            },
            success: (data) => {
                Notify(data.detail);
                if (data.success) {
                    $("#sendMessageModal").modal('hide');
                }
            }

        });

    });

});

let mql = window.matchMedia('(max-width: 810px)');

function desktop_view() {

    $("ul#category_view li a, div#category_view_in a, a#category_view_ls").on('click', function (e) {

        e.preventDefault();

    });
}

function mobile_view() {
    $("ul#category_view a, div#category_view_in a").on('click', function () {
        window.location = this.href;
    });
}

if (mql.matches) {
    mobile_view();

} else {
    desktop_view();
}


function screenTest(e) {
    if (e.matches) {
        /* MOBILE switch */
        mobile_view();
    } else {

        desktop_view();
    }
}

mql.addListener(screenTest);

function letframe_button_reset() {
    $("a#show_more").removeClass("dj-hidden");
    $("#lf_pagination_wrapper").addClass("dj-hidden");
    localStorage.removeItem("navigation_page");
}

function leftframe_stick(category = null, extended = false, page = null) {


    // leftframe behaviour on link clicks on desktop.
    let year_select = $("#year_select");
    year_select.css("display", "none");
    year_select.html("");


    if (category == null) {
        console.log("something happened.");
    }


    let api_url = `/category/${category}/`;
    let parameters = "";

    // add parameters for specific slugs

    if (category === "bugun") {
        parameters = "?day=today";
    }

    if (category === "caylaklar") {
        parameters = "?a=caylaklar";
    }


    if (category === "tarihte-bugun") {
        year_select.css("display", "block");
        let years = ["2019", "2018", "2017"];
        for (let year of years) {
            $("#year_select").append(`<option id="${year}">${year}</option>`);
        }

        let selected_year = null;

        if (localStorage.getItem("selected_year")) {
            selected_year = localStorage.getItem("selected_year");
        } else {
            selected_year = years[Math.floor(Math.random() * years.length)];
            localStorage.setItem("selected_year", selected_year);
        }


        year_select.val(selected_year);
        parameters = `?year=${selected_year}`;
    }

    topic_ajax_call(api_url, parameters, extended, page);

}

$("#year_select").on("change", function () {
    let selected_year = this.value;
    localStorage.setItem("selected_year", selected_year);
    //let parameters = `?year=${selected_year}`;
    // let api_url = `/category/tarihte-bugun/`;
    $("a#show_more").removeClass("dj-hidden");
    leftframe_stick("tarihte-bugun");

    //topic_ajax_call(api_url, parameters);
});

class Paginator {
    constructor(items, items_per_page) {
        this.items = items;
        this.items_per_page = items_per_page;
        this.total_pages = Math.ceil(items.length / items_per_page);

    }

    get_page(page) {
        --page;
        return this.items.slice(page * this.items_per_page, (page + 1) * this.items_per_page);

    }

    get range() {
        let range = [];
        for (let i = 1; i <= this.total_pages; i++) {
            range.push(i);
        }
        return range;
    }

}

function topic_ajax_call(api_url, parameters, extended = false, page = null) {
    $("#load_indicator").css("display", "inline-block");
    // extended=true calls ALL of the corresponding topics
    let topic_list = $("ul#topic-list");
    // if extended == true then set extended parameter, if other parameters exist convert ? to &
    let ext_parameter = extended ? `${parameters ? "&" : "?"}extended=yes` : "";
    $.ajax({
        type: "GET",
        url: api_url + parameters + ext_parameter,
        success: function (data) {
            $("#current_category_name").html(localStorage.getItem("active_category_safe"));
            $("#load_indicator").css("display", "none");

            if (data.length === 0) {

                topic_list.html("<small>yok ki</small>");
                $("a#show_more").addClass("dj-hidden");

            } else {

                if (page) {
                    const paginator = new Paginator(data, 2);

                    if (page > paginator.total_pages) {
                        Notify("yok hiç bişi kalmamış");
                    } else {
                        localStorage.setItem("navigation_page", page);
                        const left_frame_select = $("select#left_frame_paginator");
                        left_frame_select.empty();
                        for (const element of paginator.range) {
                            left_frame_select.append($('<option>', {
                                    value: element,
                                    text: element
                                }
                            ));
                        }
                        left_frame_select.val(page);
                        $("#lf_total_pages").html(paginator.total_pages);
                        data = paginator.get_page(page);
                        $("#lf_pagination_wrapper").removeClass("dj-hidden");
                    }

                }
                // default behaviour (no page number is  supplied)
                topic_list.empty();
                for (let i = 0; i < data.length; i++) {
                    let topic_template = `<li class="list-group-item"><a href="${data[i].slug}${parameters}">${data[i].title}<small class="total_entries">${data[i].count ? data[i].count : ''}</small></a></li>`;
                    topic_list.append(topic_template);

                }


            }

        },
        error: function (error) {
            Notify("bir şeyler yanlış gitti");
            $("#load_indicator").css("display", "none");
            console.log(error);
        },
    });
}

$("select#left_frame_paginator").on("change", function () {
    leftframe_stick(localStorage.getItem("active_category"), true, this.value);
});

$("#lf_total_pages").on("click", function () {
    $("select#left_frame_paginator").val($(this).html()).trigger("change");

});

$("#lf_navigate_before").on("click", function () {
    const selected = parseInt($("select#left_frame_paginator").val());
    if (selected - 1 > 0) {
        $("select#left_frame_paginator").val(selected - 1).trigger("change");
    }
});
$("#lf_navigate_after").on("click", function () {
    const selected = parseInt($("select#left_frame_paginator").val());
    const max = parseInt($("#lf_total_pages").html());
    if (selected + 1 <= max) {
        $("select#left_frame_paginator").val(selected + 1).trigger("change");
    }
});


$("a#show_more").on("click", function () {
    leftframe_stick(localStorage.getItem("active_category"), true, 2);
    $(this).addClass("dj-hidden");
});


// https://stackoverflow.com/questions/5999118/how-can-i-add-or-update-a-query-string-parameter
function updateQueryStringParameter(uri, key, value) {
    let re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
    let separator = uri.indexOf('?') !== -1 ? "&" : "?";
    if (uri.match(re)) {
        return uri.replace(re, '$1' + key + "=" + value + '$2');
    } else {
        return uri + separator + key + "=" + value;
    }
}


$("select#entry_list_page").on("change", function () {
    window.location = updateQueryStringParameter(location.href, "page", this.value);
});

jQuery.fn.extend({
    insertAtCaret: function (myValue) {
        return this.each(function (i) {
            if (document.selection) {
                // Internet Explorer
                this.focus();
                var sel = document.selection.createRange();
                sel.text = myValue;
                this.focus();
            } else if (this.selectionStart || this.selectionStart === '0') {
                //For browsers like Firefox and Webkit based
                let startPos = this.selectionStart;
                let endPos = this.selectionEnd;
                let scrollTop = this.scrollTop;
                this.value = this.value.substring(0, startPos) + myValue + this.value.substring(endPos, this.value.length);
                this.focus();
                this.selectionStart = startPos + myValue.length;
                this.selectionEnd = startPos + myValue.length;
                this.scrollTop = scrollTop;
            } else {
                this.value += myValue;
                this.focus();
            }
        });
    },
    toggleText: function (a, b) {
        return this.text(this.text() === b ? a : b);
    }


});


const replace_text = (element_id, replacement_type) => {
    let txtarea = document.getElementById(element_id);
    let start = txtarea.selectionStart;
    let finish = txtarea.selectionEnd;
    let allText = txtarea.value;
    let sel = allText.substring(start, finish);
    if (!sel) {
        return false;
    } else {
        if (replacement_type === "bkz") {
            txtarea.value = allText.substring(0, start) + `(bkz: ${sel})` + allText.substring(finish, allText.length);
        } else if (replacement_type === "hede") {
            txtarea.value = allText.substring(0, start) + `\`${sel}\`` + allText.substring(finish, allText.length);
        } else if (replacement_type === "swh") {
            txtarea.value = allText.substring(0, start) + `\`:${sel}\`` + allText.substring(finish, allText.length);
        } else if (replacement_type === "spoiler") {
            txtarea.value = allText.substring(0, start) + `--\`spoiler\`--\n${sel}\n--\`spoiler\`--` + allText.substring(finish, allText.length);
        } else if (replacement_type === "link") {
            let link_text = prompt("hangi adrese gidecek?", "http://");
            if (link_text !== "http://") {
                txtarea.value = allText.substring(0, start) + `[${link_text} ${sel}]` + allText.substring(finish, allText.length);
            }
        }
        return true;
    }
};


$("button#insert_bkz").on('click', function () {
    if (!replace_text("user_content_edit", "bkz")) {
        let bkz_text = prompt("bkz verilecek başlık");
        if (bkz_text) {
            $("textarea#user_content_edit").insertAtCaret(`(bkz: ${bkz_text})`);
        }
    }
});


$("button#insert_hede").on('click', function () {
    if (!replace_text("user_content_edit", "hede")) {
        let hede_text = prompt("hangi başlık için link oluşturulacak?");
        if (hede_text) {
            $("textarea#user_content_edit").insertAtCaret(`\`${hede_text}\``);
        }
    }
});

$("button#insert_swh").on('click', function () {
    if (!replace_text("user_content_edit", "swh")) {
        let swh_text = prompt("yıldız içinde ne görünecek?");
        if (swh_text) {
            $("textarea#user_content_edit").insertAtCaret(`\`:${swh_text}\``);
        }
    }
});

$("button#insert_spoiler").on('click', function () {
    if (!replace_text("user_content_edit", "spoiler")) {
        let spoiler_text = prompt("spoiler arasına ne yazılacak?");
        if (spoiler_text) {
            $("textarea#user_content_edit").insertAtCaret(`--\`spoiler\`--\n${spoiler_text}\n--\`spoiler\`--`);
        }

    }
});

$("button#insert_link").on('click', function () {
    if (!replace_text("user_content_edit", "link")) {
        let link_text = prompt("hangi adrese gidecek?", "http://");
        if (link_text !== "http://") {
            let link_name = prompt(" verilecek linkin adı ne olacak?");
            if (link_name) {
                $("textarea#user_content_edit").insertAtCaret(`[${link_text} ${link_name}]`);
            }
        }
    }
});


$(".favorite-entry-btn").on("click", function () {
    let self = this;
    let entry_id = $(self).closest("#rate").attr("data-entry-id");


    $.ajax({
        url: '/entry/favorite/',
        type: 'POST',
        data: {
            "entry_id": entry_id,
        },
        success: function (data) {
            $(self).next().html(data['count']);
            console.log(data);
            if (data['count'] === 0 || data['count'] === 1 && data['status'] === 1) {
                $(self).next().toggleClass('dj-hidden');
            }
            $(self).toggleClass("fav-inverted");
        }
    });
});


$(document).on('click', 'div.entry_info div.rate .dropdown-menu', e => {
    e.stopPropagation();
});


$(".dropdown-fav-count").on('click', ({currentTarget}) => {
    let self = currentTarget;
    let favorites_list = $(self).next();
    $.ajax({
        url: '/entry/favorite/',
        type: 'GET',
        data: {
            "entry_id": $(self).closest("#rate").attr("data-entry-id"),
        },
        success: data => {
            favorites_list.html("");
            if (data['users'][0].length > 0) {
                for (let author of data['users'][0]) {
                    favorites_list.append(`<a class="author-name" href="/biri/${author}/">@${author}</a>`);
                }
            }

            if (data['users'][1].length > 0) {
                favorites_list.append(`<a id="show_novice_button" href="#">...${data['users'][1].length} çaylak</a><span class="dj-hidden" id="favorites_list_novices"></span>`);
                $("a#show_novice_button").on('click', () => {
                    $("#favorites_list_novices").toggleClass("dj-hidden");
                });
                for (let novice of data['users'][1]) {
                    $("#favorites_list_novices").append(`<a class="author-name novice" href="/biri/${novice}/">@${novice}</a>`);
                }
            }

        }
    });

});


$("a#message_history_show").on('click', ({currentTarget}) => {
    $("ul#message_list li.bubble").css('display', 'list-item');
    $(currentTarget).toggle();
});


function entry_rate(entry_id, vote, anon_action = -1,) {
    $.ajax({
        url: '/entry/vote/',
        type: 'POST',
        data: {
            "entry_id": entry_id,
            "vote": vote,
            "anon_action": anon_action,
        },

        success: data => {
            console.log(data);
        },

        error: err => {
            console.log(err);
        },


    });
}


$("#rate a#upvote").on("click", ({currentTarget}) => {
    let entry_id = $(currentTarget).closest("#rate").attr("data-entry-id");
    entry_rate(entry_id, "up");
    $(currentTarget).siblings("a#downvote").removeClass("active");
    $(currentTarget).toggleClass("active");

});

$("#rate a#downvote").on("click", ({currentTarget}) => {
    let entry_id = $(currentTarget).closest("#rate").attr("data-entry-id");
    entry_rate(entry_id, "down");
    $(currentTarget).siblings("a#upvote").removeClass("active");
    $(currentTarget).toggleClass("active");
});


const user_action = (type, recipient_username) => {
    // todo -> yükleniyor tarzı bişiy modalda engelleme.
    $.ajax({
        url: '/user/action/',
        type: 'POST',
        data: {
            "type": type,
            "recipient_username": recipient_username,
        },
        success: (data) => {
            if (data["redirect"]) {
                window.location.replace(data["redirect"]);
            }
        },
        error: (err) => {
            Notify("olmadı");
        }

    });

};


const block_user = (username) => {
    user_action("block", username);
};

$(".block-user-trigger").on("click", ({currentTarget}) => {
    let username = $(currentTarget).attr("data-username")
    $("#block_user").attr("data-username", username);
    $("#username-holder").text(username);
    $("#blockUserModal").modal('show');
});

$("#block_user").on("click", ({currentTarget}) => {
    let target_user = $(currentTarget).attr("data-username");
    block_user(target_user);
});

$(".unblock-user-trigger").on("click", ({currentTarget}) => {
    if (confirm("engel kalksın mı?")) {
        block_user($(currentTarget).attr("data-username"));
        $(currentTarget).hide();
    }
});

$("#follow_user").on("click", ({currentTarget}) => {
    let target_user = $(currentTarget).parent().attr("data-username");
    user_action("follow", target_user);
    $(currentTarget).children("a").toggleText('takip et', 'takip etme');
});


const entry_action = (type, entry_id, sucess_message = "silindi", redirect = false) => {
    $.ajax({
        url: '/entry/action/',
        type: 'POST',
        data: {
            "type": type,
            "entry_id": entry_id,
            "redirect": redirect,

        },
        success: (data) => {
            console.log(data);
            if (sucess_message) {
                Notify(sucess_message);
            }

            if (redirect) {
                window.location.replace(data['redirect_to']);
            }
        },
        error: (err) => {
            console.log(err);
        }
    });
};


$(".delete-entry").on("click", ({currentTarget}) => {
    if (confirm("harbiden silinsin mi?")) {
        entry_action("delete", $(currentTarget).attr("data-target-entry"));
        $(currentTarget).closest(".entry-full").css("display", "none");
    }

});


$(".delete-entry-redirect").on("click", ({currentTarget}) => {
    if (confirm("harbiden silinsin mi?")) {
        entry_action("delete", $(currentTarget).attr("data-target-entry"), false, true);
    }
});


$(".pin-entry").on("click", ({currentTarget}) => {
    entry_action("pin", $(currentTarget).attr("data-target-entry"), "hallettik.");
});

const topic_action = (type, topic_id) => {
    $.ajax({
        url: '/t/action/',
        type: 'POST',
        data: {
            "type": type,
            "topic_id": topic_id,
        },
        success: (data) => {
            console.log(data);

        },
        error: (err) => {
            console.log(err);
        }
    });
};

$(".follow-topic-trigger").on("click", ({currentTarget}) => {
    $(currentTarget).toggleText('takip etme', 'takip et');
    topic_action("follow", $(currentTarget).attr("data-topic-id"));


});

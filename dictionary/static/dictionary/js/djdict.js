$.ajaxSetup({
  beforeSend (xhr, settings) {
    const getCookie = function (name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        let cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
          let cookie = jQuery.trim(cookies[i]);
          // Does this cookie string begin with the name we want?
          if (cookie.substring(0, name.length + 1) === (name + "=")) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    };

    if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
      // Only send the token to relative URLs i.e. locally.
      xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
    }
  }
});

const sleep = function (ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
};

const notify = async (message, type = "default") => {
  let notifictionHolder = $("#notifications");
  notifictionHolder.append(`<li class="${type} dj-hidden">${message}</li>`);
  let nfList = $("#notifications li");
  let numberOfMessages = nfList.length;

  for (const ele of nfList) {
    $(ele).slideDown();
  }

  for (const ele of nfList) {
    await sleep(2750 - numberOfMessages * 300);
    $(ele).slideUp(400);
    await sleep(400);
    $(ele).remove();
  }
};

const leftFrameReset = function () {
  $("a#show_more").addClass("dj-hidden");
  $("#lf_pagination_wrapper").addClass("dj-hidden");
  localStorage.removeItem("navigation_page");
};

const topicListCall = function (slug, parameters, page = null) {
  const loadIndicator = $("#load_indicator");
  loadIndicator.css("display", "inline-block");
  let topicList = $("ul#topic-list");
  // by default, each item in the topic list gets paramaters from api parameters. for example ?day=today calls for
  // topics of today and also includes ?day=today parameter for links of topics. if you do not want this behaviour
  // set this to false for desired slugs.
  const excludeParamteresInLink = ["hayvan-ara"]; // slug list
  let excludeParameters = false;
  if (excludeParamteresInLink.includes(slug)) {
    excludeParameters = true;
  }

  let apiUrl = `/category/${slug}/`;

  if (!page) {
    page = 1;
  }

  let pageParameter = "?page=" + page;

  if (parameters) {
    pageParameter = "&page=" + page;
  }

  $.ajax({
    type: "GET",
    url: apiUrl + parameters + pageParameter,
    success (data) {
      $("#current_category_name").html(localStorage.getItem("active_category_safe")); // change title
      loadIndicator.css("display", "none"); // hide spinner

      if (data["topic_data"].length === 0) {
        topicList.html("<small>yok ki</small>");
      } else {
        if (data["refresh_count"]) {
          $("#refresh_bugun").removeClass("dj-hidden");
          $("span#new_content_count").text(`(${data["refresh_count"]})`);
        } else {
          $("#refresh_bugun").addClass("dj-hidden");
        }

        // decides whether it is an entry permalink or topic and whatsoever
        const slugIdentifier = data["slug_identifier"];
        const totalPages = data["total_pages"];

        if (page > totalPages) {
          notify("yok hiç bişi kalmamış");
          topicListCall(slug, parameters, 1);
        }

        topicList.empty();
        localStorage.setItem("navigation_page", page);

        if (page > 1 && totalPages >= page) {
          let pageRange = [];
          for (let i = 1; i <= totalPages; i++) {
            pageRange.push(i);
          }

          const leftFrameSelect = $("select#left_frame_paginator");
          leftFrameSelect.empty();
          for (const element of pageRange) {
            leftFrameSelect.append($("<option>", {
              value: element,
              text: element
            }
            ));
          }

          leftFrameSelect.val(page);
          $("#lf_total_pages").html(totalPages);
          $("#lf_pagination_wrapper").removeClass("dj-hidden");
        } else {
          leftFrameReset();
          if (page < totalPages) {
            $("a#show_more").removeClass("dj-hidden");
          }
        }

        if (excludeParameters) {
          parameters = "";
        }

        if (slug === "bugun") {
          parameters = "?day=today"; // remove extra parameters (excludeParameters removes all of them)
        }

        data = data["topic_data"];
        for (let i = 0; i < data.length; i++) {
          let topicItem = `<li class="list-group-item"><a href="${slugIdentifier}${data[i]["slug"]}${parameters}">${data[i]["title"]}<small class="total_entries">${data[i]["count"] ? data[i].count : ""}</small></a></li>`;
          topicList.append(topicItem);
        }
      }
    },
    error () {
      notify("bir şeyler yanlış gitti", "error");
      topicList.html("<small>yok yapamıyorum olmuyor :(</small>");
      loadIndicator.css("display", "none");
    }
  });
};

const dictToParameters = function (dict) {
  const str = [];
  for (let key in dict) {
    if (dict.hasOwnProperty(key) && dict[key]) {
      str.push(encodeURIComponent(key) + "=" + encodeURIComponent(dict[key]));
    }
  }
  return str.join("&");
};

const leftFramePopulate = function (slug = null, page = null, resetCache = false, searchParameters = null) {
  // category -> cateogry slug to call topics
  // extended -> retrieve full data (required for paginated data)
  // page -> which page to call, use with extended true
  // reset_cache -> whether to use cached data while calling

  // leftframe behaviour on link clicks on desktop.
  let yearSelect = $("#year_select");
  yearSelect.css("display", "none");
  yearSelect.html("");

  if (!slug) {
    notify("noluyo ayol.", "error");
    return;
  }

  let parameters = "";

  // add parameters for specific slugs

  if (slug === "bugun") {
    parameters = "?day=today";
  }

  if (slug === "caylaklar") {
    parameters = "?a=caylaklar";
  }

  if (slug === "hayvan-ara") {
    if (localStorage.getItem("search_parameters")) {
      parameters = localStorage.getItem("search_parameters");
    } else {
      parameters = searchParameters;
    }
  }

  if (slug === "tarihte-bugun") {
    yearSelect.css("display", "block");
    let years = ["2019", "2018", "2017"];
    for (let year of years) {
      yearSelect.append(`<option id="${year}">${year}</option>`);
    }

    let selectedYear = null;

    if (localStorage.getItem("selected_year")) {
      selectedYear = localStorage.getItem("selected_year");
    } else {
      selectedYear = years[Math.floor(Math.random() * years.length)];
      localStorage.setItem("selected_year", selectedYear);
    }

    yearSelect.val(selectedYear);
    parameters = `?year=${selectedYear}`;
  }
  if (parameters && resetCache) {
    parameters += "&nocache=yes";
  }

  topicListCall(slug, parameters, page);
};

$("ul#category_view li.nav-item, div#category_view_in a.nav-item:not(.regular), a#category_view_ls").on("click", function () {
  localStorage.setItem("active_category_safe", $(this).attr("data-safename"));
  $("ul#category_view li").removeClass("active");
  $("div#category_view_in a").removeClass("active");
  $(this).addClass("active");
  localStorage.setItem("active_category", $(this).attr("data-category"));
  leftFrameReset();
  leftFramePopulate($(this).attr("data-category"));
});

$(function () {
  let mql = window.matchMedia("(max-width: 810px)");

  const desktopView = function () {
    $("ul#category_view li a, div#category_view_in a:not(.regular), a#category_view_ls").on("click", function (e) {
      e.preventDefault();
    });
  };

  const mobileView = function () {
    // add mobile listeners here.
  };

  if (mql.matches) {
    mobileView();
  } else {
    desktopView();
  }

  const screenTest = function (e) {
    if (e.matches) {
    /* mobile switch */
      mobileView();
    } else {
      desktopView();
    }
  };

  $("input.with-datepicker").datepicker(
    {
      container: "#dropdown_detailed_search",
      todayHighlight: true,
      language: "tr",
      autoclose: true,
      orientation: "auto bottom"
    }
  ).attr("placeholder", "gg.aa.yyyy");

  const notificationHolder = $("#notifications");
  let notifications = notificationHolder.attr("data-request-message");
  if (notifications) {
    for (let item of notifications.split("&&")) {
      const nf = item.split("::"); // get type
      notify(nf[0], nf[1]);
    }
  }

  if (!mql.matches) {
    // triggers only in desktop views
    if (localStorage.getItem("active_category")) {
      let category = localStorage.getItem("active_category");
      const navigationPage = localStorage.getItem("navigation_page");
      let selector = $("li[data-category=" + category + "], a[data-category=" + category + "]");
      selector.addClass("active");
      if (!selector.attr("data-category") && category !== "hayvan-ara") {
        // DEFAULT
        // YÜKLENİYOR.
      } else {
        $("#current_category_name").text(selector.attr("data-safename"));
        if (navigationPage) {
          leftFramePopulate(category, parseInt(navigationPage));
        } else {
          leftFramePopulate(category);
        }
      }
    }
  }

  $("#header_search").autocomplete({
    serviceUrl: "/autocomplete/general/",
    preserveInput: true,
    triggerSelectOnValidInput: false,

    onSelect (suggestion) {
      window.location.replace("/topic/?q=" + suggestion.value);
    }
  });

  $(".author-search").autocomplete({
    serviceUrl: "/autocomplete/general/",
    triggerSelectOnValidInput: false,
    paramName: "author",
    onSelect (suggestion) {
      $("input.author-search").val(suggestion.value);
    }
  });

  $("input#author_nick").autocomplete({
    serviceUrl: "/autocomplete/general/",
    triggerSelectOnValidInput: false,
    paramName: "author",
    appendTo: "#raw_inputs"
  });

  $(".send-message-trigger").on("click", function () {
    let recipient = $(this).attr("data-recipient");
    $("input.author-search").val(recipient);
    $("#sendMessageModal").modal("show");
  });

  $("#send_message_btn").on("click", () => {
    $.ajax({
      type: "POST",
      url: "/mesaj/action/gonder/",
      data: {
        message_body: $("textarea#message_body").val(),
        recipient: $("input.author-search").val()
      },
      success: data => {
        notify(data.message);
        if (data.success) {
          $("#sendMessageModal").modal("hide");
        }
      }

    });
  });

  mql.addEventListener("change", screenTest);
});

$("#year_select").on("change", function () {
  let selectedYear = this.value;
  localStorage.setItem("selected_year", selectedYear);
  leftFrameReset();
  leftFramePopulate("tarihte-bugun");
});

$("select#left_frame_paginator").on("change", function () {
  leftFramePopulate(localStorage.getItem("active_category"), this.value);
});

$("#lf_total_pages").on("click", function () {
  $("select#left_frame_paginator").val($(this).html()).trigger("change");
});

$("#lf_navigate_before").on("click", function () {
  const lfSelect = $("select#left_frame_paginator");
  const selected = parseInt(lfSelect.val());
  if (selected - 1 > 0) {
    lfSelect.val(selected - 1).trigger("change");
  }
});

$("#lf_navigate_after").on("click", function () {
  const lfSelect = $("select#left_frame_paginator");
  const selected = parseInt(lfSelect.val());
  const max = parseInt($("#lf_total_pages").html());
  if (selected + 1 <= max) {
    lfSelect.val(selected + 1).trigger("change");
  }
});

$("a#show_more").on("click", function () {
  leftFramePopulate(localStorage.getItem("active_category"), 2);
  $(this).addClass("dj-hidden");
});

// https://stackoverflow.com/questions/5999118/how-can-i-add-or-update-a-query-string-parameter
const updateQueryStringParameter = function (uri, key, value) {
  let re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
  let separator = uri.indexOf("?") !== -1 ? "&" : "?";
  if (uri.match(re)) {
    return uri.replace(re, "$1" + key + "=" + value + "$2");
  } else {
    return uri + separator + key + "=" + value;
  }
};

$("select#entry_list_page").on("change", function () {
  window.location = updateQueryStringParameter(location.href, "page", this.value);
});

jQuery.fn.extend({
  insertAtCaret (myValue) {
    return this.each(function (i) {
      if (document.selection) {
        // Internet Explorer
        this.focus();
        let sel = document.selection.createRange();
        sel.text = myValue;
        this.focus();
      } else if (this.selectionStart || this.selectionStart === "0") {
        // For browsers like Firefox and Webkit based
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
  toggleText (a, b) {
    return this.text(this.text() === b ? a : b);
  }

});

const replaceText = (elementId, replacementType) => {
  let txtarea = document.getElementById(elementId);
  let start = txtarea.selectionStart;
  let finish = txtarea.selectionEnd;
  let allText = txtarea.value;
  let sel = allText.substring(start, finish);
  if (!sel) {
    return false;
  } else {
    if (replacementType === "bkz") {
      txtarea.value = allText.substring(0, start) + `(bkz: ${sel})` + allText.substring(finish, allText.length);
    } else if (replacementType === "hede") {
      txtarea.value = allText.substring(0, start) + `\`${sel}\`` + allText.substring(finish, allText.length);
    } else if (replacementType === "swh") {
      txtarea.value = allText.substring(0, start) + `\`:${sel}\`` + allText.substring(finish, allText.length);
    } else if (replacementType === "spoiler") {
      txtarea.value = allText.substring(0, start) + `--\`spoiler\`--\n${sel}\n--\`spoiler\`--` + allText.substring(finish, allText.length);
    } else if (replacementType === "link") {
      let linkText = prompt("hangi adrese gidecek?", "http://");
      if (linkText !== "http://") {
        txtarea.value = allText.substring(0, start) + `[${linkText} ${sel}]` + allText.substring(finish, allText.length);
      }
    }
    return true;
  }
};

$("button#insert_bkz").on("click", function () {
  if (!replaceText("user_content_edit", "bkz")) {
    let bkzText = prompt("bkz verilecek başlık");
    if (bkzText) {
      $("textarea#user_content_edit").insertAtCaret(`(bkz: ${bkzText})`);
    }
  }
});

$("button#insert_hede").on("click", function () {
  if (!replaceText("user_content_edit", "hede")) {
    let hedeText = prompt("hangi başlık için link oluşturulacak?");
    if (hedeText) {
      $("textarea#user_content_edit").insertAtCaret(`\`${hedeText}\``);
    }
  }
});

$("button#insert_swh").on("click", function () {
  if (!replaceText("user_content_edit", "swh")) {
    let swhText = prompt("yıldız içinde ne görünecek?");
    if (swhText) {
      $("textarea#user_content_edit").insertAtCaret(`\`:${swhText}\``);
    }
  }
});

$("button#insert_spoiler").on("click", function () {
  if (!replaceText("user_content_edit", "spoiler")) {
    let spoilerText = prompt("spoiler arasına ne yazılacak?");
    if (spoilerText) {
      $("textarea#user_content_edit").insertAtCaret(`--\`spoiler\`--\n${spoilerText}\n--\`spoiler\`--`);
    }
  }
});

$("button#insert_link").on("click", function () {
  if (!replaceText("user_content_edit", "link")) {
    let linkText = prompt("hangi adrese gidecek?", "http://");
    if (linkText !== "http://") {
      let linkName = prompt(" verilecek linkin adı ne olacak?");
      if (linkName) {
        $("textarea#user_content_edit").insertAtCaret(`[${linkText} ${linkName}]`);
      }
    }
  }
});

$(".favorite-entry-btn").on("click", function () {
  let self = this;
  let entryId = $(self).closest("#rate").attr("data-entry-id");
  $.ajax({
    url: "/entry/action/",
    type: "POST",
    data: {
      "type": "favorite",
      "entry_id": entryId
    },
    success (data) {
      $(self).next().html(data["count"]);
      if (data["count"] === 0 || (data["count"] === 1 && data["status"] === 1)) {
        $(self).next().toggleClass("dj-hidden");
      }
      $(self).toggleClass("fav-inverted");
    }
  });
});

$(document).on("click", "div.entry_info div.rate .dropdown-menu, #dropdown_detailed_search :not(#close_search_dropdown)", e => {
  e.stopPropagation();
});

$(".dropdown-fav-count").on("click", function () {
  let self = this;
  let favoritesList = $(self).next();
  $.ajax({
    url: "/entry/action/",
    type: "GET",
    data: {
      "type": "favorite_list",
      "entry_id": $(self).closest("#rate").attr("data-entry-id")
    },
    success: data => {
      favoritesList.html("");
      if (data["users"][0].length > 0) {
        for (let author of data["users"][0]) {
          favoritesList.append(`<a class="author-name" href="/biri/${author}/">@${author}</a>`);
        }
      }

      if (data["users"][1].length > 0) {
        favoritesList.append(`<a id="show_novice_button" href="#">...${data["users"][1].length} çaylak</a><span class="dj-hidden" id="favorites_list_novices"></span>`);
        $("a#show_novice_button").on("click", () => {
          $("#favorites_list_novices").toggleClass("dj-hidden");
        });
        for (let novice of data["users"][1]) {
          $("#favorites_list_novices").append(`<a class="author-name novice" href="/biri/${novice}/">@${novice}</a>`);
        }
      }
    }
  });
});

$("a#message_history_show").on("click", function () {
  $("ul#message_list li.bubble").css("display", "list-item");
  $(this).toggle();
});

const entryRate = function (entryId, vote, anonAction = -1) {
  $.ajax({
    url: "/entry/vote/",
    type: "POST",
    data: {
      "entry_id": entryId,
      vote,
      "anon_action": anonAction
    }
  });
};

$("#rate a#upvote").on("click", function () {
  let entryId = $(this).closest("#rate").attr("data-entry-id");
  entryRate(entryId, "up");
  $(this).siblings("a#downvote").removeClass("active");
  $(this).toggleClass("active");
});

$("#rate a#downvote").on("click", function () {
  let entryId = $(this).closest("#rate").attr("data-entry-id");
  entryRate(entryId, "down");
  $(this).siblings("a#upvote").removeClass("active");
  $(this).toggleClass("active");
});

const userAction = (type, recipientUsername) => {
  $.ajax({
    url: "/user/action/",
    type: "POST",
    data: {
      type,
      "recipient_username": recipientUsername
    },
    success: data => {
      if (data["redirect_to"]) {
        window.location.replace(data["redirect_to"]);
      }
    },
    error: data => {
      notify(data["message"]);
    }

  });
};

const blockUser = username => {
  userAction("block", username);
};

$(".block-user-trigger").on("click", function () {
  let username = $(this).attr("data-username");
  $("#block_user").attr("data-username", username);
  $("#username-holder").text(username);
  $("#blockUserModal").modal("show");
});

$("#block_user").on("click", function () {
  let targetUser = $(this).attr("data-username");
  blockUser(targetUser);
  $("#blockUserModal").modal("hide");
});

$(".unblock-user-trigger").on("click", function () {
  if (confirm("engel kalksın mı?")) {
    blockUser($(this).attr("data-username"));
    $(this).hide();
  }
});

$("#follow_user").on("click", function () {
  let targetUser = $(this).parent().attr("data-username");
  userAction("follow", targetUser);
  $(this).children("a").toggleText("takip et", "takip etme");
});

const entryAction = (type, entryId, redirect = false) => {
  $.ajax({
    url: "/entry/action/",
    type: "POST",
    data: {
      type,
      "entry_id": entryId,
      redirect

    },
    success: data => {
      if (data["message"]) {
        notify(data["message"]);
      }

      if (redirect) {
        window.location.replace(data["redirect_to"]);
      }
    },
    error: () => {
      notify("olmuyor", "error");
    }
  });
};

$(".delete-entry").on("click", function () {
  if (confirm("harbiden silinsin mi?")) {
    entryAction("delete", $(this).attr("data-target-entry"));
    $(this).closest(".entry-full").css("display", "none");
  }
});

$(".delete-entry-redirect").on("click", function () {
  if (confirm("harbiden silinsin mi?")) {
    entryAction("delete", $(this).attr("data-target-entry"), true);
  }
});

$(".pin-entry").on("click", function () {
  entryAction("pin", $(this).attr("data-target-entry"));
});

const topicAction = (type, topicId) => {
  $.ajax({
    url: "/t/action/",
    type: "POST",
    data: {
      type,
      "topic_id": topicId
    },
    error: () => {
      notify("olmuyor", "error");
    }
  });
};

$(".follow-topic-trigger").on("click", function () {
  $(this).toggleText("takip etme", "takip et");
  topicAction("follow", $(this).attr("data-topic-id"));
});

$("select#mobile_year_changer").on("change", function () {
  window.location = updateQueryStringParameter(location.href, "year", this.value);
});

$("#refresh_bugun").on("click", function () {
  let page = null;
  if (localStorage.getItem("navigation_page")) {
    page = localStorage.getItem("navigation_page");
  }
  leftFrameReset();
  leftFramePopulate("bugun", page, true);
  $(this).addClass("dj-hidden");
});

$.fn.overflown = function () {
  const e = this[0];
  return e.scrollHeight > e.clientHeight || e.scrollWidth > e.clientWidth;
};

const truncateEntryText = () => {
  for (const element of $("article.entry p ")) {
    if ($(element).overflown()) {
      $(element).parent().append(`<div class="read_more">devamını okuyayım</div>`);
    }
  }
};

if ($("body").hasClass("has-entries")) {
  truncateEntryText();
  $("div.read_more").on("click", function () {
    $(this).siblings("p").css("max-height", "none");
    $(this).hide();
  });
}

$("button#perform_advanced_search").on("click", function () {
  const keywords = $("input#keywords").val();
  const authorNick = $("input#author_nick").val();
  const isNiceOnes = $("input#nice_ones").is(":checked");
  const isFavorites = $("input#in_favorites").is(":checked");
  const fromDate = $("input#date_from").val();
  const toDate = $("input#date_to").val();
  const ordering = $("select#ordering").val();

  const keys = {
    keywords,
    "author_nick": authorNick,
    "is_nice_ones": isNiceOnes,
    "is_in_favorites": isFavorites,
    "from_date": fromDate,
    "to_date": toDate,
    ordering
  };
  const searchParameters = "?" + dictToParameters(keys);
  localStorage.setItem("active_category_safe", "arama sonuçları");
  localStorage.setItem("active_category", "hayvan-ara");
  localStorage.setItem("search_parameters", searchParameters);
  leftFrameReset();
  leftFramePopulate("hayvan-ara", null, false, searchParameters);
});

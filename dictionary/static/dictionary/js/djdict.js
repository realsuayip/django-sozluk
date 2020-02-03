/* global Cookies */

// b64 functions source: https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
const b64EncodeUnicode = function (str) {
  // first we use encodeURIComponent to get percent-encoded UTF-8,
  // then we convert the percent encodings into raw bytes which
  // can be fed into btoa.
  return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g,
    function toSolidBytes (match, p1) {
      return String.fromCharCode("0x" + p1);
    }));
};

const b64DecodeUnicode = function (str) {
  // Going backwards: from bytestream, to percent-encoding, to original string.
  return decodeURIComponent(atob(str).split("").map(function (c) {
    return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
  }).join(""));
};

const cookies = Cookies.withConverter(
  // Use ONLY with custom cookies
  {
    write (value) {
      return b64EncodeUnicode(value);
    },
    read (value) {
      return b64DecodeUnicode(value);
    }
  }
).withAttributes({sameSite: "Lax"});

$.ajaxSetup({
  beforeSend (xhr, settings) {
    if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
      // Only send the token to relative URLs i.e. locally.
      xhr.setRequestHeader("X-CSRFToken", Cookies.get("csrftoken"));
    }
  }
});

const sleep = function (ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
};

const notify = async (message, type = "default") => {
  const notifictionHolder = $("#notifications");
  notifictionHolder.append(`<li class="${type} dj-hidden">${message}</li>`);
  const nfList = $("#notifications li");
  const numberOfMessages = nfList.length;

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
  $("#left-frame-nav").scrollTop(0);
  $("a#show_more").addClass("dj-hidden");
  $("#lf_pagination_wrapper").addClass("dj-hidden");
  cookies.remove("navigation_page");
};

const topicListCall = function (slug, parameters, page = null) {
  const loadIndicator = $("#load_indicator");
  loadIndicator.css("display", "inline-block");
  const topicList = $("ul#topic-list");
  // by default, each item in the topic list gets paramaters from api parameters. for example ?day=today calls for
  // topics of today and also includes ?day=today parameter for links of topics. if you do not want this behaviour
  // set this to false for desired slugs.
  const excludeParamteresInLink = ["hayvan-ara"]; // slug list
  let excludeParameters = false;
  if (excludeParamteresInLink.includes(slug)) {
    excludeParameters = true;
  }

  const apiUrl = `/category/${slug}/`;

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
      $("#current_category_name").text(cookies.get("active_category_safe")); // change title
      loadIndicator.css("display", "none"); // hide spinner

      if (data.refresh_count) {
        $("#refresh_bugun").removeClass("dj-hidden");
        $("span#new_content_count").text(`(${data.refresh_count})`);
      } else {
        $("#refresh_bugun").addClass("dj-hidden");
      }

      if (data.topic_data.length === 0) {
        topicList.html("<small>yok ki</small>");
      } else {
        // decides whether it is an entry permalink or topic and whatsoever
        const slugIdentifier = data.slug_identifier;
        const totalPages = data.total_pages;

        if (page > totalPages) {
          notify("yok hiç bişi kalmamış");
          topicListCall(slug, parameters, 1);
        }

        topicList.empty();
        cookies.set("navigation_page", page);

        if (page > 1 && totalPages >= page) {
          const pageRange = [];
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

        data = data.topic_data;
        for (let i = 0; i < data.length; i++) {
          const topicItem = `<li class="list-group-item"><a href="${slugIdentifier}${data[i].slug}/${parameters}">${data[i].title}<small class="total_entries">${data[i].count ? data[i].count : ""}</small></a></li>`;
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
  for (const key in dict) {
    // a. check if the property/key is defined in the object itself, not in parent
    // b. check if the key is not empty
    if (Object.prototype.hasOwnProperty.call(dict, key) && dict[key]) {
      str.push(encodeURIComponent(key) + "=" + encodeURIComponent(dict[key]));
    }
  }
  return str.join("&");
};

const leftFramePopulate = function (slug = null, page = null, resetCache = false, searchParameters = null) {
  // category -> cateogry slug (or non_db_categories slug)
  // page -> which page to call
  // reset_cache -> whether to use cached data while calling

  // leftframe behaviour on link clicks on desktop.
  const yearSelect = $("#year_select");
  yearSelect.css("display", "none");
  yearSelect.html("");

  if (!slug) {
    notify("noluyo ayol.", "error");
    return;
  }

  let parameters = "";
  const entryCategories = ["takip", "kenar", "debe"]; // these slugs will have no query strings

  // add query string parameters for specific slugs
  if ((slug === "bugun") || (slug === "basiboslar")) {
    parameters = "?day=today";
  } else if (slug === "caylaklar") {
    parameters = "?a=caylaklar";
  } else if (slug === "hayvan-ara") {
    if (cookies.get("search_parameters")) {
      parameters = cookies.get("search_parameters");
    } else {
      parameters = searchParameters;
    }
  } else if (slug === "tarihte-bugun") {
    yearSelect.css("display", "block");
    const years = ["2020", "2019", "2018"];
    for (const year of years) {
      yearSelect.append(`<option id="${year}">${year}</option>`);
    }

    let selectedYear;

    if (cookies.get("selected_year")) {
      selectedYear = cookies.get("selected_year");
    } else {
      selectedYear = years[Math.floor(Math.random() * years.length)];
      cookies.set("selected_year", selectedYear);
    }

    yearSelect.val(selectedYear);
    parameters = `?year=${selectedYear}`;
  } else {
    // generic category
    if (!(entryCategories.includes(slug))) {
      parameters = "?day=today";
    }
  }

  if (parameters && resetCache) {
    parameters += "&nocache=yes";
  }

  topicListCall(slug, parameters, page);
};

$("ul#category_view li.nav-item, div#category_view_in a.nav-item:not(.regular), a#category_view_ls").on("click", function () {
  cookies.set("active_category_safe", $(this).attr("data-safename"));
  $("ul#category_view li").removeClass("active");
  $("div#category_view_in a").removeClass("active");
  $(this).addClass("active");
  cookies.set("active_category", $(this).attr("data-category"));
  leftFrameReset();
  leftFramePopulate($(this).attr("data-category"));
});

let userIsMobile = false;

$(function () {
  const mql = window.matchMedia("(max-width: 810px)");
  const desktopView = function () {
    $("ul#category_view li a, div#category_view_in a:not(.regular), a#category_view_ls").on("click", function (e) {
      e.preventDefault();
    });
  };

  const mobileView = function () {
    userIsMobile = true;
    // add mobile listeners here.
  };

  if (mql.matches) {
    mobileView();
  } else {
    desktopView();
  }

  $("input.with-datepicker-dropdown").datepicker(
    {
      container: "#dropdown_detailed_search",
      todayHighlight: true,
      language: "tr",
      autoclose: true,
      orientation: "auto bottom"
    }
  ).attr("placeholder", "gg.aa.yyyy");

  $("input.with-datepicker-mobile").datepicker(
    {
      container: ".row",
      todayHighlight: true,
      language: "tr",
      autoclose: true,
      orientation: "auto left"
    }
  ).attr("placeholder", "gg.aa.yyyy");

  const notificationHolder = $("#notifications");
  const notifications = notificationHolder.attr("data-request-message");
  if (notifications) {
    for (const item of notifications.split("&&")) {
      const nf = item.split("::"); // get type
      notify(nf[0], nf[1]);
    }
  }

  if (!userIsMobile && parseInt(localStorage.getItem("where")) > 0) {
    $("#left-frame-nav").scrollTop(localStorage.getItem("where"));
  }

  $("#header_search").autocomplete({
    serviceUrl: "/autocomplete/general/",
    triggerSelectOnValidInput: false,
    showNoSuggestionNotice: true,
    noSuggestionNotice: "-- buna yakın bir sonuç yok --",

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

  $(".send-message-trigger").on("click", function () {
    const recipient = $(this).attr("data-recipient");
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
});

$("#year_select").on("change", function () {
  const selectedYear = this.value;
  cookies.set("selected_year", selectedYear);
  leftFrameReset();
  leftFramePopulate("tarihte-bugun");
});

$("select#left_frame_paginator").on("change", function () {
  leftFramePopulate(cookies.get("active_category"), this.value);
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
  leftFramePopulate(cookies.get("active_category"), 2);
  $(this).addClass("dj-hidden");
});

// https://stackoverflow.com/questions/5999118/how-can-i-add-or-update-a-query-string-parameter
const updateQueryStringParameter = function (uri, key, value) {
  const re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
  const separator = uri.indexOf("?") !== -1 ? "&" : "?";
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
    return this.each(function () {
      if (document.selection) {
        // Internet Explorer
        this.focus();
        const sel = document.selection.createRange();
        sel.text = myValue;
        this.focus();
      } else if (this.selectionStart || this.selectionStart === "0") {
        // For browsers like Firefox and Webkit based
        const startPos = this.selectionStart;
        const endPos = this.selectionEnd;
        const scrollTop = this.scrollTop;
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
  const txtarea = document.getElementById(elementId);
  const start = txtarea.selectionStart;
  const finish = txtarea.selectionEnd;
  const allText = txtarea.value;
  const sel = allText.substring(start, finish);
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
      const linkText = prompt("hangi adrese gidecek?", "http://");
      if (linkText !== "http://") {
        txtarea.value = allText.substring(0, start) + `[${linkText} ${sel}]` + allText.substring(finish, allText.length);
      }
    }
    return true;
  }
};

$("button#insert_bkz").on("click", function () {
  if (!replaceText("user_content_edit", "bkz")) {
    const bkzText = prompt("bkz verilecek başlık, #entry veya @yazar");
    if (bkzText) {
      $("textarea#user_content_edit").insertAtCaret(`(bkz: ${bkzText})`);
    }
  }
});

$("button#insert_hede").on("click", function () {
  if (!replaceText("user_content_edit", "hede")) {
    const hedeText = prompt("hangi başlık veya #entry için link oluşturulacak?");
    if (hedeText) {
      $("textarea#user_content_edit").insertAtCaret(`\`${hedeText}\``);
    }
  }
});

$("button#insert_swh").on("click", function () {
  if (!replaceText("user_content_edit", "swh")) {
    const swhText = prompt("yıldız içinde ne görünecek?");
    if (swhText) {
      $("textarea#user_content_edit").insertAtCaret(`\`:${swhText}\``);
    }
  }
});

$("button#insert_spoiler").on("click", function () {
  if (!replaceText("user_content_edit", "spoiler")) {
    const spoilerText = prompt("spoiler arasına ne yazılacak?");
    if (spoilerText) {
      $("textarea#user_content_edit").insertAtCaret(`--\`spoiler\`--\n${spoilerText}\n--\`spoiler\`--`);
    }
  }
});

$("button#insert_link").on("click", function () {
  if (!replaceText("user_content_edit", "link")) {
    const linkText = prompt("hangi adrese gidecek?", "http://");
    if (linkText && linkText !== "http://") {
      const linkName = prompt(" verilecek linkin adı ne olacak?");
      if (linkName) {
        $("textarea#user_content_edit").insertAtCaret(`[${linkText} ${linkName}]`);
      }
    }
  }
});

$(".favorite-entry-btn").on("click", function () {
  const self = this;
  const entryId = $(self).closest("#rate").attr("data-entry-id");
  $.ajax({
    url: "/entry/action/",
    type: "POST",
    data: {
      type: "favorite",
      entry_id: entryId
    },
    success (data) {
      $(self).next().html(data.count);
      if (data.count === 0 || (data.count === 1 && data.status === 1)) {
        $(self).next().toggleClass("dj-hidden");
      }
      $(self).toggleClass("fav-inverted");
    }
  });
});

$(document).on("click", "div.entry_info div.rate .dropdown-menu, #dropdown_detailed_search :not(#close_search_dropdown), .autocomplete-suggestions", e => {
  e.stopPropagation();
});

$(".dropdown-fav-count").on("click", function () {
  const self = this;
  const favoritesList = $(self).next();
  $.ajax({
    url: "/entry/action/",
    type: "GET",
    data: {
      type: "favorite_list",
      entry_id: $(self).closest("#rate").attr("data-entry-id")
    },
    success: data => {
      favoritesList.html("");
      if (data.users[0].length > 0) {
        for (const author of data.users[0]) {
          favoritesList.append(`<a class="author-name" href="/biri/${author}/">@${author}</a>`);
        }
      }

      if (data.users[1].length > 0) {
        favoritesList.append(`<a id="show_novice_button" role="button" tabindex="0">...${data.users[1].length} çaylak</a><span class="dj-hidden" id="favorites_list_novices"></span>`);
        $("a#show_novice_button").on("click", () => {
          $("#favorites_list_novices").toggleClass("dj-hidden");
        });
        for (const novice of data.users[1]) {
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
      entry_id: entryId,
      vote,
      anon_action: anonAction
    }
  });
};

$("#rate a#upvote").on("click", function () {
  const entryId = $(this).closest("#rate").attr("data-entry-id");
  entryRate(entryId, "up");
  $(this).siblings("a#downvote").removeClass("active");
  $(this).toggleClass("active");
});

$("#rate a#downvote").on("click", function () {
  const entryId = $(this).closest("#rate").attr("data-entry-id");
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
      recipient_username: recipientUsername
    },
    success: data => {
      if (data.redirect_to) {
        window.location.replace(data.redirect_to);
      }
    },
    error: data => {
      if (data.message) {
        notify(data.message);
      }
    }

  });
};

const blockUser = username => {
  userAction("block", username);
};

$(".block-user-trigger").on("click", function () {
  const username = $(this).attr("data-username");
  $("#block_user").attr("data-username", username);
  $("#username-holder").text(username);
  $("#blockUserModal").modal("show");
});

$("#block_user").on("click", function () {
  const targetUser = $(this).attr("data-username");
  blockUser(targetUser);
  $("#blockUserModal").modal("hide");
});

$(".unblock-user-trigger").on("click", function () {
  if (confirm("engel kalksın mı?")) {
    blockUser($(this).attr("data-username"));
    $(this).hide();
  }
});

$(".follow-user-trigger").on("click", function () {
  const targetUser = $(this).parent().attr("data-username");
  userAction("follow", targetUser);
  $(this).children("a").toggleText("takip et", "takip etme");
});

const entryAction = (type, entryId, redirect = false) => {
  $.ajax({
    url: "/entry/action/",
    type: "POST",
    data: {
      type,
      entry_id: entryId,
      redirect

    },
    success: data => {
      if (data.message) {
        notify(data.message);
      }

      if (redirect) {
        window.location.replace(data.redirect_to);
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
      topic_id: topicId
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
  if (cookies.get("navigation_page")) {
    page = cookies.get("navigation_page");
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

window.onload = function () {
  if ($("body").hasClass("has-entries")) {
    truncateEntryText();
    $("div.read_more").on("click", function () {
      $(this).siblings("p").css("max-height", "none");
      $(this).hide();
    });
  }
};

const populateSearchResults = searchParameters => {
  if (!searchParameters) {
    return;
  }

  const slug = "hayvan-ara";

  if (userIsMobile) {
    window.location.replace("/basliklar/" + slug + "/" + searchParameters);
  }

  cookies.set("active_category_safe", "arama sonuçları");
  cookies.set("active_category", slug);
  cookies.set("search_parameters", searchParameters);
  leftFrameReset();
  leftFramePopulate(slug, null, false, searchParameters);
};

$("button#perform_advanced_search").on("click", function () {
  const keywords = $("input#keywords_dropdown").val();
  const authorNick = $("input#author_nick_dropdown").val();
  const isNiceOnes = $("input#nice_ones_dropdown").is(":checked");
  const isFavorites = $("input#in_favorites_dropdown").is(":checked");
  const fromDate = $("input#date_from_dropdown").val();
  const toDate = $("input#date_to_dropdown").val();
  const ordering = $("select#ordering_dropdown").val();

  const keys = {
    keywords,
    author_nick: authorNick,
    is_nice_ones: isNiceOnes,
    is_in_favorites: isFavorites,
    from_date: fromDate,
    to_date: toDate,
    ordering
  };
  const searchParameters = "?" + dictToParameters(keys);
  populateSearchResults(searchParameters);
});

const categoryAction = (type, categoryId) => {
  $.ajax({
    url: "/c/action/",
    type: "POST",
    data: {
      type,
      category_id: categoryId
    },
    error: () => {
      notify("olmuyor", "error");
    }
  });
};

$("button#follow-category-trigger").on("click", function () {
  categoryAction("follow", $(this).data("category-id"));
  $(this).toggleText("bırak ya", "takip et");
  $(this).toggleClass("faded");
});

$("form.search_mobile").submit(function () {
  const emptyFields = $(this).find(":input").filter(function () {
    return $(this).val() === "";
  });
  emptyFields.prop("disabled", true);
  return true;
});

$("a[role=button]").keypress(function (event) {
  if (event.which === 13 || event.which === 32) { // space or enter
    $(this).trigger("click");
  }
});

$("a[role=button].quicksearch").on("click", function () {
  const searchParameters = "?keywords=" + $(this).attr("data-keywords") + "&ordering=newer";
  populateSearchResults(searchParameters);
});

$("#left-frame-nav").scroll(function () {
  localStorage.setItem("where", $(this).scrollTop());
});


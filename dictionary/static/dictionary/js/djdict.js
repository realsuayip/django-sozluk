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

// Use ONLY with custom cookies
const cookies = Cookies.withConverter({
    write (value) {
        return b64EncodeUnicode(value);
    },
    read (value) {
        return b64DecodeUnicode(value);
    }
}).withAttributes({ sameSite: "Lax" });

$.ajaxSetup({
    beforeSend (xhr, settings) {
        xhr.setRequestHeader("Content-Type", "application/json");
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

class LeftFrame {
    constructor (slug, page = 1, year = null, searchKeys = null, refresh = false) {
        // slug -> str, year -> int or str, searchKeys -> str (query parameters)
        this.slug = slug;
        this.page = page;
        this.year = year;
        this.refresh = refresh;
        this.searchKeys = searchKeys;

        this.setCookies();
        this.loadIndicator = $("#load_indicator");
    }

    setCookies () {
        cookies.set("active_category", this.slug);
        cookies.set("navigation_page", this.page);

        const cookieYear = cookies.get("selected_year");
        const cookieSearchKeys = cookies.get("search_parameters");

        if (this.slug === "tarihte-bugun") {
            this.year = this.year ? this.year : cookieYear || null;
        } else if (this.slug === "hayvan-ara") {
            this.searchKeys = this.searchKeys ? this.searchKeys : cookieSearchKeys || null;
        }
    }

    call () {
        this.loadIndicator.css("display", "inline-block");

        const slug = `slug: "${this.slug}"`;
        const year = `${this.year ? `year: ${this.year}` : ""}`;
        const page = `${this.page ? `page: ${this.page}` : ""}`;
        const searchKeys = `${this.searchKeys ? `searchKeys: "${this.searchKeys}"` : ""}`;
        const refresh = `${this.refresh ? `refresh: ${this.refresh}` : ""}`;
        const queryParams = [slug, year, page, searchKeys, refresh].filter(val => val).join(", ");

        const query = `{topics(${queryParams}){
            safename refreshCount year yearRange slugIdentifier
            page { 
              objectList { slug title count }
              paginator { pageRange numPages }
              number hasOtherPages
            }
          }}`;

        const self = this;

        $.post("/graphql/", JSON.stringify({ query }), function (response) {
            if (response.errors) {
                self.loadIndicator.css("display", "none");
                notify("bir şeyler yanlış gitti", "error");
            } else {
                self.render(response.data.topics);
            }
        }).fail(function () {
            notify("bir şeyler yanlış gitti", "error");
            self.loadIndicator.css("display", "none");
        });
    }

    render (data) {
        $("#left-frame-nav").scrollTop(0);
        $("#current_category_name").text(data.safename);
        this.renderRefreshButton(data.refreshCount);
        this.renderYearSelector(data.year, data.yearRange);
        this.renderPagination(data.page.hasOtherPages, data.page.paginator.pageRange, data.page.paginator.numPages, data.page.number);
        this.renderTopicList(data.page.objectList, data.slugIdentifier, data.parameters);
        this.renderShowMoreButton(data.page.number, data.page.hasOtherPages);
        this.loadIndicator.css("display", "none");
    }

    renderRefreshButton (count) {
        const refreshButton = $("#refresh_bugun");
        if (count) {
            refreshButton.removeClass("dj-hidden");
            $("span#new_content_count").text(`(${count})`);
        } else {
            refreshButton.addClass("dj-hidden");
        }
    }

    renderShowMoreButton (currentPage, isPaginated) {
        const showMoreButton = $("a#show_more");

        if (currentPage !== 1 || !isPaginated) {
            showMoreButton.addClass("dj-hidden");
        } else {
            showMoreButton.removeClass("dj-hidden");
        }
    }

    renderYearSelector (currentYear, yearRange) {
        const yearSelect = $("#year_select");
        yearSelect.html("");

        if (this.slug === "tarihte-bugun") {
            yearSelect.css("display", "block");
            for (const year of yearRange) {
                yearSelect.append(`<option ${year === currentYear ? "selected" : ""} id="${year}">${year}</option>`);
            }
        } else {
            yearSelect.css("display", "none");
        }
    }

    renderTopicList (objectList, slugIdentifier, parameters) {
        const topicList = $("ul#topic-list");
        if (objectList.length === 0) {
            topicList.html(`<small>yok ki</small>`);
        } else {
            topicList.empty();
            const params = parameters || "";

            for (const topic of objectList) {
                topicList.append(`<li class="list-group-item"><a href="${slugIdentifier}${topic.slug}/${params}">${topic.title}<small class="total_entries">${topic.count ? topic.count : ""}</small></a></li>`);
            }
        }
    }

    renderPagination (isPaginated, pageRange, totalPages, currentPage) {
        // Pagination related selectors
        const paginationWrapper = $("#lf_pagination_wrapper");
        const pageSelector = $("select#left_frame_paginator");
        const totalPagesButton = $("#lf_total_pages");

        // Render pagination
        if (isPaginated && currentPage !== 1) {
            // Render Page selector
            pageSelector.empty();
            for (const page of pageRange) {
                pageSelector.append($("<option>", {
                    value: page,
                    text: page,
                    selected: page === currentPage
                }));
            }
            totalPagesButton.text(totalPages); // Last page
            paginationWrapper.removeClass("dj-hidden"); // Show it
        } else {
            paginationWrapper.addClass("dj-hidden");
        }
    }

    static populate (slug, page = 1, year = null, searchKeys = null, refresh = false) {
        const leftFrame = new LeftFrame(slug, page, year, searchKeys, refresh);
        leftFrame.call();
    }

    static refreshPopulate () {
        LeftFrame.populate("bugun", 1, null, null, true);
    }
}

/* Start of LefFrame related triggers */

$("[data-lf-slug]").on("click", function () {
    // Regular, slug-only
    const slug = $(this).attr("data-lf-slug");
    LeftFrame.populate(slug);
});

$("#year_select").on("change", function () {
    // Year is changed
    const selectedYear = this.value;
    LeftFrame.populate("tarihte-bugun", 1, selectedYear);
});

$("select#left_frame_paginator").on("change", function () {
    // Page is changed
    LeftFrame.populate(cookies.get("active_category"), this.value);
});

$("#lf_total_pages").on("click", function () {
    // Navigated to last page
    $("select#left_frame_paginator").val($(this).html()).trigger("change");
});

$("#lf_navigate_before").on("click", function () {
    // Previous page
    const lfSelect = $("select#left_frame_paginator");
    const selected = parseInt(lfSelect.val());
    if (selected - 1 > 0) {
        lfSelect.val(selected - 1).trigger("change");
    }
});

$("#lf_navigate_after").on("click", function () {
    // Subsequent page
    const lfSelect = $("select#left_frame_paginator");
    const selected = parseInt(lfSelect.val());
    const max = parseInt($("#lf_total_pages").text());
    if (selected + 1 <= max) {
        lfSelect.val(selected + 1).trigger("change");
    }
});

$("a#show_more").on("click", function () {
    // Show more button event
    const slug = cookies.get("active_category");

    if (slug) {
        LeftFrame.populate(slug, 2);
    }

    $(this).addClass("dj-hidden");
});

$("#refresh_bugun").on("click", function () {
    LeftFrame.refreshPopulate();
});

/* End of LefFrame related triggers */

$("ul#category_view li[data-lf-slug], div#category_view_in a[data-lf-slug]:not(.regular)").on("click", function () {
    // Visual guidance for active category
    $("ul#category_view li[data-lf-slug], div#category_view_in a[data-lf-slug]:not(.regular)").removeClass("active");
    $(this).addClass("active");
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

    if (userIsMobile) {
        // Code to hide some part of the header on mobile scroll.
        let lastScrollTop = 0;
        const delta = 30;
        $(window).scroll(function () {
            const st = $(this).scrollTop();
            const header = $("header.page_header");
            if (Math.abs(lastScrollTop - st) <= delta) {
                return;
            }

            if (st > lastScrollTop) {
                // downscroll code
                $(".sub-nav").css("margin-top", ".75em");
                header.css("top", "-55px").hover(function () {
                    $(".sub-nav").css("margin-top", "0");
                    header.css("top", "0px");
                });
            } else {
                // upscroll code
                $(".sub-nav").css("margin-top", "0");
                header.css("top", "0px");
            }
            lastScrollTop = st;
        });
    }

    $("#header_search").autocomplete({
        triggerSelectOnValidInput: false,
        showNoSuggestionNotice: true,
        noSuggestionNotice: "-- buna yakın bir sonuç yok --",

        lookup (lookup, done) {
            if (lookup.startsWith("@") && lookup.substr(1)) {
                const query = `{ autocomplete { authors(lookup: "${lookup.substr(1)}") { username } } }`;
                $.post("/graphql/", JSON.stringify({ query }), function (response) {
                    done({ suggestions: response.data.autocomplete.authors.map(user => ({ value: `@${user.username}` })) });
                });
            } else {
                const query = `{ autocomplete { authors(lookup: "${lookup}", limit: 3) { username } 
                                                topics(lookup: "${lookup}", limit: 7) { title } } }`;
                $.post("/graphql/", JSON.stringify({ query }), function (response) {
                    const topicSuggestions = response.data.autocomplete.topics.map(topic => ({ value: topic.title }));
                    const authorSuggestions = response.data.autocomplete.authors.map(user => ({ value: `@${user.username}` }));
                    done({ suggestions: topicSuggestions.concat(authorSuggestions) });
                });
            }
        },

        onSelect (suggestion) {
            window.location.replace("/topic/?q=" + suggestion.value);
        }
    });

    $(".author-search").autocomplete({
        lookup (lookup, done) {
            const query = `{ autocomplete { authors(lookup: "${lookup}") { username } } }`;
            $.post("/graphql/", JSON.stringify({ query }), function (response) {
                done({ suggestions: response.data.autocomplete.authors.map(user => ({ value: user.username })) });
            });
        },

        onSelect (suggestion) {
            $("input.author-search").val(suggestion.value);
        }
    });
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

$("select.page-selector").on("change", function () {
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
    const pk = $(self).closest("#rate").attr("data-entry-id");
    const query = `mutation { entry { favorite(pk: "${pk}") { feedback count } } }`;

    $.post("/graphql/", JSON.stringify({ query }), function (response) {
        const count = response.data.entry.favorite.count;
        const countHolder = $(self).next();

        $(self).toggleClass("fav-inverted");
        countHolder.text(count);

        if (count > 0) {
            countHolder.removeClass("dj-hidden");
        } else {
            countHolder.addClass("dj-hidden");
        }
    }).fail(function () {
        notify("bir şeyler yanlış gitti", "error");
    });
});

$(document).on("click", "div.entry_info div.rate .dropdown-menu, #dropdown_detailed_search :not(#close_search_dropdown), .autocomplete-suggestions", e => {
    e.stopPropagation();
});

$(".dropdown-fav-count").on("click", function () {
    const self = this;
    const favoritesList = $(self).next();
    const pk = $(self).closest("#rate").attr("data-entry-id");

    const query = `{ entry{ favoriters(pk:${pk}){ username isNovice } } } `;

    $.post("/graphql/", JSON.stringify({ query }), function (response) {
        const allUsers = response.data.entry.favoriters;
        const authors = allUsers.filter(user => user.isNovice === false);
        const novices = allUsers.filter(user => user.isNovice === true);

        favoritesList.html("");

        if (authors.length > 0) {
            for (const author of authors) {
                favoritesList.append(`<a class="author-name" href="/biri/${author.username}/">@${author.username}</a>`);
            }
        }

        if (novices.length > 0) {
            favoritesList.append(`<a id="show_novice_button" role="button" tabindex="0">...${novices.length} çaylak</a><span class="dj-hidden" id="favorites_list_novices"></span>`);

            $("a#show_novice_button").on("click", function () {
                $("#favorites_list_novices").toggleClass("dj-hidden");
            });

            for (const novice of novices) {
                $("#favorites_list_novices").append(`<a class="author-name novice" href="/biri/${novice.username}/">@${novice.username}</a>`);
            }
        }
    }).fail(function () {
        notify("bir şeyler yanlış gitti", "error");
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

const userAction = function (type, recipient) {
    const query = `mutation { user { ${type}(username: "${recipient}") { feedback redirect } } }`;
    $.post("/graphql/", JSON.stringify({ query }), function (response) {
        const info = response.data.user[type];
        if (info.redirect) {
            window.location.replace(info.redirect);
        } else {
            notify(info.feedback);
        }
    }).fail(function () {
        notify("bir şeyler yanlış gitti", "error");
    });
};

$(".block-user-trigger").on("click", function () {
    const username = $(this).attr("data-username");
    $("#block_user").attr("data-username", username);
    $("#username-holder").text(username);
    $("#blockUserModal").modal("show");
});

$("#block_user").on("click", function () {
    const targetUser = $(this).attr("data-username");
    userAction("block", targetUser);
    $("#blockUserModal").modal("hide");
});

$(".unblock-user-trigger").on("click", function () {
    if (confirm("engel kalksın mı?")) {
        userAction("block", $(this).attr("data-username"));
        $(this).hide();
    }
});

$(".follow-user-trigger").on("click", function () {
    const targetUser = $(this).parent().attr("data-username");
    userAction("follow", targetUser);
    $(this).children("a").toggleText("takip et", "takip etme");
});

const entryAction = (type, pk, redirect = false) => {
    const query = `mutation { entry { ${type}(pk: "${pk}") { feedback ${redirect ? "redirect" : ""}} } }`;
    $.post("/graphql/", JSON.stringify({ query }), function (response) {
        const info = response.data.entry[type];

        if (redirect) {
            window.location.replace(info.redirect);
        } else {
            notify(info.feedback);
        }
    }).fail(function () {
        notify("bir şeyler yanlış gitti", "error");
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

const topicAction = function (type, pk) {
    const query = `mutation { topic { ${type}(pk: "${pk}") { feedback } } }`;
    $.post("/graphql/", JSON.stringify({ query }), function (response) {
        const info = response.data.topic[type];
        notify(info.feedback);
    }).fail(function () {
        notify("bir şeyler yanlış gitti", "error");
    });
};

$(".follow-topic-trigger").on("click", function () {
    $(this).toggleText("takip etme", "takip et");
    topicAction("follow", $(this).attr("data-topic-id"));
});

$("select#mobile_year_changer").on("change", function () {
    window.location = updateQueryStringParameter(location.href, "year", this.value);
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
        window.location.replace(`/basliklar/${slug}/?${searchParameters}`);
    }
    LeftFrame.populate(slug, null, null, searchParameters);
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
    populateSearchResults(dictToParameters(keys));
});

const categoryAction = function (type, pk) {
    const query = `mutation { category { ${type}(pk: "${pk}") { feedback } } }`;
    $.post("/graphql/", JSON.stringify({ query })).fail(function () {
        notify("bir şeyler yanlış gitti", "error");
    });
};

const composeMessage = function (recipient, body) {
    const queryArgs = `body: "${body}", recipient: "${recipient}"`;
    const query = `mutation { message { compose(${queryArgs}) { feedback } } }`;
    $.post("/graphql/", JSON.stringify({ query }), function (response) {
        notify(response.data.message.compose.feedback);
    }).fail(function () {
        notify("o mesaj gitmedi yalnız", "error");
    });
};

$(".send-message-trigger").on("click", function () {
    const recipient = $(this).attr("data-recipient");
    $("#message_body[data-for]").attr("data-for", recipient);
    $("#sendMessageModal").modal("show");
});

$("#send_message_btn").on("click", function () {
    const textarea = $("textarea#message_body");
    const body = textarea.val();

    if (body.length < 3) {
        // not strictly needed but written so as to reduce api calls.
        notify("az bir şeyler yaz yeğenim");
        return;
    }

    const recipient = textarea.attr("data-for");
    $("#sendMessageModal").modal("hide");
    composeMessage(recipient, body);
    textarea.val("");
});

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

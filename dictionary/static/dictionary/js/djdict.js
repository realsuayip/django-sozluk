/* global Cookies gettext pgettext ngettext interpolate Dropzone notSafe notify gqlc findOne createTemplate */

"use strict";
(function () {
    const cookies = Cookies.withConverter({
        read (value) {
            return decodeURIComponent(value);
        },
        write (value) {
            return encodeURIComponent(value);
        }
    }).withAttributes({ sameSite: "Lax" });

    function isValidText (body) {
        return /^[A-Za-z0-9 ğçıöşüĞÇİÖŞÜ#&@()_+=':%/",.!?*~`[\]{}<>^;\\|-]+$/g.test(body.split(/[\r\n]+/).join());
    }

    function dictToParameters (dict) {
        const str = [];
        for (const key in dict) {
            // a. check if the property/key is defined in the object itself, not in parent
            // b. check if the key is not empty
            if (Object.prototype.hasOwnProperty.call(dict, key) && dict[key]) {
                str.push(encodeURIComponent(key) + "=" + encodeURIComponent(dict[key]));
            }
        }
        return str.join("&");
    }

    function addEvent (node, type, callback, ...args) {
        if (!node) {
            return;
        }

        node.addEventListener(type, callback, ...args);
    }

    function addEvents (nodes, type, callback, ...args) {
        nodes.forEach(node => {
            addEvent(node, type, callback, ...args);
        });
    }

    const userIsAuthenticated = findOne("body").id === "au";

    let userIsMobile = false;
    let lastScrollTop = 0;

    function hideRedundantHeader () {
        const delta = 30;
        const st = window.pageYOffset;
        const header = findOne("header.page_header");
        const sub = findOne(".sub-nav");

        if (Math.abs(lastScrollTop - st) <= delta) {
            return;
        }

        const reset = () => {
            sub.style.marginTop = "0";
            header.style.top = "0";
        };

        if (st > lastScrollTop) {
            // Down scroll code
            sub.style.marginTop = ".75em";
            header.style.top = "-55px";
            header.addEventListener("mouseover", reset, { once: true });
        } else {
            reset();
        }
        lastScrollTop = st;
    }

    const mql = window.matchMedia("(max-width: 810px)");

    function desktopView () {
        userIsMobile = false;

        // Find left frame scroll position.
        if (parseInt(localStorage.getItem("where")) > 0) {
            findOne("#left-frame-nav").scroll(0, localStorage.getItem("where"));
        }

        // Restore header.
        window.removeEventListener("scroll", hideRedundantHeader);
        findOne(".sub-nav").style.marginTop = "0";
        findOne("header.page_header").style.top = "0";

        // Code to render swh references properly (reverse)
        find("a[data-sup]").forEach(sup => {
            sup.innerHTML = `*`;
        });
    }

    function mobileView () {
        userIsMobile = true;
        // Code to hide some part of the header on mobile scroll.
        window.addEventListener("scroll", hideRedundantHeader);

        // Code to render swh references properly
        find("a[data-sup]").forEach(sup => {
            sup.innerHTML = `<sup>${sup.getAttribute("data-sup")}</sup>`;
        });
    }

    function mqlsw (mql) {
        // check mql & switch
        if (mql.matches) {
            mobileView();
        } else {
            desktopView();
        }
    }

    // Safari doesn't support mql.addEventListener yet, so we have
    // to use deprecated addListener.
    mql.addListener(mqlsw);

    document.addEventListener("DOMContentLoaded", () => {
        // DOM ready.
        mqlsw(mql);

        // Handles notifications passed by django's message framework.
        const requestMessages = findOne("#request-messages");
        if (requestMessages.getAttribute("data-has-messages") === "true") {
            let delay = 2000;
            requestMessages.childNodes.forEach(message => {
                const isPersistent = message.getAttribute("data-extra").includes("persistent");
                notify(message.getAttribute("data-message"), message.getAttribute("data-level"), delay, isPersistent);
                delay += 1000;
            });
        }
    });

    function setExclusions (exclusions) {
        const cookieExclusions = JSON.parse(cookies.get("lfex") || "null");
        if (exclusions) {
            if (cookieExclusions) {
                for (const exclusion of exclusions) {
                    if (cookieExclusions.includes(exclusion)) {
                        exclusions = cookieExclusions.filter(item => item !== exclusion);
                    } else {
                        cookieExclusions.push(exclusion);
                        exclusions = cookieExclusions;
                    }
                }
            }
            cookies.set("lfex", JSON.stringify(exclusions));
            return exclusions;
        } else {
            return cookieExclusions;
        }
    }

    class LeftFrame {
        constructor (slug, page = 1, year = null, searchKeys = null, refresh = false, tab = null, exclusions = null, extra = null) {
            this.slug = slug;
            this.page = page;
            this.year = year;
            this.refresh = refresh;
            this.searchKeys = searchKeys;
            this.tab = tab;
            this.exclusions = exclusions;
            this.extra = extra;

            this.setCookies();
            this.loadIndicator = findOne("#load_indicator");
        }

        setCookies () {
            cookies.set("lfac", this.slug);
            cookies.set("lfnp", this.page);

            if (this.tab) {
                cookies.set("lfat", this.tab);
            } else {
                this.tab = cookies.get("lfat") || null;
            }

            if (this.extra) {
                cookies.set("lfea", this.extra);
            } else {
                this.extra = cookies.get("lfea") || null;
            }

            if (this.slug === "today-in-history") {
                const cookieYear = cookies.get("lfsy");
                if (!this.year) {
                    this.year = cookieYear || null;
                } else {
                    cookies.set("lfsy", this.year);
                }
            } else if (this.slug === "search") {
                const cookieSearchKeys = cookies.get("lfsp");
                if (!this.searchKeys) {
                    this.searchKeys = cookieSearchKeys || null;
                } else {
                    cookies.set("lfsp", this.searchKeys);
                }
            } else if (this.slug === "popular") {
                this.exclusions = setExclusions(this.exclusions);
            }
        }

        call () {
            this.loadIndicator.style.display = "inline";
            const variables = {
                slug: this.slug,
                year: this.year,
                page: this.page,
                searchKeys: this.searchKeys,
                refresh: this.refresh,
                tab: this.tab,
                exclusions: this.exclusions,
                extra: this.extra
            };

            const query = `query($slug: String!,$year:Int,$page:Int,$searchKeys:String,$refresh:Boolean,$tab:String,
            $exclusions:[String],$extra:JSONString){topics(slug:$slug,year:$year,page:$page,searchKeys:$searchKeys,
            refresh:$refresh,tab:$tab,exclusions:$exclusions,extra:$extra){
                safename refreshCount year yearRange slugIdentifier parameters
                page { objectList { slug title count } paginator { pageRange numPages } number hasOtherPages }
                tabs{current available{name, safename}}
                exclusions{active, available{name, slug, description}}
            }}`;

            const self = this;

            gqlc({ query, variables }, true).then(response => {
                if (response.errors) {
                    self.loadIndicator.style.display = "none";
                    notify(gettext("something went wrong"), "error");
                } else {
                    self.render(response.data.topics);
                }
            });
        }

        render (data) {
            findOne("#left-frame-nav").scroll({ top: 0, behavior: "smooth" });
            findOne("#current_category_name").textContent = data.safename;
            this.renderRefreshButton(data.refreshCount);
            this.renderYearSelector(data.year, data.yearRange);
            this.renderPagination(data.page.hasOtherPages, data.page.paginator.pageRange, data.page.paginator.numPages, data.page.number);
            this.renderTopicList(data.page.objectList, data.slugIdentifier, data.parameters);
            this.renderShowMoreButton(data.page.number, data.page.hasOtherPages);
            this.renderTabs(data.tabs);
            this.renderExclusions(data.exclusions);
            this.loadIndicator.style.display = "none";
        }

        renderRefreshButton (count) {
            const refreshButton = findOne("#refresh_bugun");
            if (count) {
                refreshButton.classList.remove("dj-hidden");
                findOne("span#new_content_count").textContent = `(${count})`;
            } else {
                refreshButton.classList.add("dj-hidden");
            }
        }

        renderShowMoreButton (currentPage, isPaginated) {
            const showMoreButton = findOne("a#show_more");

            if (currentPage !== 1 || !isPaginated) {
                showMoreButton.classList.add("dj-hidden");
            } else {
                showMoreButton.classList.remove("dj-hidden");
            }
        }

        renderTabs (tabData) {
            const tabHolder = findOne("ul#left-frame-tabs");
            if (tabData) {
                tabHolder.innerHTML = "";
                const availableTabs = tabData.available;
                const current = tabData.current;
                for (const tab of availableTabs) {
                    tabHolder.innerHTML += `<li class="nav-item"><a role="button" tabindex="0" data-lf-slug="${this.slug}" data-tab="${tab.name}" class="nav-link${current === tab.name ? " active" : ""}">${tab.safename}</a></li>`;
                }
                tabHolder.classList.remove("dj-hidden");
            } else {
                tabHolder.classList.add("dj-hidden");
            }
        }

        renderExclusions (exclusions) {
            const toggler = findOne("#popular_excluder");
            const categoryHolder = findOne("#exclusion-choices");
            const categoryList = categoryHolder.querySelector("ul.exclusion-choices");

            if (exclusions) {
                categoryList.innerHTML = "";
                toggler.classList.remove("dj-hidden");

                for (const category of exclusions.available) {
                    const isActive = exclusions.active.includes(category.slug);
                    categoryList.innerHTML += `<li><a role="button" title="${category.description}" ${isActive ? `class="active"` : ""} tabindex="0" data-slug="${category.slug}">#${category.name}</a></li>`;
                }
                if (exclusions.active.length) {
                    toggler.classList.add("active");
                } else {
                    toggler.classList.remove("active");
                }
            } else {
                toggler.classList.add("dj-hidden");
                categoryHolder.style.display = "none";
            }
        }

        renderYearSelector (currentYear, yearRange) {
            const yearSelect = findOne("#year_select");
            yearSelect.innerHTML = "";

            if (this.slug === "today-in-history") {
                yearSelect.style.display = "block";
                for (const year of yearRange) {
                    yearSelect.innerHTML += `<option ${year === currentYear ? "selected" : ""} id="${year}">${year}</option>`;
                }
            } else {
                yearSelect.style.display = "none";
            }
        }

        renderTopicList (objectList, slugIdentifier, parameters) {
            const topicList = findOne("ul#topic-list");
            if (objectList.length === 0) {
                topicList.innerHTML = `<small>${gettext("nothing here")}</small>`;
            } else {
                topicList.innerHTML = "";
                const params = parameters || "";

                let topics = "";

                for (const topic of objectList) {
                    topics += `<li class="list-group-item"><a href="${slugIdentifier}${topic.slug}/${params}">${notSafe(topic.title)}<small class="total_entries">${topic.count && topic.count !== "0" ? topic.count : ""}</small></a></li>`;
                }

                if (topics) {
                    topicList.innerHTML = topics;
                }
            }
        }

        renderPagination (isPaginated, pageRange, totalPages, currentPage) {
            // Pagination related selectors
            const paginationWrapper = findOne("#lf_pagination_wrapper");
            const pageSelector = findOne("select#left_frame_paginator");
            const totalPagesButton = findOne("#lf_total_pages");

            // Render pagination
            if (isPaginated && currentPage !== 1) {
                // Render Page selector
                pageSelector.innerHTML = "";
                let options = "";

                for (const page of pageRange) {
                    options += `<option ${page === currentPage ? "selected" : ""} value="${page}">${page}</option>`;
                }

                pageSelector.innerHTML += options;
                totalPagesButton.textContent = totalPages;
                paginationWrapper.classList.remove("dj-hidden");
            } else {
                paginationWrapper.classList.add("dj-hidden");
            }
        }

        static populate (slug, page = 1, ...args) {
            if (userIsMobile) {
                return;
            }
            const leftFrame = new LeftFrame(slug, page, ...args);
            leftFrame.call();
        }

        static refreshPopulate () {
            LeftFrame.populate("today", 1, null, null, true);
        }
    }

    /* Start of LefFrame related triggers */

    findOne("body").addEventListener("click", event => {
        // Regular, slug-only
        const delegated = event.target.closest("[data-lf-slug]");

        if (delegated && !userIsMobile) {
            const slug = delegated.getAttribute("data-lf-slug");
            const tab = delegated.getAttribute("data-tab") || null;
            const extra = delegated.getAttribute("data-lf-extra") || null;
            LeftFrame.populate(slug, 1, null, null, false, tab, null, extra);

            if (delegated.classList.contains("dropdown-item")) {
                // Prevents dropdown collapsing, good for accessibility.
                event.stopPropagation();
            }
            event.preventDefault();
        }
    });

    addEvent(findOne("#year_select"), "change", function () {
        const selectedYear = this.value;
        LeftFrame.populate("today-in-history", 1, selectedYear);
    });

    addEvent(findOne("select#left_frame_paginator"), "change", function () {
        LeftFrame.populate(cookies.get("lfac"), this.value);
    });

    const selector = findOne("select#left_frame_paginator");
    const totalPagesElement = findOne("#lf_total_pages");
    const changeEvent = new Event("change");

    addEvent(totalPagesElement, "click", function () {
        // Navigated to last page
        if (selector.value === this.textContent) {
            return;
        }

        selector.value = this.textContent;
        selector.dispatchEvent(changeEvent);
    });

    addEvent(findOne("#lf_navigate_before"), "click", () => {
        // Previous page
        const selected = parseInt(selector.value);
        if (selected - 1 > 0) {
            selector.value = selected - 1;
            selector.dispatchEvent(changeEvent);
        }
    });

    addEvent(findOne("#lf_navigate_after"), "click", () => {
        // Subsequent page
        const selected = parseInt(selector.value);
        const max = parseInt(totalPagesElement.textContent);
        if (selected + 1 <= max) {
            selector.value = selected + 1;
            selector.dispatchEvent(changeEvent);
        }
    });

    addEvent(findOne("a#show_more"), "click", function () {
        // Show more button event
        const slug = cookies.get("lfac");

        if (slug) {
            LeftFrame.populate(slug, 2);
        }

        this.classList.add("dj-hidden");
    });

    addEvent(findOne("#refresh_bugun"), "click", LeftFrame.refreshPopulate);

    addEvents(find(".exclusion-button"), "click", function () {
        this.closest("div").parentNode.querySelector(".exclusion-settings").classList.toggle("dj-hidden");
    });

    addEvent(findOne("#exclusion-choices"), "click", event => {
        if (event.target.tagName === "A") {
            event.target.classList.toggle("active");
            LeftFrame.populate("popular", 1, null, null, null, null, [event.target.getAttribute("data-slug")]);
        }
    });

    addEvent(findOne("#exclusion-settings-mobile"), "click", event => {
        if (event.target.tagName === "A") {
            setExclusions([event.target.getAttribute("data-slug")]);
            window.location = location;
        }
    });

    addEvents(find("[data-lf-slug]"), "click", function () {
        find("[data-lf-slug]").forEach(el => el.classList.remove("active"));
        find(`[data-lf-slug=${this.getAttribute("data-lf-slug")}]`).forEach(el => el.classList.add("active"));
    });

    /* End of LefFrame related triggers */

    // https://stackoverflow.com/questions/5999118/how-can-i-add-or-update-a-query-string-parameter
    function updateQueryStringParameter (uri, key, value) {
        const re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
        const separator = uri.indexOf("?") !== -1 ? "&" : "?";
        if (uri.match(re)) {
            return uri.replace(re, "$1" + key + "=" + value + "$2");
        } else {
            return uri + separator + key + "=" + value;
        }
    }

    addEvent(findOne("select.page-selector"), "change", function () {
        window.location = updateQueryStringParameter(location.href, "page", this.value);
    });

    function insertAtCaret (el, insertValue) {
        const startPos = el.selectionStart;
        if (startPos) {
            console.log(insertValue);
            const endPos = el.selectionEnd;
            const scrollTop = el.scrollTop;
            el.value = el.value.substring(0, startPos) + insertValue + el.value.substring(endPos, el.value.length);
            el.focus();
            el.selectionStart = startPos + insertValue.length;
            el.selectionEnd = startPos + insertValue.length;
            el.scrollTop = scrollTop;
        } else {
            el.value += insertValue;
            el.focus();
        }
    }

    function toggleText (el, a, b) {
        el.textContent = el.textContent === b ? a : b;
    }

    function insertMeta (type) {
        let fmt;

        switch (type) {
            case "ref":
                fmt = [gettext("target topic, #entry or @author to reference:"), text => `(${pgettext("editor", "see")}: ${text})`];
                break;
            case "thingy":
                fmt = [gettext("target topic, #entry or @author to thingy:"), text => `\`${text}\``];
                break;
            case "swh":
                fmt = [gettext("what should be referenced in asterisk?"), text => `\`:${text}\``];
                break;
            case "spoiler": {
                const spoiler = gettext("spoiler");
                fmt = [gettext("what to write between spoiler tags?"), text => `--\`${spoiler}\`--\n${text}\n--\`${spoiler}\`--`];
                break;
            }
        }

        return { label: fmt[0], format: fmt[1] };
    }

    function replaceText (elementId, type) {
        const textArea = document.getElementById(elementId);
        const start = textArea.selectionStart;
        const finish = textArea.selectionEnd;
        const allText = textArea.value;
        const sel = allText.substring(start, finish);
        if (!sel) {
            return false;
        } else {
            if (type === "link") {
                const linkText = prompt(gettext("which address to link?"), "http://");
                if (linkText !== "http://") {
                    textArea.value = allText.substring(0, start) + `[${linkText} ${sel}]` + allText.substring(finish, allText.length);
                }
            } else {
                textArea.value = allText.substring(0, start) + insertMeta(type).format(sel) + allText.substring(finish, allText.length);
            }
            textArea.focus();
            return true;
        }
    }

    addEvent(findOne("button#insert_image"), "click", () => {
        const dropzone = findOne(".dropzone");
        dropzone.style.display = dropzone.style.display === "none" ? "" : "none";
    });

    addEvents(find("button.insert"), "click", function () {
        const type = this.getAttribute("data-type");
        if (!replaceText("user_content_edit", type)) {
            const meta = insertMeta(type);
            const text = prompt(meta.label);
            if (text) {
                insertAtCaret(findOne("#user_content_edit"), meta.format(text));
            }
        }
    });

    addEvent(findOne("button#insert_link"), "click", () => {
        if (!replaceText("user_content_edit", "link")) {
            const linkText = prompt(gettext("which address to link?"), "http://");
            if (linkText && linkText !== "http://") {
                const linkName = prompt(gettext("alias for the link?"));
                if (linkName) {
                    insertAtCaret(findOne("#user_content_edit"), `[${linkText} ${linkName}]`);
                }
            }
        }
    });

    addEvents(find("a.favorite[role='button']"), "click", function () {
        const pk = this.closest(".entry-full").getAttribute("data-id");

        gqlc({ query: `mutation{entry{favorite(pk:"${pk}"){feedback count}}}` }).then(response => {
            const count = response.data.entry.favorite.count;
            const countHolder = this.nextElementSibling;

            this.classList.toggle("active");

            if (count === 0) {
                countHolder.textContent = "";
                countHolder.setAttribute("tabindex", "-1");
            } else {
                countHolder.textContent = count;
                countHolder.setAttribute("tabindex", "0");
            }

            this.parentNode.querySelector("span.favorites-list").setAttribute("data-loaded", "false");
        });
    });

    addEvents(find("a.fav-count[role='button']"), "click", function () {
        const favoritesList = this.nextElementSibling;

        if (favoritesList.getAttribute("data-loaded") === "true") {
            return;
        }

        favoritesList.innerHTML = "<div class='px-3 py-1'><div class='spinning'><span style='font-size: 1.25em'>&orarr;</span></div></div>";

        const pk = this.closest(".entry-full").getAttribute("data-id");

        gqlc({ query: `{entry{favoriters(pk:${pk}){username slug isNovice}}}` }).then(response => {
            const allUsers = response.data.entry.favoriters;
            const authors = allUsers.filter(user => user.isNovice === false);
            const novices = allUsers.filter(user => user.isNovice === true);

            favoritesList.innerHTML = "";
            favoritesList.setAttribute("data-loaded", "true");

            if (!allUsers.length) {
                favoritesList.innerHTML = `<span class='p-2'>${gettext("actually, nothing here.")}</span>`;
                return;
            }

            let favList = "";

            if (authors.length > 0) {
                for (const author of authors) {
                    favList += `<a class="author" href="/author/${author.slug}/">@${author.username}</a>`;
                }
                favoritesList.innerHTML = favList;
            }

            if (novices.length > 0) {
                const noviceString = interpolate(ngettext("... %(count)s novice", "... %(count)s novices", novices.length), { count: novices.length }, true);
                const noviceToggle = createTemplate(`<a role="button" tabindex="0">${noviceString}</a>`);
                const noviceList = createTemplate(`<span class="dj-hidden"></span>`);

                favoritesList.append(noviceToggle);
                noviceToggle.addEventListener("click", () => {
                    noviceList.classList.toggle("dj-hidden");
                });

                favList = "";

                for (const novice of novices) {
                    favList += `<a class="novice" href="/author/${novice.slug}/">@${novice.username}</a>`;
                }
                noviceList.innerHTML = favList;
                favoritesList.append(noviceList);
            }
        });
    });

    addEvent(findOne("a#message_history_show"), "click", function () {
        find("ul#message_list li.bubble").forEach(item => {
            item.style.display = "list-item";
        });
        this.classList.add("dj-hidden");
    });

    function userAction (type, recipient, loc = null, re = true) {
        gqlc({ query: `mutation{user{${type}(username:"${recipient}"){feedback redirect}}}` }).then(function (response) {
            const info = response.data.user[type];
            if (re && (loc || info.redirect)) {
                window.location = loc || info.redirect;
            } else {
                notify(info.feedback);
            }
        });
    }

    function showBlockDialog (recipient, redirect = true) {
        const button = findOne("#block_user");
        button.setAttribute("data-username", recipient);
        button.setAttribute("data-re", redirect);
        findOne("#username-holder").textContent = recipient;

        const modal = findOne("#blockUserModal");
        modal._modalInstance.show();
    }

    function showMessageDialog (recipient, extraContent) {
        const msgModal = findOne("#sendMessageModal");
        findOne("#sendMessageModal span.username").textContent = recipient;

        if (extraContent) {
            findOne("#sendMessageModal textarea#message_body").value = extraContent;
        }

        msgModal.setAttribute("data-for", recipient);
        msgModal._modalInstance.show();
    }

    addEvents(find(".entry-actions"), "click", function (event) {
        if (event.target.classList.contains("block-user-trigger")) {
            const target = this.parentNode.querySelector(".username").textContent;
            const profile = findOne(".profile-username");
            const re = profile && profile.textContent === target;
            showBlockDialog(target, re);
        }
    });

    addEvent(findOne("#block_user"), "click", function () {
        // Modal button click event
        const targetUser = this.getAttribute("data-username");
        const re = this.getAttribute("data-re") === "true";
        if (!re) {
            find(".entry-full").forEach(entry => {
                if (entry.querySelector(".meta .username").textContent === targetUser) {
                    entry.remove();
                }
            });
        }
        userAction("block", targetUser, null, re);
    });

    addEvent(findOne(".unblock-user-trigger"), "click", function () {
        if (confirm(gettext("Are you sure?"))) {
            let loc;
            if (this.classList.contains("sync")) {
                loc = location;
            } else {
                this.classList.toggle("dj-hidden");
            }
            userAction("block", this.getAttribute("data-username"), loc);
        }
    });

    addEvents(find(".follow-user-trigger"), "click", function () {
        const targetUser = this.parentNode.getAttribute("data-username");
        userAction("follow", targetUser);
        toggleText(this.querySelector("a"), gettext("follow"), gettext("unfollow"));
    });

    function entryAction (type, pk, redirect = false) {
        return gqlc({ query: `mutation{entry{${type}(pk:"${pk}"){feedback ${redirect ? "redirect" : ""}}}}` });
    }

    addEvents(find("a.twitter[role='button'], a.facebook[role='button']"), "click", function () {
        const base = this.classList.contains("twitter") ? "https://twitter.com/intent/tweet?text=" : "https://www.facebook.com/sharer/sharer.php?u=";
        const entry = this.closest(".entry-footer").querySelector(".meta .permalink").getAttribute("href");
        const windowReference = window.open();
        windowReference.opener = null;
        windowReference.location = `${base}${window.location.origin}${entry}`;
    });

    addEvents(find(".entry-vote .vote"), "click", function () {
        const type = this.classList.contains("upvote") ? "upvote" : "downvote";
        const entryId = this.closest(".entry-full").getAttribute("data-id");
        entryAction(type, entryId).then(response => {
            const feedback = response.data.entry[type].feedback;
            if (feedback == null) {
                const sibling = this.nextElementSibling || this.previousElementSibling;
                sibling.classList.remove("active");
                this.classList.toggle("active");
            } else {
                notify(feedback, "error", 4000);
            }
        });
    });

    addEvents(find(".comment-vote .vote"), "click", function () {
        const action = this.classList.contains("upvote") ? "upvote" : "downvote";
        const pk = this.parentNode.getAttribute("data-id");
        gqlc({
            query: "mutation($pk:ID!,$action:String!){entry{votecomment(pk:$pk,action:$action){count}}}",
            variables: { pk, action }
        }).then(response => {
            if (response.errors) {
                for (const error of response.errors) {
                    notify(error.message, "error");
                }
                return;
            }

            this.parentNode.querySelectorAll(".vote").forEach(el => {
                el !== this && el.classList.remove("active");
            });

            this.classList.toggle("active");
            this.parentNode.querySelector(".rating").textContent = response.data.entry.votecomment.count;
        });
    });

    addEvents(find(".suggestion-vote button"), "click", function () {
        const direction = this.classList.contains("up") ? 1 : -1;
        const topic = this.parentNode.getAttribute("data-topic");
        const category = this.parentNode.getAttribute("data-category");

        gqlc({
            query: "mutation($category:String!,$topic:String!,$direction:Int!){category{suggest(category:$category,topic:$topic,direction:$direction){feedback}}}",
            variables: { category, topic, direction }
        }).then(response => {
            if (response.errors) {
                for (const error of response.errors) {
                    notify(error.message, "error");
                }
            } else {
                this.classList.toggle("btn-django-link");
                const sibling = this.nextElementSibling || this.previousElementSibling;
                sibling.classList.remove("btn-django-link");
            }
        });
    });

    addEvents(find(".entry-actions"), "click", function (event) {
        if (event.target.classList.contains("delete-entry")) {
            if (confirm(gettext("are you sure to delete?"))) {
                const entry = this.closest(".entry-full");
                const redirect = find("ul.topic-view-entries li.entry-full").length === 1;

                entryAction("delete", entry.getAttribute("data-id"), redirect).then(response => {
                    const data = response.data.entry.delete;
                    if (redirect) {
                        window.location = data.redirect;
                    } else {
                        entry.remove();
                        notify(data.feedback);
                    }
                });
            }
        }
    });

    addEvent(findOne(".delete-entry-redirect"), "click", function () {
        if (confirm(gettext("are you sure to delete?"))) {
            entryAction("delete", this.getAttribute("data-target-entry"), true).then(response => {
                window.location = response.data.entry.delete.redirect;
            });
        }
    });

    addEvents(find(".entry-actions"), "click", function (event) {
        if (event.target.classList.contains("pin-entry")) {
            const entryID = this.closest(".entry-full").getAttribute("data-id");
            const body = findOne("body");
            entryAction("pin", entryID).then(response => {
                find("a.action[role='button']").forEach(action => {
                    action.classList.remove("loaded");
                });

                if (body.getAttribute("data-pin") === entryID) {
                    body.removeAttribute("data-pin");
                } else {
                    body.setAttribute("data-pin", entryID);
                }

                notify(response.data.entry.pin.feedback);
            });
        }
    });

    addEvent(findOne(".pin-sync"), "click", function () {
        entryAction("pin", this.getAttribute("data-id")).then(response => {
            notify(response.data.entry.pin.feedback);
            window.location = location;
        });
    });

    function topicAction (type, pk) {
        return gqlc({ query: `mutation{topic{${type}(pk:"${pk}"){feedback}}}` }).then(response => {
            notify(response.data.topic[type].feedback);
        });
    }

    addEvent(findOne(".follow-topic-trigger"), "click", function () {
        toggleText(this, gettext("unfollow"), gettext("follow"));
        topicAction("follow", this.getAttribute("data-topic-id"));
    });

    addEvent(findOne("select#mobile_year_changer"), "change", function () {
        window.location = updateQueryStringParameter(location.href, "year", this.value);
    });

    function truncateEntryText () {
        const overflown = el => el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;
        find("article.entry p").forEach(el => {
            if (overflown(el)) {
                const readMore = createTemplate(`<div role="button" tabindex="0" class="read_more">${gettext("continue reading")}</div>`);
                el.parentNode.append(readMore);
                addEvent(readMore, "click", function () {
                    el.style.maxHeight = "none";
                    this.style.display = "none";
                });
            }
        });
    }

    window.onload = () => {
        if (findOne("body").classList.contains("has-entries")) {
            truncateEntryText();
        }
    };

    function populateSearchResults (searchParameters) {
        if (!searchParameters) {
            return;
        }

        const slug = "search";

        if (userIsMobile) {
            window.location = `/threads/${slug}/?${searchParameters}`;
        }
        LeftFrame.populate(slug, 1, null, searchParameters);
    }

    addEvent(findOne("button#perform_advanced_search"), "click", () => {
        const favoritesElement = findOne("input#in_favorites_dropdown");

        const keywords = findOne("input#keywords_dropdown").value;
        const authorNick = findOne("input#author_nick_dropdown").value;
        const isNiceOnes = findOne("input#nice_ones_dropdown").checked;
        const isFavorites = favoritesElement && favoritesElement.checked;
        const fromDate = findOne("input#date_from_dropdown").value;
        const toDate = findOne("input#date_to_dropdown").value;
        const ordering = findOne("select#ordering_dropdown").value;

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

    function categoryAction (type, pk) {
        return gqlc({ query: `mutation{category{${type}(pk:"${pk}"){feedback}}}` });
    }

    function composeMessage (recipient, body) {
        const variables = { recipient, body };
        const query = `mutation compose($body:String!,$recipient:String!){message{compose(body:$body,recipient:$recipient){feedback}}}`;
        return gqlc({ query, variables }).then(function (response) {
            notify(response.data.message.compose.feedback);
        });
    }

    addEvents(find(".entry-actions"), "click", function (event) {
        if (event.target.classList.contains("send-message-trigger")) {
            const recipient = this.parentNode.querySelector(".username").textContent;
            const entryInQuestion = this.closest(".entry-full").getAttribute("data-id");
            showMessageDialog(recipient, `\`#${entryInQuestion}\`:\n`);
        }
    });

    addEvent(findOne("#send_message_btn"), "click", function () {
        const textarea = findOne("#sendMessageModal textarea");
        const msgModal = findOne("#sendMessageModal");
        const body = textarea.value;

        if (body.length < 3) {
            // not strictly needed but written so as to reduce api calls.
            notify(gettext("if only you could write down something"), "error");
            return;
        }

        if (!isValidText(body)) {
            notify(gettext("this content includes forbidden characters."), "error");
            return;
        }

        this.disabled = true;

        composeMessage(msgModal.getAttribute("data-for"), body).then(() => {
            msgModal._modalInstance.hide();
            textarea.value = "";
        }).finally(() => {
            this.disabled = false;
        });
    });

    addEvents(find("button.follow-category-trigger"), "click", function () {
        categoryAction("follow", this.getAttribute("data-category-id")).then(() => {
            toggleText(this, pgettext("category-list", "unfollow"), pgettext("category-list", "follow"));
            this.classList.toggle("faded");
        });
    });

    addEvent(findOne("form.search_mobile, form.reporting-form"), "submit", function () {
        Array.from(this.querySelectorAll("input")).filter(input => {
            if (input.type === "checkbox" && !input.checked) {
                return true;
            }
            return input.value === "";
        }).forEach(input => {
            input.disabled = true;
        });
        return false;
    });

    addEvent(findOne("body"), "keypress", event => {
        if (event.target.matches("[role=button], .key-clickable") && (event.key === " " || event.key === "Enter")) {
            event.preventDefault();
            event.target.dispatchEvent(new Event("click"));
        }
    });

    addEvents(find("a[role=button].quicksearch"), "click", function () {
        const term = this.getAttribute("data-keywords");
        let parameter;
        if (term.startsWith("@") && term.substr(1)) {
            parameter = `author_nick=${term.substr(1)}`;
        } else {
            parameter = `keywords=${term}`;
        }
        const searchParameters = parameter + "&ordering=newer";
        populateSearchResults(searchParameters);
    });

    addEvent(findOne("#left-frame-nav"), "scroll", function () {
        localStorage.setItem("where", this.scrollTop);
    });

    addEvents(find(".entry-full a.action[role='button']"), "click", function () {
        // todo-> move action events here?.
        if (this.classList.contains("loaded")) {
            return;
        }

        const entry = this.closest(".entry-full");
        const entryID = entry.getAttribute("data-id");
        const topicTitle = encodeURIComponent(entry.closest("[data-topic]").getAttribute("data-topic"));
        const actions = this.parentNode.querySelector(".entry-actions");
        const pinLabel = entryID === findOne("body").getAttribute("data-pin") ? gettext("unpin from profile") : gettext("pin to profile");

        actions.innerHTML = "";

        if (userIsAuthenticated) {
            if (entry.classList.contains("commentable")) {
                actions.innerHTML += `<a target="_blank" href="/entry/${entryID}/comment/" class="dropdown-item">${gettext("comment")}</a>`;
            }
            if (entry.classList.contains("owner")) {
                actions.innerHTML += `<a role="button" tabindex="0" class="dropdown-item pin-entry">${pinLabel}</a>`;
                actions.innerHTML += `<a role="button" tabindex="0" class="dropdown-item delete-entry">${gettext("delete")}</a>`;
                actions.innerHTML += `<a href="/entry/update/${entryID}/" class="dropdown-item">${gettext("edit")}</a>`;
            } else {
                if (!entry.classList.contains("private")) {
                    actions.innerHTML += `<a role="button" tabindex="0" class="dropdown-item send-message-trigger">${gettext("message")}</a>`;
                    actions.innerHTML += `<a role="button" tabindex="0" class="dropdown-item block-user-trigger">${gettext("block")}</a>`;
                }
            }
        }

        actions.innerHTML += `<a class="dropdown-item" href="/contact/?referrer_entry=${entryID}&referrer_topic=${topicTitle}">${gettext("report")}</a>`;
        this.classList.add("loaded");
    });

    addEvent(findOne("ul.user-links"), "click", function (event) {
        let dialog;

        if (event.target.matches("li.block-user a")) {
            dialog = showBlockDialog;
        } else if (event.target.matches("li.send-message a")) {
            dialog = showMessageDialog;
        }

        if (dialog) {
            const recipient = this.getAttribute("data-username");
            dialog(recipient);
        }
    });

    function wishTopic (title, hint = null) {
        const query = `mutation wish($title:String!,$hint:String){topic{wish(title:$title,hint:$hint){feedback hint}}}`;
        const variables = { title, hint };
        return gqlc({ query, variables });
    }

    addEvent(findOne("a.wish-prepare[role=button]"), "click", function () {
        this.parentNode.querySelectorAll(":not(.wish-purge):not(.wish-prepare)").forEach(el => {
            el.classList.toggle("dj-hidden");
        });
        toggleText(this, gettext("someone should populate this"), gettext("nevermind"));
    });

    addEvent(findOne("a.wish-send[role=button]"), "click", function () {
        const textarea = this.parentNode.querySelector("textarea");
        const hint = textarea.value;

        if (hint && !isValidText(hint)) {
            notify(gettext("this content includes forbidden characters."), "error");
            return;
        }

        const title = this.parentNode.getAttribute("data-topic");
        wishTopic(title, hint).then(response => {
            if (response.errors) {
                for (const error of response.errors) {
                    notify(error.message, "error");
                }
                return;
            }
            textarea.value = "";
            Array.from(this.parentNode.children).forEach(child => {
                child.classList.toggle("dj-hidden");
            });
            const hintFormatted = response.data.topic.wish.hint;
            const wishList = findOne("ul#wish-list");
            wishList.classList.remove("dj-hidden");
            wishList.prepend(createTemplate(`<li class="list-group-item owner">${gettext("you just wished for this topic.")} ${hintFormatted ? `${gettext("your hint:")} <p class="m-0 text-formatted"><i>${hintFormatted}</i></p>` : ""}</li>`));
            window.scrollTo({ top: 0, behavior: "smooth" });
            notify(response.data.topic.wish.feedback);
        });
    });

    addEvent(findOne("a.wish-purge[role=button]"), "click", function () {
        const title = this.parentNode.getAttribute("data-topic");
        if (confirm(gettext("are you sure to delete?"))) {
            wishTopic(title).then(response => {
                this.classList.toggle("dj-hidden");
                const wishList = findOne("ul#wish-list");
                const popButton = this.parentNode.querySelector(".wish-prepare");

                popButton.textContent = gettext("someone should populate this");
                popButton.classList.toggle("dj-hidden");
                wishList.querySelector("li.owner").remove();

                if (!wishList.children.length) {
                    wishList.classList.add("dj-hidden");
                }

                notify(response.data.topic.wish.feedback);
            });
        }
    });

    addEvent(findOne(".content-skipper"), "click", function () {
        location.replace(this.getAttribute("data-href"));
    });

    addEvents(find("input.is-invalid"), "input", function () {
        this.classList.remove("is-invalid");
    });

    addEvents(find("textarea#user_content_edit, textarea#message-body"), "input", function () {
        window.onbeforeunload = () => this.value || null;
    });

    addEvents(find("textarea.expandable"), "focus", function () {
        this.style.height = `${this.offsetHeight + 150}px`;
        addEvent(this, "transitionend", () => {
            this.style.transition = "none";
        });
    }, { once: true });

    addEvents(find("form"), "submit", function (event) {
        window.onbeforeunload = null;

        const userInput = this.querySelector("#user_content_edit");

        if (userInput && userInput.value) {
            if (!isValidText(userInput.value)) {
                notify(gettext("this content includes forbidden characters."), "error");
                window.onbeforeunload = () => true;
                event.preventDefault();
                return false;
            }
        }
    });

    // Conversation actions functionality

    addEvents(find("input.chat-selector"), "change", function () {
        this.closest("li.chat").classList.toggle("selected");
    });

    addEvent(findOne("a[role=button].chat-reverse"), "click", () => {
        find("input.chat-selector").forEach(input => {
            input.checked = !input.checked;
            input.dispatchEvent(new Event("change"));
        });
    });

    function getPkSet (selected) {
        const pkSet = [];
        selected.forEach(el => {
            pkSet.push(el.getAttribute("data-id"));
        });
        return pkSet;
    }

    function selectChat (init) {
        // inbox.html || conversation.html
        let chat = init.closest("li.chat");
        if (!chat) {
            chat = init.parentNode;
        }
        return chat;
    }

    function deleteConversation (pkSet, mode) {
        const query = `mutation($pkSet:[ID!]!, $mode:String){message{deleteConversation(pkSet:$pkSet,mode:$mode){redirect}}}`;
        const variables = { pkSet, mode };
        return gqlc({ query, variables });
    }

    addEvents(find("a[role=button].chat-delete-individual"), "click", function () {
        if (!confirm(gettext("are you sure to delete?"))) {
            return false;
        }

        const chat = selectChat(this);
        const mode = (findOne("ul.threads") || chat).getAttribute("data-mode");

        deleteConversation(chat.getAttribute("data-id"), mode).then(response => {
            const data = response.data.message.deleteConversation;
            if (data) {
                if (find("li.chat").length > 1) {
                    chat.remove();
                    notify(gettext("deleted conversation"));
                } else {
                    window.location = data.redirect;
                }
            }
        });
    });

    addEvent(findOne("a[role=button].chat-delete"), "click", () => {
        const selected = find("li.chat.selected");

        if (selected.length) {
            if (!confirm(gettext("are you sure to delete all selected conversations?"))) {
                return false;
            }

            deleteConversation(getPkSet(selected), findOne("ul.threads").getAttribute("data-mode")).then(response => {
                const data = response.data.message.deleteConversation;
                if (data) {
                    window.location = data.redirect;
                }
            });
        } else {
            notify(gettext("you need to select at least one conversation to delete"), "error");
        }
    });

    function archiveConversation (pkSet) {
        const query = `mutation($pkSet:[ID!]!){message{archiveConversation(pkSet:$pkSet){redirect}}}`;
        const variables = { pkSet };
        return gqlc({ query, variables });
    }

    addEvent(findOne("a[role=button].chat-archive"), "click", () => {
        const selected = find("li.chat.selected");

        if (selected.length) {
            if (!confirm(gettext("are you sure to archive all selected conversations?"))) {
                return false;
            }

            archiveConversation(getPkSet(selected)).then(response => {
                const data = response.data.message.archiveConversation;
                if (data) {
                    window.location = data.redirect;
                }
            });
        } else {
            notify(gettext("you need to select at least one conversation to archive"), "error");
        }
    });

    addEvents(find("a[role=button].chat-archive-individual"), "click", function () {
        if (!confirm(gettext("are you sure to archive?"))) {
            return false;
        }

        const chat = selectChat(this);

        archiveConversation(chat.getAttribute("data-id")).then(response => {
            const data = response.data.message.archiveConversation;
            if (data) {
                if (find("li.chat").length > 1) {
                    chat.remove();
                    notify(gettext("archived conversation"));
                } else {
                    window.location = data.redirect;
                }
            }
        });
    });

    function deleteImage (slug) {
        return gqlc({
            query: "mutation($slug:String!){image{delete(slug:$slug){feedback}}}",
            variables: { slug }
        });
    }

    addEvents(find("a[role=button].delete-image"), "click", function () {
        if (confirm(gettext("Are you sure?"))) {
            const img = this.closest(".image-detail");
            deleteImage(img.getAttribute("data-slug"));
            img.remove();
        }
    });

    Dropzone.options.userImageUpload = {
        addRemoveLinks: true,
        paramName: "file",
        maxFilesize: 2.5, // MB
        acceptedFiles: "image/*",
        maxFiles: 10,
        dictRemoveFileConfirmation: gettext("Are you sure?"),
        dictDefaultMessage: gettext("click or drop files here to upload"),
        dictRemoveFile: gettext("delete image"),
        dictFileTooBig: gettext("File is too big ({{filesize}}MB). Max filesize: {{maxFilesize}}MB."),
        dictMaxFilesExceeded: gettext("You can not upload any more files."),
        dictUploadCanceled: gettext("Upload canceled."),
        dictCancelUploadConfirmation: gettext("Are you sure?"),

        success (file, response) {
            insertAtCaret(findOne("#user_content_edit"), `(${pgettext("editor", "image")}: ${response.slug})`);
        },

        removedfile (file) {
            file.previewElement.remove();
            const text = findOne("#user_content_edit");
            const slug = JSON.parse(file.xhr.response).slug;
            text.value = text.value.replace(new RegExp(`\\(${pgettext("editor", "image")}: ${slug}\\)`, "g"), "");
            deleteImage(slug);
        }
    };

    addEvent(document, "click", event => {
        const self = event.target;
        if (self.matches(".entry a[data-img], .text-formatted a[data-img]")) {
            if (!self.hasAttribute("data-loaded")) {
                const p = self.parentNode;
                p.style.maxHeight = "none"; // Click "read more" button.
                const readMore = p.querySelector(".read_more");

                if (readMore) {
                    readMore.style.display = "none";
                }

                const url = self.getAttribute("data-img");
                const image = createTemplate(`<img src="${url}" alt="image" class="img-thumbnail img-fluid" draggable="false">`);
                const expander = createTemplate(`<a rel="ugc nofollow noopener" title="${gettext("open full image in new tab")}" href="${url}" target="_blank" class="ml-3 position-relative" style="top: 3px;"></a>`);

                self.after(expander);
                expander.after(image);
            } else {
                self.nextElementSibling.classList.toggle("d-none");
                self.nextElementSibling.nextElementSibling.classList.toggle("d-none");
            }
            self.setAttribute("data-loaded", "true");
        }
    });

    function draftEntry (content, pk = null, title = null) {
        return gqlc({
            query: "mutation($content:String!,$pk:ID,$title:String){entry{edit(content:$content,pk:$pk,title:$title){pk,content,feedback}}}",
            variables: { content, title, pk }
        }).then(response => {
            if (response.errors) {
                for (const error of response.errors) {
                    notify(error.message, "error");
                }
            } else {
                const btn = findOne("button.draft-async");
                btn.textContent = gettext("save changes");
                if (!btn.hasAttribute("data-pk")) {
                    // ^^ Only render delete button once.
                    btn.after(createTemplate(`<button type="button" class="btn btn-django-link fs-90 ml-3 draft-del">${gettext("delete")}</button>`));
                }
                window.onbeforeunload = null;
                notify(response.data.entry.edit.feedback, "info");
                return response;
            }
        });
    }

    addEvent(findOne("button.draft-async"), "click", function () {
        const title = this.getAttribute("data-title");
        const pk = this.getAttribute("data-pk");
        const content = findOne("#user_content_edit").value;

        if (!content.trim()) {
            notify(gettext("if only you could write down something"), "error");
            return;
        }

        if (pk) {
            draftEntry(content, pk).then(response => {
                if (response) {
                    findOne("p.pw-text").innerHTML = response.data.entry.edit.content;
                }
            });
            return; // Don't check title.
        }

        if (title) {
            draftEntry(content, null, title).then(response => {
                if (response) {
                    findOne(".user-content").prepend(createTemplate(`<section class="pw-area"><h2 class="h5 text-muted">${gettext("preview")}</h2><p class="text-formatted pw-text">${response.data.entry.edit.content}</p></section>`));
                    const pk = response.data.entry.edit.pk;
                    this.setAttribute("data-pk", pk);
                    findOne("#content-form").prepend(createTemplate(`<input type="hidden" name="pub_draft_pk" value="${pk}" />`));
                }
            });
        }
    });

    addEvent(document, "click", event => {
        if (event.target.matches("button.draft-del") && confirm(gettext("Are you sure?"))) {
            const btn = findOne("button.draft-async");
            entryAction("delete", btn.getAttribute("data-pk")).then(response => {
                findOne("section.pw-area").remove();
                findOne("#user_content_edit").value = "";
                findOne("[name=pub_draft_pk]").remove();
                btn.textContent = gettext("keep this as draft");
                btn.removeAttribute("data-pk");
                event.target.remove();
                notify(response.data.entry.delete.feedback, "info");
            });
        }
    });

    addEvent(findOne(".allowsave"), "keydown", event => {
        if (event.ctrlKey || event.metaKey) {
            if (String.fromCharCode(event.which).toLowerCase() === "s") {
                event.preventDefault();
                findOne("button.draft-async").dispatchEvent(new Event("click"));
            }
        }
    });
})();

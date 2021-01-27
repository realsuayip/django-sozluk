/* global gettext */

import { cookies, many, one, notify, gqlc, notSafe, Handler, Handle, updateQueryStringParameter } from "./utils"
import { userIsMobile } from "./mql"

function setExclusions (exclusions) {
    const cookieExclusions = JSON.parse(cookies.get("lfex") || "null")
    if (exclusions) {
        if (cookieExclusions) {
            exclusions.forEach(exclusion => {
                if (cookieExclusions.includes(exclusion)) {
                    exclusions = cookieExclusions.filter(item => item !== exclusion)
                } else {
                    cookieExclusions.push(exclusion)
                    exclusions = cookieExclusions
                }
            })
        }
        cookies.set("lfex", JSON.stringify(exclusions), { expires: 90 })
        return exclusions
    } else {
        return cookieExclusions
    }
}

class LeftFrame {
    constructor (slug, page = 1, year = null, searchKeys = null, refresh = false, tab = null, exclusions = null, extra = null) {
        this.slug = slug
        this.page = page
        this.year = year
        this.refresh = refresh
        this.searchKeys = searchKeys
        this.tab = tab
        this.exclusions = exclusions
        this.extra = extra

        this.setCookies()
        this.loadIndicator = one("#load_indicator")
    }

    setCookies () {
        cookies.set("lfac", this.slug)
        cookies.set("lfnp", this.page)

        if (this.tab) {
            cookies.set("lfat", this.tab)
        } else {
            this.tab = cookies.get("lfat") || null
        }

        if (this.extra) {
            cookies.set("lfea", this.extra)
        } else {
            this.extra = cookies.get("lfea") || null
        }

        if (this.slug === "today-in-history") {
            const cookieYear = cookies.get("lfsy")
            if (!this.year) {
                this.year = cookieYear || null
            } else {
                cookies.set("lfsy", this.year)
            }
        } else if (this.slug === "search") {
            const cookieSearchKeys = cookies.get("lfsp")
            if (!this.searchKeys) {
                this.searchKeys = cookieSearchKeys || null
            } else {
                cookies.set("lfsp", this.searchKeys)
            }
        } else if (this.slug === "popular") {
            this.exclusions = setExclusions(this.exclusions)
        }
    }

    call () {
        this.loadIndicator.style.display = "inline"
        const variables = {
            slug: this.slug,
            year: this.year,
            page: this.page,
            searchKeys: this.searchKeys,
            refresh: this.refresh,
            tab: this.tab,
            exclusions: this.exclusions,
            extra: this.extra
        }

        const query = `query($slug: String!,$year:Int,$page:Int,$searchKeys:String,$refresh:Boolean,$tab:String,
            $exclusions:[String],$extra:JSONString){topics(slug:$slug,year:$year,page:$page,searchKeys:$searchKeys,
            refresh:$refresh,tab:$tab,exclusions:$exclusions,extra:$extra){
                safename refreshCount year yearRange slugIdentifier parameters
                page { objectList { slug title count } paginator { pageRange numPages } number hasOtherPages hasNext }
                tabs{current available{name, safename}}
                exclusions{active, available{name, slug, description}}
            }}`

        gqlc({ query, variables }, true).then(response => {
            if (response.errors) {
                this.loadIndicator.style.display = "none"
                notify(gettext("something went wrong"), "error")
            } else {
                this.render(response.data.topics)
            }
        })
    }

    render (data) {
        one("#left-frame-nav").scroll({ top: 0, behavior: "smooth" })
        one("#current_category_name").textContent = data.safename
        this.renderRefreshButton(data.refreshCount)
        this.renderYearSelector(data.year, data.yearRange)
        this.renderPagination(data.page.hasOtherPages, data.page.paginator.pageRange, data.page.paginator.numPages, data.page.number, data.page.hasNext)
        this.renderTopicList(data.page.objectList, data.slugIdentifier, data.parameters)
        this.renderShowMoreButton(data.page.number, data.page.hasOtherPages)
        this.renderTabs(data.tabs)
        this.renderExclusions(data.exclusions)
        this.loadIndicator.style.display = "none"
    }

    renderRefreshButton (count) {
        const refreshButton = one("#refresh_bugun")
        if (count) {
            refreshButton.classList.remove("dj-hidden")
            one("span#new_content_count").textContent = `(${count})`
        } else {
            refreshButton.classList.add("dj-hidden")
        }
    }

    renderShowMoreButton (currentPage, isPaginated) {
        const showMoreButton = one("a#show_more")

        if (currentPage !== 1 || !isPaginated) {
            showMoreButton.classList.add("d-none")
        } else {
            showMoreButton.classList.remove("d-none")
        }
    }

    renderTabs (tabData) {
        const tabHolder = one("ul#left-frame-tabs")
        if (tabData) {
            tabHolder.innerHTML = ""

            tabData.available.forEach(tab => {
                tabHolder.innerHTML += `<li class="nav-item"><a role="button" tabindex="0" data-lf-slug="${this.slug}" data-tab="${tab.name}" class="nav-link${tabData.current === tab.name ? " active" : ""}">${tab.safename}</a></li>`
            })

            tabHolder.classList.remove("dj-hidden")
        } else {
            tabHolder.classList.add("dj-hidden")
        }
    }

    renderExclusions (exclusions) {
        const toggler = one("#popular_excluder")
        const categoryHolder = one("#exclusion-choices")
        const categoryList = categoryHolder.querySelector("ul.exclusion-choices")

        if (exclusions) {
            categoryList.innerHTML = ""
            toggler.classList.remove("dj-hidden")

            exclusions.available.forEach(category => {
                const isActive = exclusions.active.includes(category.slug)
                categoryList.innerHTML += `<li><a role="button" title="${category.description}" ${isActive ? `class="active"` : ""} tabindex="0" data-slug="${category.slug}">#${category.name}</a></li>`
            })

            if (exclusions.active.length) {
                toggler.classList.add("active")
            } else {
                toggler.classList.remove("active")
            }
        } else {
            toggler.classList.add("dj-hidden")
            categoryHolder.classList.add("dj-hidden")
        }
    }

    renderYearSelector (currentYear, yearRange) {
        const yearSelect = one("#year_select")
        yearSelect.innerHTML = ""

        if (this.slug === "today-in-history") {
            yearSelect.style.display = "block"
            yearRange.forEach(year => {
                yearSelect.innerHTML += `<option ${year === currentYear ? "selected" : ""} id="${year}">${year}</option>`
            })
        } else {
            yearSelect.style.display = "none"
        }
    }

    renderTopicList (objectList, slugIdentifier, parameters) {
        const topicList = one("ul#topic-list")
        if (objectList.length === 0) {
            topicList.innerHTML = `<small>${gettext("nothing here")}</small>`
        } else {
            topicList.innerHTML = ""
            const params = parameters || ""

            let topics = ""

            objectList.forEach(topic => {
                topics += `<li class="list-group-item"><a href="${slugIdentifier}${topic.slug}/${params}">${notSafe(topic.title)}<small class="total_entries">${topic.count && topic.count !== "0" ? topic.count : ""}</small></a></li>`
            })

            if (topics) {
                topicList.innerHTML = topics
            }
        }
    }

    renderPagination (isPaginated, pageRange, totalPages, currentPage, hasNext) {
    // Pagination related selectors
        const paginationWrapper = one("#lf_pagination_wrapper")
        const pageSelector = one("select#left_frame_paginator")
        const totalPagesButton = one("#lf_total_pages")
        const nextPageButton = one("#lf_navigate_after")

        // Render pagination
        if (isPaginated && currentPage !== 1) {
            // Render Page selector
            pageSelector.innerHTML = ""
            let options = ""

            pageRange.forEach(page => {
                options += `<option ${page === currentPage ? "selected" : ""} value="${page}">${page}</option>`
            })

            pageSelector.innerHTML += options
            totalPagesButton.textContent = totalPages
            nextPageButton.classList[hasNext ? "remove" : "add"]("d-none")
            paginationWrapper.classList.remove("dj-hidden")
        } else {
            paginationWrapper.classList.add("dj-hidden")
        }
    }

    static populate (slug, page = 1, ...args) {
        if (userIsMobile) {
            return
        }
        const leftFrame = new LeftFrame(slug, page, ...args)
        leftFrame.call()
    }

    static refreshPopulate () {
        LeftFrame.populate("today", 1, null, null, true)
    }
}

Handle("body", "click", event => {
    // Regular, slug-only
    const delegated = event.target.closest("[data-lf-slug]")

    if (delegated && !userIsMobile) {
        const slug = delegated.getAttribute("data-lf-slug")
        const tab = delegated.getAttribute("data-tab") || null
        const extra = delegated.getAttribute("data-lf-extra") || null
        LeftFrame.populate(slug, 1, null, null, false, tab, null, extra)

        if (delegated.classList.contains("dropdown-item")) {
            // Prevents dropdown collapsing, good for accessibility.
            event.stopPropagation()
        }
        event.preventDefault()
    }
})

Handle("#year_select", "change", function () {
    const selectedYear = this.value
    LeftFrame.populate("today-in-history", 1, selectedYear)
})

Handle("select#left_frame_paginator", "change", function () {
    LeftFrame.populate(cookies.get("lfac"), this.value)
})

const selector = one("select#left_frame_paginator")
const totalPagesElement = one("#lf_total_pages")
const changeEvent = new Event("change")

Handle(totalPagesElement, "click", function () {
    // Navigated to last page
    if (selector.value === this.textContent) {
        return
    }

    selector.value = this.textContent
    selector.dispatchEvent(changeEvent)
})

Handle("#lf_navigate_before", "click", () => {
    // Previous page
    const selected = parseInt(selector.value, 10)
    if (selected - 1 > 0) {
        selector.value = selected - 1
        selector.dispatchEvent(changeEvent)
    }
})

Handle("#lf_navigate_after", "click", () => {
    // Subsequent page
    const selected = parseInt(selector.value, 10)
    const max = parseInt(totalPagesElement.textContent, 10)
    if (selected + 1 <= max) {
        selector.value = selected + 1
        selector.dispatchEvent(changeEvent)
    }
})

Handle("a#show_more", "click", function () {
    // Show more button event
    const slug = cookies.get("lfac")

    if (slug) {
        LeftFrame.populate(slug, 2)
        one("#left-frame-nav").scroll(0, 0)
    }

    this.classList.add("d-none")
})

Handle("#refresh_bugun", "click", LeftFrame.refreshPopulate)

Handler(".exclusion-button", "click", function () {
    this.closest("div").parentNode.querySelector(".exclusion-settings").classList.toggle("dj-hidden")
})

Handle("#exclusion-choices", "click", event => {
    if (event.target.tagName === "A") {
        event.target.classList.toggle("active")
        LeftFrame.populate("popular", 1, null, null, null, null, [event.target.getAttribute("data-slug")])
    }
})

Handle("#exclusion-settings-mobile", "click", event => {
    if (event.target.tagName === "A") {
        setExclusions([event.target.getAttribute("data-slug")])
        window.location = location
    }
})

Handler("[data-lf-slug]", "click", function () {
    many("[data-lf-slug]").forEach(el => el.classList.remove("active"))
    many(`[data-lf-slug=${this.getAttribute("data-lf-slug")}]`).forEach(el => el.classList.add("active"))
})

Handle("select#mobile_year_changer", "change", function () {
    window.location = updateQueryStringParameter(location.href, "year", this.value)
})

Handle("#left-frame-nav", "scroll", function () {
    localStorage.setItem("where", this.scrollTop)
})

export { LeftFrame }

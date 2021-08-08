/* global interpolate, gettext, ngettext */

import { Handle, Handler, template, many, one, gqlc, notify, userIsAuthenticated } from "./utils"
import { showMessageDialog, showBlockDialog } from "./dialog"
import { isTouchDevice } from "./mql"

function entryAction (type, pk, redirect = false) {
    return gqlc({ query: `mutation{entry{${type}(pk:"${pk}"){feedback ${redirect ? "redirect" : ""}}}}` })
}

Handler("a.favorite[role='button']", "click", function () {
    const pk = this.closest(".entry-full").getAttribute("data-id")

    gqlc({ query: `mutation{entry{favorite(pk:"${pk}"){feedback count}}}` }).then(response => {
        const count = response.data.entry.favorite.count
        const countHolder = this.nextElementSibling

        this.classList.toggle("active")

        if (count === 0) {
            countHolder.textContent = ""
            countHolder.setAttribute("tabindex", "-1")
        } else {
            countHolder.textContent = count
            countHolder.setAttribute("tabindex", "0")
        }

        this.parentNode.querySelector("span.favorites-list").setAttribute("data-loaded", "false")
    })
})

Handler("a.fav-count[role='button']", "click", function () {
    const favoritesList = this.nextElementSibling

    if (favoritesList.getAttribute("data-loaded") === "true") {
        return
    }

    favoritesList.innerHTML = "<div class='px-3 py-1'><div class='spinning'><span style='font-size: 1.25em'>&orarr;</span></div></div>"

    const pk = this.closest(".entry-full").getAttribute("data-id")

    gqlc({ query: `{entry{favoriters(pk:${pk}){username slug isNovice}}}` }).then(response => {
        const allUsers = response.data.entry.favoriters
        const authors = allUsers.filter(user => user.isNovice === false)
        const novices = allUsers.filter(user => user.isNovice === true)

        favoritesList.innerHTML = ""
        favoritesList.setAttribute("data-loaded", "true")

        if (!allUsers.length) {
            favoritesList.innerHTML = `<span class='p-2'>${gettext("actually, nothing here.")}</span>`
            return
        }

        let favList = ""

        if (authors.length > 0) {
            authors.forEach(author => {
                favList += `<a class="author" href="/author/${author.slug}/">@${author.username}</a>`
            })

            favoritesList.innerHTML = favList
        }

        if (novices.length > 0) {
            const noviceString = interpolate(ngettext("... %(count)s novice", "... %(count)s novices", novices.length), { count: novices.length }, true)
            const noviceToggle = template(`<a role="button" tabindex="0">${noviceString}</a>`)
            const noviceList = template(`<span class="dj-hidden"></span>`)

            favoritesList.append(noviceToggle)
            noviceToggle.addEventListener("click", () => {
                noviceList.classList.toggle("dj-hidden")
            })

            favList = ""

            novices.forEach(novice => {
                favList += `<a class="novice" href="/author/${novice.slug}/">@${novice.username}</a>`
            })

            noviceList.innerHTML = favList
            favoritesList.append(noviceList)
        }
    })
})

Handler("a.twitter[role='button'], a.facebook[role='button']", "click", function () {
    const base = this.classList.contains("twitter") ? "https://twitter.com/intent/tweet?text=" : "https://www.facebook.com/sharer/sharer.php?u="
    const entry = this.closest(".entry-footer").querySelector(".meta .permalink").getAttribute("href")
    const windowReference = window.open()
    windowReference.opener = null
    windowReference.location = `${base}${window.location.origin}${entry}`
})

Handler(".entry-vote .vote", "click", function () {
    const type = this.classList.contains("upvote") ? "upvote" : "downvote"
    const entryId = this.closest(".entry-full").getAttribute("data-id")
    entryAction(type, entryId).then(response => {
        const feedback = response.data.entry[type].feedback
        if (feedback == null) {
            const sibling = this.nextElementSibling || this.previousElementSibling
            sibling.classList.remove("active")
            this.classList.toggle("active")
        } else {
            notify(feedback, "error", 4000)
        }
    })
})

Handler(".comment-vote .vote", "click", function () {
    const action = this.classList.contains("upvote") ? "upvote" : "downvote"
    const pk = this.parentNode.getAttribute("data-id")
    gqlc({
        query: "mutation($pk:ID!,$action:String!){entry{votecomment(pk:$pk,action:$action){count}}}",
        variables: { pk, action }
    }).then(response => {
        if (response.errors) {
            response.errors.forEach(error => {
                notify(error.message, "error")
            })
            return
        }

        this.parentNode.querySelectorAll(".vote").forEach(el => {
            el !== this && el.classList.remove("active")
        })

        this.classList.toggle("active")
        this.parentNode.querySelector(".rating").textContent = response.data.entry.votecomment.count
    })
})

Handler(".entry-actions", "click", function (event) {
    const target = event.target.closest(".dropdown-item")
    const [action] = ["message", "pin", "block", "delete", "copy", "share"].filter(action => target.classList.contains(action))

    switch (action) {
        case "message" : {
            const recipient = this.parentNode.querySelector(".username").textContent
            const entryInQuestion = this.closest(".entry-full").getAttribute("data-id")
            showMessageDialog(recipient, `\`#${entryInQuestion}\`:\n`, this.previousElementSibling)
            break
        }

        case "pin" : {
            const entryID = this.closest(".entry-full").getAttribute("data-id")
            const body = one("body")
            entryAction("pin", entryID).then(response => {
                many("a.action[role='button']").forEach(action => {
                    action.classList.remove("loaded")
                })

                if (body.getAttribute("data-pin") === entryID) {
                    body.removeAttribute("data-pin")
                } else {
                    body.setAttribute("data-pin", entryID)
                }

                notify(response.data.entry.pin.feedback)
            })
            break
        }

        case "block" : {
            const target = this.parentNode.querySelector(".username").textContent
            const profile = one(".profile-username")
            const re = profile && profile.textContent === target
            showBlockDialog(target, re, this.previousElementSibling)
            break
        }

        case "delete" : {
            if (confirm(gettext("are you sure to delete?"))) {
                const entry = this.closest(".entry-full")
                const redirect = many("ul.topic-view-entries li.entry-full").length === 1

                entryAction("delete", entry.getAttribute("data-id"), redirect).then(response => {
                    const data = response.data.entry.delete
                    if (redirect) {
                        window.location = data.redirect
                    } else {
                        entry.remove()
                        notify(data.feedback)
                    }
                })
            }
            break
        }

        case "copy": {
            const link = this.parentNode.querySelector(".permalink").href
            navigator.clipboard.writeText(link).then(() => {
                notify(gettext("link copied to clipboard."), "info")
            })
            break
        }

        case "share": {
            const url = this.parentNode.querySelector(".permalink").href
            navigator.share({ url })
            break
        }
    }
})

// Render actions
const icon = (name, a = 16, b = 16) => `<svg fill="currentColor" viewBox="0 0 ${a} ${b}"><use href="#${name}"></use></svg>`

Handler(".entry-full a.action[role='button']", "click", function () {
    if (this.classList.contains("loaded")) {
        return
    }

    const entry = this.closest(".entry-full")
    const entryID = entry.getAttribute("data-id")
    const topicTitle = encodeURIComponent(entry.closest("[data-topic]").getAttribute("data-topic"))
    const actions = this.parentNode.querySelector(".entry-actions")
    const pinLabel = entryID === one("body").getAttribute("data-pin") ? gettext("unpin from profile") : gettext("pin to profile")

    actions.innerHTML = ""
    let menuItems = ""

    if (userIsAuthenticated) {
        if (entry.classList.contains("commentable")) {
            menuItems += `<a target="_blank" href="/entry/${entryID}/comment/" class="dropdown-item">${icon("comment")}${gettext("comment")}</a>`
        }
        if (entry.classList.contains("owner")) {
            menuItems += `<a role="button" tabindex="0" class="dropdown-item pin">${icon("pin")}${pinLabel}</a>`
            menuItems += `<a role="button" tabindex="0" class="dropdown-item delete">${icon("trash")}${gettext("delete")}</a>`
            menuItems += `<a href="/entry/update/${entryID}/" class="dropdown-item">${icon("edit", 44, 44)}${gettext("edit")}</a>`
        } else {
            if (!entry.classList.contains("private")) {
                menuItems += `<a role="button" tabindex="0" class="dropdown-item message">${icon("message")}${gettext("message")}</a>`
                menuItems += `<a role="button" tabindex="0" class="dropdown-item block">${icon("block")}${gettext("block")}</a>`
            }
        }
    }

    if (isTouchDevice && !navigator.share) {
        menuItems += `<a role="button" tabindex="0" class="dropdown-item copy">${icon("link")}${gettext("copy link")}</a>`
    }

    if (navigator.share) {
        menuItems += `<a role="button" tabindex="0" class="dropdown-item share">${icon("share")}${gettext("share")}</a>`
    }

    menuItems += `<a class="dropdown-item" href="/contact/?referrer_entry=${entryID}&referrer_topic=${topicTitle}">${icon("flag")}${gettext("report")}</a>`

    actions.innerHTML = menuItems
    this.classList.add("loaded")
})

// External entry actions

Handle(".delete-entry-redirect", "click", function () {
    if (confirm(gettext("are you sure to delete?"))) {
        entryAction("delete", this.getAttribute("data-target-entry"), true).then(response => {
            window.location = response.data.entry.delete.redirect
        })
    }
})

Handle(".pin-sync", "click", function () {
    entryAction("pin", this.getAttribute("data-id")).then(response => {
        notify(response.data.entry.pin.feedback)
        window.location = location
    })
})

// Read more functionality

function truncateEntryText () {
    const overflown = el => el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth
    many("article.entry p").forEach(el => {
        if (overflown(el)) {
            const readMore = template(`<div role="button" tabindex="0" class="read_more">${gettext("continue reading")}</div>`)
            el.parentNode.append(readMore)
            Handle(readMore, "click", function () {
                el.style.maxHeight = "none"
                this.style.display = "none"
            })
        }
    })
}

window.onload = () => {
    if (one("body").classList.contains("has-entries")) {
        truncateEntryText()
    }
}

// Async draft

function draftEntry (content, pk = null, title = null) {
    return gqlc({
        query: "mutation($content:String!,$pk:ID,$title:String){entry{edit(content:$content,pk:$pk,title:$title){pk,content,feedback}}}",
        variables: { content, title, pk }
    }).then(response => {
        if (response.errors) {
            response.errors.forEach(error => {
                notify(error.message, "error")
            })
        } else {
            const btn = one("button.draft-async")
            btn.textContent = gettext("save changes")
            if (!btn.hasAttribute("data-pk")) {
                // ^^ Only render delete button once.
                btn.after(template(`<button type="button" class="btn btn-django-link fs-90 ml-3 draft-del">${gettext("delete")}</button>`))
            }
            window.onbeforeunload = null
            notify(response.data.entry.edit.feedback, "info")
            return response
        }
    })
}

const titleInput = one("#user_title_edit")

Handle("button.draft-async", "click", function () {
    const title = this.getAttribute("data-title") || (titleInput && titleInput.value)
    const pk = this.getAttribute("data-pk")
    const content = one("#user_content_edit").value

    if (!content.trim() || ((title !== null) && !title.trim())) {
        // Check if content is not empty, also check title (if provided).
        notify(gettext("if only you could write down something"), "error")
        return
    }

    if (pk) {
        draftEntry(content, pk).then(response => {
            if (response) {
                one("p.pw-text").innerHTML = response.data.entry.edit.content
            }
        })
        return // Don't check title.
    }

    if (title) {
        draftEntry(content, null, title).then(response => {
            if (response) {
                one(".user-content").prepend(template(`<section class="pw-area"><h2 class="h5 text-muted">${gettext("preview")}</h2><p class="text-formatted pw-text">${response.data.entry.edit.content}</p></section>`))
                const pk = response.data.entry.edit.pk
                this.setAttribute("data-pk", pk)
                one("#content-form").prepend(template(`<input type="hidden" name="pub_draft_pk" value="${pk}" />`))
                if (titleInput) {
                    titleInput.disabled = true
                    titleInput.classList.add("highlighted")
                }
            }
        })
    }
})

Handle(document, "click", event => {
    if (event.target.matches("button.draft-del") && confirm(gettext("Are you sure?"))) {
        const btn = one("button.draft-async")
        entryAction("delete", btn.getAttribute("data-pk")).then(response => {
            one("section.pw-area").remove()
            one("#user_content_edit").value = ""
            one("[name=pub_draft_pk]").remove()
            btn.textContent = gettext("keep this as draft")
            btn.removeAttribute("data-pk")
            event.target.remove()

            if (titleInput) {
                titleInput.disabled = false
                titleInput.classList.remove("highlighted")
            }

            notify(response.data.entry.delete.feedback, "info")
        })
    }
})

Handle(".allowsave", "keydown", event => {
    if (event.ctrlKey || event.metaKey) {
        if (String.fromCharCode(event.which).toLowerCase() === "s") {
            event.preventDefault()
            one("button.draft-async").dispatchEvent(new Event("click"))
        }
    }
})

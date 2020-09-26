/* global gettext */

import {
    Handle,
    Handler,
    template,
    one,
    gqlc,
    isValidText,
    notify,
    toggleText
} from "./utils"

function topicAction (type, pk) {
    return gqlc({ query: `mutation{topic{${type}(pk:"${pk}"){feedback}}}` }).then(response => {
        notify(response.data.topic[type].feedback)
    })
}

Handle(".follow-topic-trigger", "click", function () {
    toggleText(this, gettext("unfollow"), gettext("follow"))
    topicAction("follow", this.getAttribute("data-topic-id"))
})

// Category suggestion

Handler(".suggestion-vote button", "click", function () {
    const direction = this.classList.contains("up") ? 1 : -1
    const topic = this.parentNode.getAttribute("data-topic")
    const category = this.parentNode.getAttribute("data-category")

    gqlc({
        query: "mutation($category:String!,$topic:String!,$direction:Int!){category{suggest(category:$category,topic:$topic,direction:$direction){feedback}}}",
        variables: { category, topic, direction }
    }).then(response => {
        if (response.errors) {
            response.errors.forEach(error => {
                notify(error.message, "error")
            })
        } else {
            this.classList.toggle("btn-django-link")
            const sibling = this.nextElementSibling || this.previousElementSibling
            sibling.classList.remove("btn-django-link")
        }
    })
})

// Wish

function wishTopic (title, hint = null) {
    const query = `mutation wish($title:String!,$hint:String){topic{wish(title:$title,hint:$hint){feedback hint}}}`
    const variables = { title, hint }
    return gqlc({ query, variables })
}

Handle("a.wish-prepare[role=button]", "click", function () {
    this.parentNode.querySelectorAll(":not(.wish-purge):not(.wish-prepare)").forEach(el => {
        el.classList.toggle("dj-hidden")
    })
    toggleText(this, gettext("someone should populate this"), gettext("nevermind"))
})

Handle("a.wish-send[role=button]", "click", function () {
    const textarea = this.parentNode.querySelector("textarea")
    const hint = textarea.value

    if (hint && !isValidText(hint)) {
        notify(gettext("this content includes forbidden characters."), "error")
        return
    }

    const title = this.parentNode.getAttribute("data-topic")
    wishTopic(title, hint).then(response => {
        if (response.errors) {
            response.errors.forEach(error => {
                notify(error.message, "error")
            })
            return
        }
        textarea.value = ""
        Array.from(this.parentNode.children).forEach(child => {
            child.classList.toggle("dj-hidden")
        })
        const hintFormatted = response.data.topic.wish.hint
        const wishList = one("ul#wish-list")
        wishList.classList.remove("dj-hidden")
        wishList.prepend(template(`<li class="list-group-item owner">${gettext("you just wished for this topic.")} ${hintFormatted ? `${gettext("your hint:")} <p class="m-0 text-formatted"><i>${hintFormatted}</i></p>` : ""}</li>`))
        window.scrollTo({ top: 0, behavior: "smooth" })
        notify(response.data.topic.wish.feedback)
    })
})

Handle("a.wish-purge[role=button]", "click", function () {
    const title = this.parentNode.getAttribute("data-topic")
    if (confirm(gettext("are you sure to delete?"))) {
        wishTopic(title).then(response => {
            this.classList.toggle("dj-hidden")
            const wishList = one("ul#wish-list")
            const popButton = this.parentNode.querySelector(".wish-prepare")

            popButton.textContent = gettext("someone should populate this")
            popButton.classList.toggle("dj-hidden")
            wishList.querySelector("li.owner").remove()

            if (!wishList.children.length) {
                wishList.classList.add("dj-hidden")
            }

            notify(response.data.topic.wish.feedback)
        })
    }
})

Handle(".snap-user-content", "click", () => {
    one("#user_content_edit").focus()
})

const topicView = one(".topic-view-entries")
const pagination = one(".pagination")

if (topicView && pagination) {
    const paginationClone = pagination.cloneNode(true)
    paginationClone.style.justifyContent = "flex-end"
    paginationClone.classList.add("mt-2")
    topicView.after(paginationClone)
}

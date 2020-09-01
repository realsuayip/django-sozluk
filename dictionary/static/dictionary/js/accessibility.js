/* global gettext */

import { Handle, Handler, isValidText, notify } from "./utils"

Handle("body", "keypress", event => {
    if (event.target.matches("[role=button], .key-clickable") && (event.key === " " || event.key === "Enter")) {
        event.preventDefault()
        event.target.dispatchEvent(new Event("click", { bubbles: true }))
    }
})

Handle(".content-skipper", "click", function () {
    location.replace(this.getAttribute("data-href"))
})

Handler("input.is-invalid", "input", function () {
    this.classList.remove("is-invalid")
})

Handler("textarea.expandable", "focus", function () {
    this.style.height = `${this.offsetHeight + 150}px`
    Handle(this, "transitionend", () => {
        this.style.transition = "none"
    })
}, { once: true })

Handler("textarea#user_content_edit, textarea#message-body", "input", function () {
    window.onbeforeunload = () => this.value || null
})

Handler("form", "submit", function (event) {
    window.onbeforeunload = null

    if (this.id === "header_search_form" && !new FormData(this).get("q").trim()) {
        event.preventDefault()
        window.location = "/threads/search/"
    }

    const userInput = this.querySelector("#user_content_edit")

    if (userInput && userInput.value) {
        if (!isValidText(userInput.value)) {
            notify(gettext("this content includes forbidden characters."), "error")
            window.onbeforeunload = () => true
            event.preventDefault()
            return false
        }
    }
})

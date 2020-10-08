import { Handle, Handler, template, updateQueryStringParameter } from "./utils"
import { isTouchDevice } from "./mql"

Handle("body", "change", event => {
    if (event.target.matches("select.page-selector")) {
        window.location = updateQueryStringParameter(location.href, "page", event.target.value)
    }
})

Handle("body", isTouchDevice ? "touchstart" : "focusin", event => {
    // Load pages for paginator select
    const select = event.target
    if (select.matches("select.page-selector") && !select.hasAttribute("data-loaded")) {
        const max = parseInt(select.getAttribute("data-max"), 10)
        const current = parseInt(select.value, 10)
        select.firstElementChild.remove()

        for (let i = 1; i <= max; i++) {
            const option = template(`<option ${i === current ? "selected" : ""}>${i}</option>`)
            select.append(option)
        }

        select.setAttribute("data-loaded", "")
    }
})

Handle("form.search_mobile, form.reporting-form", "submit", function () {
    Array.from(this.querySelectorAll("input")).filter(input => {
        if (input.type === "checkbox" && !input.checked) {
            return true
        }
        return input.value === ""
    }).forEach(input => {
        input.disabled = true
    })
    return false
})

Handler("[data-toggle=collapse]", "click", function () {
    this.closest("div").parentNode.querySelector(".collapse").classList.toggle("show")
    if (this.getAttribute("aria-expanded") === "false") {
        this.setAttribute("aria-expanded", "true")
    } else {
        this.setAttribute("aria-expanded", "false")
    }
})

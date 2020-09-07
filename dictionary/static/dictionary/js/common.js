import { Handle, Handler, updateQueryStringParameter } from "./utils"

Handle("body", "change", event => {
    if (event.target.matches("select.page-selector")) {
        window.location = updateQueryStringParameter(location.href, "page", event.target.value)
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

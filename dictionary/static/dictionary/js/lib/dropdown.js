import { Handle, Handler, many, one, createPopper } from "../utils"

const liveDropdowns = () => Array.from(many("[data-toggle=dropdown]")).filter(e => e._dropdownInstance && e._dropdownInstance.popper)

class Dropdown {
    constructor (button) {
        this.button = button
        this.menuElement = button.parentNode.querySelector(".dropdown-menu")
        this.popper = null
    }

    create () {
        const placement = this.menuElement.getAttribute("data-orientation") || "bottom-end"
        liveDropdowns().forEach(e => e._dropdownInstance.destroy())

        return createPopper(this.button, this.menuElement, {
            placement,
            modifiers: [
                {
                    name: "offset",
                    options: {
                        offset: [0, 1]
                    }
                }
            ]
        })
    }

    toggle () {
        if (this.menuElement.style.display === "block") {
            this.destroy()
            return
        }

        if (!this.popper) {
            this.popper = this.create()
        }

        this.menuElement.style.display = "block"
        this.button.setAttribute("aria-expanded", "true")
    }

    destroy () {
        this.menuElement.style.display = "none"
        this.button.setAttribute("aria-expanded", "false")

        if (this.popper) {
            this.popper.destroy()
            this.popper = null
        }
    }
}

function getActiveDropdown () {
    const [element] = liveDropdowns()
    return element ? element._dropdownInstance : null
}

Handler("[data-toggle=dropdown]", "click", function () {
    if (!this._dropdownInstance) {
        this._dropdownInstance = new Dropdown(this)
    }
    this._dropdownInstance.toggle()
})

Handle(document, "keydown", event => {
    if (event.key === "Escape") {
        const dropdown = getActiveDropdown()
        if (dropdown) {
            dropdown.destroy()
        } else {
            const modal = one(".modal.show")
            if (modal) {
                modal._modalInstance.hide()
            }
        }
    }
})

Handle(document, "click", event => {
    const dropdown = getActiveDropdown()

    if (dropdown) {
        const collapse = dropdown.menuElement.classList.contains("no-collapse") && dropdown.menuElement === event.target.closest(".dropdown-menu")
        if (event.target.classList.contains("dropdown-close") || (dropdown.button !== event.target.closest("[data-toggle=dropdown]") && !collapse)) {
            dropdown.destroy()
        }
    }
})

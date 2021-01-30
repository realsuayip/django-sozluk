import { Handle, Handler, one, createPopper, sleep } from "../utils"

const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

function getNextFocusableElement (element) {
    if (!element.nextElementSibling) {
        return null
    }

    if (element.nextElementSibling.matches(focusableSelector)) {
        return element.nextElementSibling
    }

    return getNextFocusableElement(element.nextElementSibling)
}

function getPreviousFocusableElement (element) {
    if (!element.previousElementSibling) {
        return null
    }

    if (element.previousElementSibling.matches(focusableSelector)) {
        return element.previousElementSibling
    }

    return getPreviousFocusableElement(element.previousElementSibling)
}

let liveDropdown = null

class Dropdown {
    constructor (button) {
        this.button = button
        this.menuElement = button.parentNode.querySelector(".dropdown-menu")
        this.popper = null

        this.menuElement.addEventListener("keydown", event => {
            if (!["ArrowUp", "ArrowDown"].includes(event.key) || this.menuElement.classList.contains("no-arrows")) {
                return
            }

            event.preventDefault()

            switch (event.key) {
                case "ArrowDown": {
                    const next = getNextFocusableElement(event.target)
                    if (next) {
                        next.focus()
                    } else {
                        // Return focus to top
                        this.menuElement.querySelector(focusableSelector).focus()
                    }
                    break
                }

                case "ArrowUp": {
                    const previous = getPreviousFocusableElement(event.target)
                    if (previous) {
                        previous.focus()
                    } else {
                        // Return focus to bottom
                        const items = this.menuElement.querySelectorAll(focusableSelector)
                        items[items.length - 1].focus()
                    }
                    break
                }
            }
        })
    }

    create () {
        const placement = this.menuElement.getAttribute("data-orientation") || "bottom-end"
        liveDropdown && liveDropdown.destroy()
        liveDropdown = this

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

    async toggle () {
        // To make dynamic dropdowns work (e.g., entry actions)
        // Normally, we should use popper.update() but in Chrome/Edge the layout shift
        // is preserved in (fixed) header for some reason?
        await sleep(0)

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
            liveDropdown = null
        }
    }
}

Handler("[data-toggle=dropdown]", "click", function () {
    if (!this._dropdownInstance) {
        this._dropdownInstance = new Dropdown(this)
    }
    this._dropdownInstance.toggle()
})

Handler("[data-toggle=dropdown]", "keydown", function (event) {
    if (event.key === "ArrowDown") {
        // Focus to the first focusable element if the dropdown is already open.
        event.preventDefault()
        if (this._dropdownInstance && this._dropdownInstance.popper) {
            const firstFocusableElement = this._dropdownInstance.menuElement.querySelector(focusableSelector)
            firstFocusableElement && firstFocusableElement.focus()
            return
        }
        // Show dropdown menu when users use arrow down while focusing on button.
        this.dispatchEvent(new Event("click"))
    }
})

let lastClickedElement

Handle(document, "mousedown", event => {
    lastClickedElement = event.target
})

Handle(document, "mouseup", () => {
    lastClickedElement = null
})

Handler("[data-toggle=dropdown]", "blur", function (event) {
    // Dropdown BUTTON lost focus, destroy the dropdown if the newly focused (or clicked) element is not a child of the menu.
    const dropdown = this._dropdownInstance

    if (!dropdown) {
        return
    }

    const clickBlur = lastClickedElement && lastClickedElement.closest(".dropdown-menu") === dropdown.menuElement
    const focusBlur = event.relatedTarget && event.relatedTarget.closest(".dropdown-menu") === dropdown.menuElement

    if (focusBlur || clickBlur) {
        return
    }

    dropdown.destroy()
})

Handle(document, "focusin", event => {
    // Dropdown MENU ELEMENT lost focus.
    if (event.target.matches("[data-toggle=dropdown]")) {
        return
    }

    if (liveDropdown && !event.target.closest(".dropdown-menu")) {
        liveDropdown.destroy()
    }
})

Handle(document, "keydown", event => {
    if (event.key === "Escape") {
        if (liveDropdown) {
            liveDropdown.destroy()
        } else {
            const modal = one(".modal.show")
            if (modal) {
                modal._modalInstance.hide()
            }
        }
    }
})

Handle(document, "click", event => {
    const dropdown = liveDropdown

    if (dropdown) {
        const collapse = dropdown.menuElement.classList.contains("no-collapse") && dropdown.menuElement === event.target.closest(".dropdown-menu")
        if (event.target.classList.contains("dropdown-close") || (dropdown.button !== event.target.closest("[data-toggle=dropdown]") && !collapse)) {
            dropdown.destroy()
        }
    }
})

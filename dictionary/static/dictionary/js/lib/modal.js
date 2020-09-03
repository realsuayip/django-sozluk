import { many } from "../utils"

class Modal {
    constructor (modal) {
        this.modal = modal
        this.showing = false
        this.lead = modal.querySelector(".lead")

        modal.addEventListener("click", event => {
            if (!event.target.closest(".modal-content") || event.target.closest("[data-dismiss=modal]")) {
                this.hide()
            }
        })

        // https://uxdesign.cc/how-to-trap-focus-inside-modal-to-make-it-ada-compliant-6a50f9a70700
        const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        const focusableContent = modal.querySelectorAll(focusableElements)
        const firstFocusableElement = focusableContent[0]
        const lastFocusableElement = focusableContent[focusableContent.length - 1]

        modal.addEventListener("keydown", event => {
            if (event.key !== "Tab") {
                return
            }

            if (event.shiftKey) {
                if (document.activeElement === firstFocusableElement) {
                    lastFocusableElement.focus()
                    event.preventDefault()
                }
            } else {
                if (document.activeElement === lastFocusableElement) {
                    firstFocusableElement.focus()
                    event.preventDefault()
                }
            }
        })
    }

    show (returnTo) {
        this.returnTo = returnTo
        this.showing = true
        this.modal.removeAttribute("aria-hidden")
        this.modal.classList.add("showing")
        this.modal.style.display = "block"
        setTimeout(() => {
            this.modal.classList.add("show")
            this.lead.focus()
        }, 0)
    }

    hide () {
        if (!this.showing) {
            return false
        }

        const _modal = this.modal
        _modal.classList.remove("show")

        new Promise(resolve => {
            _modal.addEventListener("transitionend", function _transitionend (event) {
                if (event.target === _modal) {
                    resolve(_transitionend)
                }
            })
        }).then(_transitionend => {
            _modal.removeEventListener("transitionend", _transitionend)
            _modal.style.display = "none"
            _modal.classList.remove("showing")
            _modal.setAttribute("aria-hidden", "true")
            this.returnTo && this.returnTo.focus()
        })
    }
}

many(".modal[role=dialog]").forEach(modal => {
    modal._modalInstance = new Modal(modal)
})

/* global Popper */

"use strict";
(function () {
    const find = document.querySelectorAll.bind(document);
    const findOne = document.querySelector.bind(document);

    Element.prototype.on = Element.prototype.addEventListener;
    Document.prototype.on = Document.prototype.addEventListener;

    Element.prototype.hasClass = function (className) {
        return this.classList.contains(className);
    };

    const liveDropdowns = () => Array.from(find("[data-toggle=dropdown]")).filter(e => e._dropdownInstance && e._dropdownInstance.popper);

    class Dropdown {
        constructor (button) {
            this.button = button;
            this.menuElement = button.parentNode.querySelector(".dropdown-menu");
            this.popper = null;
        }

        create () {
            const placement = this.menuElement.getAttribute("data-orientation") || "bottom-end";
            liveDropdowns().forEach(e => e._dropdownInstance.destroy());

            return Popper.createPopper(this.button, this.menuElement, {
                placement,
                modifiers: [
                    {
                        name: "offset",
                        options: {
                            offset: [0, 1]
                        }
                    }
                ]
            });
        }

        toggle () {
            if (this.menuElement.style.display === "block") {
                this.destroy();
                return;
            }

            if (!this.popper) {
                this.popper = this.create();
            }

            this.menuElement.style.display = "block";
            this.button.setAttribute("aria-expanded", "true");
        }

        destroy () {
            this.menuElement.style.display = "none";
            this.button.setAttribute("aria-expanded", "false");

            if (this.popper) {
                this.popper.destroy();
                this.popper = null;
            }
        }
    }

    function getActiveDropdown () {
        const [element] = liveDropdowns();
        return element ? element._dropdownInstance : null;
    }

    document.on("DOMContentLoaded", () => {
        find("[data-toggle=dropdown]").forEach(button => {
            button.on("click", () => {
                if (!button._dropdownInstance) {
                    button._dropdownInstance = new Dropdown(button);
                }
                button._dropdownInstance.toggle();
            });
        });
    });

    document.on("keydown", event => {
        if (event.key === "Escape") {
            const dropdown = getActiveDropdown();
            if (dropdown) {
                dropdown.destroy();
            } else {
                const modal = findOne(".modal.show");
                if (modal) {
                    modal._modalInstance.hide();
                }
            }
        }
    });

    document.on("click", event => {
        const dropdown = getActiveDropdown();

        if (dropdown) {
            const collapse = dropdown.menuElement.hasClass("no-collapse") && dropdown.menuElement === event.target.closest(".dropdown-menu");
            if (event.target.classList.contains("dropdown-close") ||
                    (dropdown.button !== event.target.closest("[data-toggle=dropdown]") && !collapse)) {
                dropdown.destroy();
            }
        }
    }
    );

    class Modal {
        constructor (modal) {
            this.modal = modal;
            this.showing = false;
            this.lead = modal.querySelector(".lead");

            modal.on("click", event => {
                if (!event.target.closest(".modal-content") || event.target.closest("[data-dismiss=modal]")) {
                    this.hide();
                }
            });

            // https://uxdesign.cc/how-to-trap-focus-inside-modal-to-make-it-ada-compliant-6a50f9a70700
            const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
            const focusableContent = modal.querySelectorAll(focusableElements);
            const firstFocusableElement = focusableContent[0];
            const lastFocusableElement = focusableContent[focusableContent.length - 1];

            modal.addEventListener("keydown", event => {
                if (event.key !== "Tab") {
                    return;
                }

                if (event.shiftKey) {
                    if (document.activeElement === firstFocusableElement) {
                        lastFocusableElement.focus();
                        event.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastFocusableElement) {
                        firstFocusableElement.focus();
                        event.preventDefault();
                    }
                }
            });
        }

        show () {
            this.showing = true;
            this.modal.removeAttribute("aria-hidden");
            this.modal.classList.add("showing");
            this.modal.style.display = "block";
            setTimeout(() => {
                this.modal.classList.add("show");
                this.lead.focus();
            }, 0);
        }

        hide () {
            if (!this.showing) {
                return false;
            }

            const _modal = this.modal;
            _modal.classList.remove("show");

            new Promise(resolve => {
                _modal.on("transitionend", function _transitionend (event) {
                    if (event.target === _modal) {
                        resolve(_transitionend);
                    }
                });
            }).then(_transitionend => {
                _modal.removeEventListener("transitionend", _transitionend);
                _modal.style.display = "none";
                _modal.classList.remove("showing");
                _modal.setAttribute("aria-hidden", "true");
            });
        }
    }

    find(".modal[role=dialog]").forEach(modal => {
        modal._modalInstance = new Modal(modal);
    });

    find("[data-toggle=collapse]").forEach(collapse => {
        collapse.on("click", () => {
            collapse.closest("div").parentNode.querySelector(".collapse").classList.toggle("show");
            if (collapse.getAttribute("aria-expanded") === "false") {
                collapse.setAttribute("aria-expanded", "true");
            } else {
                collapse.setAttribute("aria-expanded", "false");
            }
        });
    });
})();

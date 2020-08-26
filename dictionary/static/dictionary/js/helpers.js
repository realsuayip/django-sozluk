/* global Popper gettext Cookies */
"use strict";

const lang = document.documentElement.lang;

const entityMap = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
    "/": "&#x2F;",
    "`": "&#x60;",
    "=": "&#x3D;"
};

function notSafe (string) {
    return String(string).replace(/[&<>"'`=/]/g, function (s) {
        return entityMap[s];
    });
}

function createTemplate (html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim();
    return template.content.firstChild;
}

function sleep (ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

let toastQueue = 0;

async function notify (message, level = "default", initialDelay = 1800, persistent = false) {
    const toastHolder = document.querySelector(".toast-holder");
    const delay = initialDelay + (toastQueue * 1000);
    const toastTemplate = `
        <div role="alert" aria-live="assertive" aria-atomic="true" class="toast fade showing">
            <div class="toast-body ${level}">
                <div class="toast-content">
                    <span>${message}</span>
                    ${persistent ? `<button type="button" class="ml-2 close" data-dismiss="toast" aria-label="${gettext("Close")}"><span aria-hidden="true">&times;</span></button>` : ""}
                </div>
            </div>
        </div>`;
    const toast = createTemplate(toastTemplate);
    toastHolder.prepend(toast);

    if (persistent) {
        toast.addEventListener("click", async event => {
            if (event.target.closest("[data-dismiss=toast]")) {
                toast.classList.remove("show");
                await sleep(100);
                toast.remove();
            }
        });
    }

    await sleep(0);
    toast.classList.add("show");

    if (!persistent) {
        toastQueue += 1;
        await sleep(delay);
        toast.classList.remove("show");
        toastQueue -= 1;
        await sleep(100);
        toast.remove();
    }
}

function gqlc (data, failSilently = false, failMessage = gettext("something went wrong")) {
    const headers = new Headers({
        "Content-Type": "application/json",
        "X-CSRFToken": Cookies.get("csrftoken")
    });

    const options = {
        method: "POST",
        headers,
        mode: "same-origin",
        body: JSON.stringify(data)
    };

    const errorHandler = () => {
        if (!failSilently) {
            notify(failMessage, "error");
        }
        return { errors: [failMessage] };
    };

    return fetch("/graphql/", options).then(response => {
        if (response.ok) {
            return response.json();
        }
        return errorHandler();
    }).catch(() => {
        return errorHandler();
    });
}

const find = document.querySelectorAll.bind(document);
const findOne = document.querySelector.bind(document);

(function () {
    // eslint-disable-next-line no-extend-native
    String.prototype.replaceAll = function (pattern, replacement) {
        return this.replace(new RegExp(pattern.replace(/[.*+\-?^${}()|[\]\\]/g, "\\$&"), "g"), replacement);
    };

    class AutoComplete {
        constructor (options) {
            this.input = options.input;
            this.lookup = options.lookup; // Takes name, returns a Promise that resolves into list of {name, value}s.
            this.onSelect = options.onSelect; // Takes value.

            this.popper = null;
            this.selected = null;
            this.showing = false;

            const templateID = `id_${this.input.id}`;
            this.template = createTemplate(`<ul role="listbox" class="autocomplete" id="${templateID}"></ul>`);
            this.input.parentNode.append(this.template);

            this.input.setAttribute("role", "combobox");
            this.input.setAttribute("aria-owns", templateID);
            this.input.setAttribute("aria-autocomplete", "list");
            this.input.setAttribute("aria-expanded", "false");

            this.input.addEventListener("input", () => {
                const name = this.input.value.toLocaleLowerCase(lang).trim();
                this.selected = null;

                if (name) {
                    this.suggest(name);
                } else {
                    if (this.showing) {
                        this.destroy();
                    }
                }
            });

            this.input.addEventListener("focusout", () => {
                setTimeout(() => {
                    this.destroy();
                }, 200);
            });

            this.input.addEventListener("keydown", event => {
                if (!["ArrowUp", "ArrowDown", "Escape", "Enter", "Tab"].includes(event.key)) {
                    return;
                }

                this.selected && this.selected.classList.remove("selected"); // Remove selected class.

                switch (event.key) {
                    case "ArrowUp": {
                        const last = this.template.lastChild;
                        this.selected = this.selected ? this.selected.previousElementSibling || last : last;
                        if (!this.selected.classList.contains("no-results")) {
                            event.preventDefault(); // Prevents cursor from moving to beginning of the input.
                        }
                        break;
                    }

                    case "ArrowDown": {
                        const first = this.template.firstChild;
                        this.selected = this.selected ? this.selected.nextElementSibling || first : first;
                        break;
                    }

                    case "Escape": {
                        this.destroy();
                        break;
                    }

                    case "Enter": {
                        if (this.selected) {
                            event.preventDefault(); // Prevents form submit.
                            this.triggerOnSelect(this.selected);
                        }
                        break;
                    }

                    case "Tab": {
                        if (this.selected) {
                            this.triggerOnSelect(this.selected);
                        }
                        break;
                    }
                }

                if (this.selected && !this.selected.classList.contains("no-results")) {
                    this.selected.classList.add("selected");
                    this.input.value = this.selected.textContent;
                    this.input.setAttribute("aria-activedescendant", this.selected.id);
                }
            });

            this.template.addEventListener("click", event => {
                event.stopPropagation();
                this.triggerOnSelect(event.target);
            });

            this.template.addEventListener("mouseover", event => {
                if (event.target.tagName === "LI" && !event.target.classList.contains("no-results")) {
                    Array.from(this.template.childNodes).forEach(el => el !== event.target && el.classList.remove("selected"));
                    this.selected = event.target;
                    this.selected.classList.add("selected");
                }
            });
        }

        suggest (name) {
            this.lookup(name).then(suggestions => {
                if (!this.popper) {
                    this.popper = this.create();
                }

                // Notice: All suggestions are assumed to be in lowercase.
                const items = suggestions.map(s => ({
                    name: notSafe(s.name).replaceAll(name, `<mark>${notSafe(name)}</mark>`),
                    value: notSafe(s.value)
                }));

                if (items.length) {
                    this.template.innerHTML = "";
                    for (const [index, item] of items.entries()) {
                        this.template.innerHTML += `<li role="option" data-value="${item.value}" id="cb-opt-${index}">${item.name}</li>`;
                    }
                } else {
                    if (!this.template.querySelector(".no-results")) {
                        this.template.innerHTML = `<li role="alert" aria-live="assertive" class='no-results'>${gettext("-- no corresponding results --")}</li>`;
                    }
                }

                this.showing = true;
                this.template.style.display = "block";
                this.input.setAttribute("aria-expanded", "true");
            });
        }

        destroy () {
            if (this.popper) {
                this.input.setAttribute("aria-expanded", "false");
                this.template.style.display = "none";
                this.template.innerHTML = "";
                this.selected = null;
                this.showing = false;
                this.popper.destroy();
                this.popper = null;
            }
        }

        create () {
            return Popper.createPopper(this.input, this.template, { placement: "bottom-start" });
        }

        triggerOnSelect (selected) {
            if (selected.classList.contains("no-results")) {
                return;
            }

            this.destroy();
            this.input.value = selected.textContent;
            const value = selected.getAttribute("data-value");
            value && this.onSelect && this.onSelect(value);
        }
    }

    new AutoComplete({ // eslint-disable-line no-new
        input: findOne("#header_search"),
        lookup (name) {
            if (name.startsWith("@") && name.substr(1)) {
                return gqlc({
                    query: `query($lookup:String!){autocomplete{authors(lookup:$lookup){username}}}`,
                    variables: { lookup: name.substr(1) }
                }).then(response => {
                    return response.data.autocomplete.authors.map(user => ({
                        name: `@${user.username}`,
                        value: `@${user.username}`
                    }));
                });
            }

            return gqlc({
                query: `query($lookup:String!){autocomplete{authors(lookup:$lookup,limit:3){username}topics(lookup:$lookup,limit:7){title}}}`,
                variables: { lookup: name }
            }).then(response => {
                const topicSuggestions = response.data.autocomplete.topics.map(topic => ({
                    name: topic.title,
                    value: topic.title
                }));
                const authorSuggestions = response.data.autocomplete.authors.map(user => ({
                    name: `@${user.username}`,
                    value: `@${user.username}`
                }));
                return topicSuggestions.concat(authorSuggestions);
            });
        },

        onSelect (value) {
            window.location = "/topic/?q=" + encodeURIComponent(value);
        }
    });

    find(".author-search").forEach(input => {
        new AutoComplete({ // eslint-disable-line no-new
            input,
            lookup (name) {
                return gqlc({
                    query: `query($lookup:String!){autocomplete{authors(lookup:$lookup){username}}}`,
                    variables: { lookup: name }
                }).then(response => {
                    return response.data.autocomplete.authors.map(user => ({
                        name: user.username,
                        value: user.username
                    }));
                });
            }
        });
    });

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

    document.addEventListener("DOMContentLoaded", () => {
        find("[data-toggle=dropdown]").forEach(button => {
            button.addEventListener("click", () => {
                if (!button._dropdownInstance) {
                    button._dropdownInstance = new Dropdown(button);
                }
                button._dropdownInstance.toggle();
            });
        });
    });

    document.addEventListener("keydown", event => {
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

    document.addEventListener("click", event => {
        const dropdown = getActiveDropdown();

        if (dropdown) {
            const collapse = dropdown.menuElement.classList.contains("no-collapse") && dropdown.menuElement === event.target.closest(".dropdown-menu");
            if (event.target.classList.contains("dropdown-close") || (dropdown.button !== event.target.closest("[data-toggle=dropdown]") && !collapse)) {
                dropdown.destroy();
            }
        }
    });

    class Modal {
        constructor (modal) {
            this.modal = modal;
            this.showing = false;
            this.lead = modal.querySelector(".lead");

            modal.addEventListener("click", event => {
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
                _modal.addEventListener("transitionend", function _transitionend (event) {
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
        collapse.addEventListener("click", () => {
            collapse.closest("div").parentNode.querySelector(".collapse").classList.toggle("show");
            if (collapse.getAttribute("aria-expanded") === "false") {
                collapse.setAttribute("aria-expanded", "true");
            } else {
                collapse.setAttribute("aria-expanded", "false");
            }
        });
    });
})();

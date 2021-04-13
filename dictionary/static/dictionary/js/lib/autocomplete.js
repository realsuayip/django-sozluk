/* global gettext */

import { many, one, gqlc, notSafe, lang, template, createPopper } from "../utils"

/**
 * autocomplete source:
 * (c) 2020 Şuayip Üzülmez
 * https://github.com/realsuayip/autocomplete
 * MIT
 */

function escapeRegExChars (value) {
    return value.replace(/[|\\{}()[\]^$+*?.]/g, "\\$&")
}

function formatResult (suggestion, value) {
    /**
     *  formatResult function source:
     *  Ajax Autocomplete for jQuery, version 1.4.11
     *  (c) 2017 Tomas Kirda
     *  https://github.com/devbridge/jQuery-Autocomplete
     *  MIT
     */

    if (!value) {
        return notSafe(suggestion)
    }

    const pattern = "(" + escapeRegExChars(value) + ")"

    return notSafe(suggestion.replace(new RegExp(pattern, "gi"), "<mark>$1</mark>"))
        .replace(/&lt;(\/?mark)&gt;/g, "<$1>")
}

class AutoComplete {
    constructor (options) {
        this.input = options.input
        this.lookup = options.lookup // Takes name, returns a Promise that resolves into a list of {name, value}s.
        this.onSelect = options.onSelect // Takes value.
        this.silent = options.silent === true // Set this to true to disable no suggestions notice.
        this.highlight = options.highlight // Set this true to enable highlighting
        this.noResultsMessage = options.noResultsMessage || gettext("-- no corresponding results --")
        this.cache = options.cache === true // Set this true to enable caching

        this.cachedResults = []
        this.emptyResults = []

        this.popper = null
        this.selected = null
        this.showing = false

        const templateID = `id_${this.input.id}`
        this.template = template(`<ul role="listbox" class="autocomplete" id="${templateID}"></ul>`)
        this.input.parentNode.append(this.template)

        this.input.setAttribute("autocomplete", "off")
        this.input.setAttribute("role", "combobox")
        this.input.setAttribute("aria-owns", templateID)
        this.input.setAttribute("aria-autocomplete", "list")
        this.input.setAttribute("aria-expanded", "false")

        this.input.addEventListener("input", () => {
            const name = this.input.value.toLocaleLowerCase(lang).trim()
            this.selected = null

            if (name) {
                this.suggest(name)
            } else {
                if (this.showing) {
                    this.destroy()
                }
            }
        })

        this.input.addEventListener("focusout", () => {
            setTimeout(() => {
                this.destroy()
            }, 200)
        })

        this.input.addEventListener("keydown", event => {
            if (!["ArrowUp", "ArrowDown", "Escape", "Enter", "Tab"].includes(event.key)) {
                return
            }

            const changeSelected = ["ArrowUp", "ArrowDown"].includes(event.key)

            // Remove selected class from previously selected item.
            changeSelected && this.selected && this.selected.classList.remove("selected", "mouseover")

            switch (event.key) {
                case "ArrowUp": {
                    const last = this.template.lastChild
                    this.selected = this.selected ? this.selected.previousElementSibling || last : last
                    if (!this.selected.classList.contains("no-results")) {
                        event.preventDefault() // Prevents cursor from moving to beginning of the input.
                    }
                    break
                }

                case "ArrowDown": {
                    const first = this.template.firstChild
                    this.selected = this.selected ? this.selected.nextElementSibling || first : first
                    break
                }

                case "Escape": {
                    this.destroy()
                    break
                }

                case "Enter": {
                    if (this.selected && !this.selected.classList.contains("mouseover")) {
                        event.preventDefault() // Prevents form submit.
                        this.triggerOnSelect(this.selected)
                    }
                    break
                }

                case "Tab": {
                    if (this.selected && !event.shiftKey) {
                        this.input.value = this.selected.textContent
                    }
                    break
                }
            }

            if (changeSelected && this.selected && !this.selected.classList.contains("no-results")) {
                this.selected.classList.add("selected")
                this.input.value = this.selected.textContent
                this.input.setAttribute("aria-activedescendant", this.selected.id)
            }
        })

        this.template.addEventListener("click", event => {
            event.stopPropagation()
            this.triggerOnSelect(event.target.closest("li"))
        })

        this.template.addEventListener("mouseover", event => {
            if (event.target.tagName === "LI" && !event.target.classList.contains("no-results")) {
                Array.from(this.template.childNodes).forEach(el => el !== event.target && el.classList.remove("selected", "mouseover"))
                this.selected = event.target
                this.selected.classList.add("selected", "mouseover")
            }
        })
    }

    suggest (name) {
        if (this.cache) {
            const isEmptyResult = this.emptyResults.filter(result => name.startsWith(Object.keys(result)[0])).length

            if (isEmptyResult) {
                this.render([])
                return
            }

            const [items] = this.cachedResults.filter(result => result[name])

            if (items) {
                this.render(items[name])
                return
            }
        }

        this.lookup(name).then(suggestions => {
            const items = suggestions.map(s => ({
                name: this.highlight ? formatResult(s.name, name) : notSafe(s.name),
                value: notSafe(s.value)
            }))

            if (this.cache && (name !== "@")) {
                const resultSet = items.length ? this.cachedResults : this.emptyResults
                resultSet.push({ [name]: items })
            }

            this.render(items)
        })
    }

    render (items) {
        if (!this.popper) {
            this.popper = this.create()
        }

        if (items.length) {
            this.template.innerHTML = ""
            for (const [index, item] of items.entries()) {
                this.template.innerHTML += `<li role="option" data-value="${item.value}" id="cb-opt-${index}">${item.name}</li>`
            }
        } else {
            if (this.silent) {
                this.destroy()
                return
            }

            if (!this.template.querySelector(".no-results")) {
                this.template.innerHTML = `<li role="alert" aria-live="assertive" class='no-results'>${this.noResultsMessage}</li>`
            }
        }

        this.showing = true
        this.template.style.display = "block"
        this.input.setAttribute("aria-expanded", "true")
    }

    destroy () {
        if (this.popper) {
            this.input.setAttribute("aria-expanded", "false")
            this.template.style.display = "none"
            this.template.innerHTML = ""
            this.selected = null
            this.showing = false
            this.popper.destroy()
            this.popper = null
        }
    }

    create () {
        return createPopper(this.input, this.template, { placement: "bottom-start" })
    }

    triggerOnSelect (selected) {
        if (selected.classList.contains("no-results")) {
            return
        }

        this.destroy()
        this.input.value = selected.textContent
        const value = selected.getAttribute("data-value")
        value && this.onSelect && this.onSelect(value)
    }
}

// Initialize autocomplete inputs

const authorQuery = `query($lookup:String!){autocomplete{authors(lookup:$lookup){username}}}`

function authorAt (name) {
    // name => @username
    return gqlc({
        query: authorQuery,
        variables: { lookup: name.substr(1) }
    }).then(response => {
        return response.data.autocomplete.authors.map(user => ({
            name: `@${user.username}`,
            value: `@${user.username}`
        }))
    })
}

function fullLookup (name) {
    if (name.startsWith("@") && name.substr(1)) {
        return authorAt(name)
    }

    return gqlc({
        query: `query($lookup:String!){autocomplete{authors(lookup:$lookup,limit:3){username}topics(lookup:$lookup,limit:7){title}}}`,
        variables: { lookup: name }
    }).then(response => {
        const topicSuggestions = response.data.autocomplete.topics.map(topic => ({
            name: topic.title,
            value: topic.title
        }))
        const authorSuggestions = response.data.autocomplete.authors.map(user => ({
            name: `@${user.username}`,
            value: `@${user.username}`
        }))
        return topicSuggestions.concat(authorSuggestions)
    })
}

new AutoComplete({ // eslint-disable-line no-new
    input: one("#header_search"),
    highlight: true,
    cache: true,
    lookup: fullLookup,

    onSelect (value) {
        window.location = "/topic/?q=" + encodeURIComponent(value)
    }
})

const inEditorSearch = one("#editor_input")

if (inEditorSearch) {
    new AutoComplete({ // eslint-disable-line no-new
        input: inEditorSearch,
        silent: true,
        highlight: true,
        cache: true,
        lookup: fullLookup
    })
}

const inTopicSearch = one("#in_topic_search")

if (inTopicSearch) {
    new AutoComplete({ // eslint-disable-line no-new
        input: inTopicSearch,
        silent: true,
        highlight: true,
        cache: true,
        lookup (name) {
            if (name.startsWith("@") && name.substr(1)) {
                return authorAt(name)
            }
            return new Promise(resolve => resolve)
        },
        onSelect () {
            inTopicSearch.closest("form").submit()
        }
    })
}

many(".author-search").forEach(input => {
    new AutoComplete({ // eslint-disable-line no-new
        input,
        highlight: true,
        cache: true,
        lookup (name) {
            return gqlc({
                query: authorQuery,
                variables: { lookup: name }
            }).then(response => {
                return response.data.autocomplete.authors.map(user => ({
                    name: user.username,
                    value: user.username
                }))
            })
        }
    })
})

const titleInput = one("#user_title_edit")

if (titleInput) {
    new AutoComplete({ // eslint-disable-line no-new
        input: titleInput,
        highlight: true,
        cache: true,
        lookup (name) {
            return gqlc({
                query: `query($lookup:String!){autocomplete{topics(lookup:$lookup,limit:7){title}}}`,
                variables: { lookup: name }
            }).then(response => response.data.autocomplete.topics.map(topic => ({
                name: topic.title,
                value: topic.title
            })))
        }
    })
}

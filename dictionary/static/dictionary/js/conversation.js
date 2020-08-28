/* global gettext */

import { Handle, Handler, many, one, gqlc, notify } from "./utils"

Handle("a#message_history_show", "click", function () {
    many("ul#message_list li.bubble").forEach(item => {
        item.style.display = "list-item"
    })
    this.classList.add("dj-hidden")
})

Handle("a[role=button].chat-reverse", "click", () => {
    many("input.chat-selector").forEach(input => {
        input.checked = !input.checked
        input.dispatchEvent(new Event("change"))
    })
})

Handler("input.chat-selector", "change", function () {
    this.closest("li.chat").classList.toggle("selected")
})

function getPkSet (selected) {
    const pkSet = []
    selected.forEach(el => {
        pkSet.push(el.getAttribute("data-id"))
    })
    return pkSet
}

function selectChat (init) {
    // inbox.html || conversation.html
    let chat = init.closest("li.chat")
    if (!chat) {
        chat = init.parentNode
    }
    return chat
}

function deleteConversation (pkSet, mode) {
    const query = `mutation($pkSet:[ID!]!, $mode:String){message{deleteConversation(pkSet:$pkSet,mode:$mode){redirect}}}`
    const variables = { pkSet, mode }
    return gqlc({ query, variables })
}

// Delete (archives and active conversations)

Handler("a[role=button].chat-delete-individual", "click", function () {
    if (!confirm(gettext("are you sure to delete?"))) {
        return false
    }

    const chat = selectChat(this)
    const mode = (one("ul.threads") || chat).getAttribute("data-mode")

    deleteConversation(chat.getAttribute("data-id"), mode).then(response => {
        const data = response.data.message.deleteConversation
        if (data) {
            if (many("li.chat").length > 1) {
                chat.remove()
                notify(gettext("deleted conversation"))
            } else {
                window.location = data.redirect
            }
        }
    })
})

Handle("a[role=button].chat-delete", "click", () => {
    const selected = many("li.chat.selected")

    if (selected.length) {
        if (!confirm(gettext("are you sure to delete all selected conversations?"))) {
            return false
        }

        deleteConversation(getPkSet(selected), one("ul.threads").getAttribute("data-mode")).then(response => {
            const data = response.data.message.deleteConversation
            if (data) {
                window.location = data.redirect
            }
        })
    } else {
        notify(gettext("you need to select at least one conversation to delete"), "error")
    }
})

// Archiving

function archiveConversation (pkSet) {
    const query = `mutation($pkSet:[ID!]!){message{archiveConversation(pkSet:$pkSet){redirect}}}`
    const variables = { pkSet }
    return gqlc({ query, variables })
}

Handle("a[role=button].chat-archive", "click", () => {
    const selected = many("li.chat.selected")

    if (selected.length) {
        if (!confirm(gettext("are you sure to archive all selected conversations?"))) {
            return false
        }

        archiveConversation(getPkSet(selected)).then(response => {
            const data = response.data.message.archiveConversation
            if (data) {
                window.location = data.redirect
            }
        })
    } else {
        notify(gettext("you need to select at least one conversation to archive"), "error")
    }
})

Handler("a[role=button].chat-archive-individual", "click", function () {
    if (!confirm(gettext("are you sure to archive?"))) {
        return false
    }

    const chat = selectChat(this)

    archiveConversation(chat.getAttribute("data-id")).then(response => {
        const data = response.data.message.archiveConversation
        if (data) {
            if (many("li.chat").length > 1) {
                chat.remove()
                notify(gettext("archived conversation"))
            } else {
                window.location = data.redirect
            }
        }
    })
})

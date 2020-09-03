/* global gettext */

import { Handle, many, one, gqlc, isValidText, notify } from "./utils"
import { userAction } from "./user"

function showBlockDialog (recipient, redirect = true, returnTo = null) {
    const button = one("#block_user")
    button.setAttribute("data-username", recipient)
    button.setAttribute("data-re", redirect)
    one("#username-holder").textContent = recipient

    const modal = one("#blockUserModal")
    modal._modalInstance.show(returnTo)
}

Handle("#block_user", "click", function () {
    // Modal button click event
    const targetUser = this.getAttribute("data-username")
    const re = this.getAttribute("data-re") === "true"
    if (!re) {
        many(".entry-full").forEach(entry => {
            if (entry.querySelector(".meta .username").textContent === targetUser) {
                entry.remove()
            }
        })
    }
    userAction("block", targetUser, null, re)
})

function showMessageDialog (recipient, extraContent, returnTo = null) {
    const msgModal = one("#sendMessageModal")
    one("#sendMessageModal span.username").textContent = recipient

    if (extraContent) {
        one("#sendMessageModal textarea#message_body").value = extraContent
    }

    msgModal.setAttribute("data-for", recipient)
    msgModal._modalInstance.show(returnTo)
}

function composeMessage (recipient, body) {
    const variables = { recipient, body }
    const query = `mutation compose($body:String!,$recipient:String!){message{compose(body:$body,recipient:$recipient){feedback}}}`
    return gqlc({ query, variables }).then(function (response) {
        notify(response.data.message.compose.feedback)
    })
}

Handle("#send_message_btn", "click", function () {
    const textarea = one("#sendMessageModal textarea")
    const msgModal = one("#sendMessageModal")
    const body = textarea.value

    if (body.length < 3) {
        // not strictly needed but written so as to reduce api calls.
        notify(gettext("if only you could write down something"), "error")
        return
    }

    if (!isValidText(body)) {
        notify(gettext("this content includes forbidden characters."), "error")
        return
    }

    this.disabled = true

    composeMessage(msgModal.getAttribute("data-for"), body).then(() => {
        msgModal._modalInstance.hide()
        textarea.value = ""
    }).finally(() => {
        this.disabled = false
    })
})

export { showBlockDialog, showMessageDialog }

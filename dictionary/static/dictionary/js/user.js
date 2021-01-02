/* global gettext */

import { Handle, Handler, gqlc, notify, toggleText } from "./utils"
import { showBlockDialog, showMessageDialog } from "./dialog"

function userAction (type, recipient, loc = null, re = true) {
    return gqlc({ query: `mutation{user{${type}(username:"${recipient}"){feedback redirect}}}` }).then(function (response) {
        const info = response.data.user[type]
        if (re && (loc || info.redirect)) {
            window.location = loc || info.redirect
        } else {
            notify(info.feedback)
        }
    })
}

Handler(".block-user-trigger", "click", function () {
    const sync = this.classList.contains("sync")
    const recipient = this.getAttribute("data-username")

    if (sync) {
        return userAction("block", recipient, location)
    }

    userAction("block", recipient, null, false).then(function () {
        toggleText(this, gettext("remove block"), gettext("block this guy"))
    }.bind(this))
})

Handler(".follow-user-trigger", "click", function () {
    const targetUser = this.parentNode.getAttribute("data-username")
    userAction("follow", targetUser)
    toggleText(this.querySelector("a"), gettext("follow"), gettext("unfollow"))
})

Handle("ul.user-links", "click", function (event) {
    const recipient = this.getAttribute("data-username")
    if (event.target.matches("li.block-user a")) {
        showBlockDialog(recipient, true, event.target)
    } else if (event.target.matches("li.send-message a")) {
        showMessageDialog(recipient, null, event.target)
    }
})

export { userAction }

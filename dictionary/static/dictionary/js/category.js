/* global pgettext */

import { Handler, gqlc, toggleText } from "./utils"

function categoryAction (type, pk) {
    return gqlc({ query: `mutation{category{${type}(pk:"${pk}"){feedback}}}` })
}

Handler("button.follow-category-trigger", "click", function () {
    categoryAction("follow", this.getAttribute("data-category-id")).then(() => {
        toggleText(this, pgettext("category-list", "unfollow"), pgettext("category-list", "follow"))
        this.classList.toggle("faded")
    })
})

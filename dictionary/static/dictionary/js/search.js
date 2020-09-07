import { userIsMobile } from "./mql"
import { LeftFrame } from "./left-frame"
import { Handle, Handler, one } from "./utils"

function dictToParameters (dict) {
    const str = []
    for (const key in dict) {
        // a. check if the property/key is defined in the object itself, not in parent
        // b. check if the key is not empty
        if (Object.prototype.hasOwnProperty.call(dict, key) && dict[key]) {
            str.push(encodeURIComponent(key) + "=" + encodeURIComponent(dict[key]))
        }
    }
    return str.join("&")
}

function populateSearchResults (searchParameters) {
    if (!searchParameters) {
        return
    }

    const slug = "search"

    if (userIsMobile) {
        window.location = `/threads/${slug}/?${searchParameters}`
    }
    LeftFrame.populate(slug, 1, null, searchParameters)
}

Handle("button#perform_advanced_search", "click", () => {
    const favoritesElement = one("input#in_favorites_dropdown")

    const keywords = one("input#keywords_dropdown").value
    const authorNick = one("input#author_nick_dropdown").value
    const isNiceOnes = one("input#nice_ones_dropdown").checked
    const isFavorites = favoritesElement && favoritesElement.checked
    const fromDate = one("input#date_from_dropdown").value
    const toDate = one("input#date_to_dropdown").value
    const ordering = one("select#ordering_dropdown").value

    const keys = {
        keywords,
        author_nick: authorNick,
        is_nice_ones: isNiceOnes,
        is_in_favorites: isFavorites,
        from_date: fromDate,
        to_date: toDate,
        ordering
    }
    populateSearchResults(dictToParameters(keys))
})

Handler("body", "click", event => {
    if (event.target.matches("a[role=button].quicksearch")) {
        const term = event.target.getAttribute("data-keywords")
        let parameter
        if (term.startsWith("@") && term.substr(1)) {
            parameter = `author_nick=${term.substr(1)}`
        } else {
            parameter = `keywords=${term}`
        }
        const searchParameters = parameter + "&ordering=newer"
        populateSearchResults(searchParameters)
    }
})

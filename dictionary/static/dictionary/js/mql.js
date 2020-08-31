import { many, one, notify, notSafe, Handle, userIsAuthenticated, gqlc, cookies } from "./utils"

let userIsMobile = false
let lastScrollTop = 0

function hideRedundantHeader () {
    const delta = 30
    let st = window.pageYOffset
    const header = one("header.page_header")
    const sub = one(".sub-nav")

    if (st < 0) {
        st = 0 // Reset negative offset (iOS Safari)
    }

    if (Math.abs(lastScrollTop - st) <= delta) {
        return
    }

    const reset = () => {
        sub.style.marginTop = "0"
        header.style.top = "0"
    }

    if (st > lastScrollTop) {
        // Down scroll code
        sub.style.marginTop = ".75em"
        header.style.top = "-55px"
        header.addEventListener("mouseover", reset, { once: true })
    } else {
        reset()
    }
    lastScrollTop = st
}

const mql = window.matchMedia("(max-width: 810px)")

function desktopView () {
    userIsMobile = false

    // Find left frame scroll position.
    if (parseInt(localStorage.getItem("where")) > 0) {
        one("#left-frame-nav").scroll(0, localStorage.getItem("where"))
    }

    // Restore header.
    window.removeEventListener("scroll", hideRedundantHeader)
    one(".sub-nav").style.marginTop = "0"
    one("header.page_header").style.top = "0"

    // Code to render swh references properly (reverse)
    many("a[data-sup]").forEach(sup => {
        sup.innerHTML = `*`
    })
}

function mobileView () {
    userIsMobile = true
    // Code to hide some part of the header on mobile scroll.
    window.addEventListener("scroll", hideRedundantHeader)

    // Code to render swh references properly
    many("a[data-sup]").forEach(sup => {
        sup.innerHTML = `<sup>${notSafe(sup.getAttribute("data-sup"))}</sup>`
    })
}

function mqlsw (mql) {
    // check mql & switch
    if (mql.matches) {
        mobileView()
    } else {
        desktopView()
    }
}

// Safari doesn't support mql.addEventListener yet, so we have
// to use deprecated addListener.
mql.addListener(mqlsw)

document.addEventListener("DOMContentLoaded", () => {
    // DOM ready.
    mqlsw(mql)

    // Handles notifications passed by django's message framework.
    const requestMessages = one("#request-messages")
    if (requestMessages.getAttribute("data-has-messages") === "true") {
        let delay = 2000
        requestMessages.childNodes.forEach(message => {
            const isPersistent = message.getAttribute("data-extra").includes("persistent")
            notify(message.getAttribute("data-message"), message.getAttribute("data-level"), delay, isPersistent)
            delay += 1000
        })
    }
})

// Theme

const themeExpires = 90

function setTheme (theme) {
    const body = one("body")
    const icon = one("[data-toggle=theme]").querySelector("use")
    body.style.transition = "background-color .5s ease"

    if (theme === "dark") {
        body.classList.add("dark")
        icon.setAttribute("href", "#sun")
    } else {
        body.classList.remove("dark")
        icon.setAttribute("href", "#moon")
    }
}

Handle("[data-toggle=theme]", "click", function () {
    if (userIsAuthenticated) {
        gqlc({ query: "mutation{user{toggleTheme{theme}}}" }).then(response => {
            setTheme(response.data.user.toggleTheme.theme)
        })
    } else {
        if (cookies.get("theme") === "dark") {
            cookies.set("theme", "light", { expires: themeExpires })
            setTheme("light")
        } else {
            cookies.set("theme", "dark", { expires: themeExpires })
            setTheme("dark")
        }
    }
})

if (!userIsAuthenticated && !cookies.get("theme") && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    cookies.set("theme", "dark", { expires: themeExpires })
    setTheme("dark")
}

export { userIsMobile }

/* global gettext */

import { Handle, Handler, template, gqlc, notify } from "./utils"

const showImageErrorMessage = () => {
    notify(gettext("image could not be displayed. it might have been deleted."), "error", 2200)
}

Handle(document, "click", event => {
    const self = event.target
    if (self.matches(".entry a[data-img], .text-formatted a[data-img]")) {
        if (self.hasAttribute("data-broken")) {
            showImageErrorMessage()
            return
        }

        if (!self.hasAttribute("data-loaded")) {
            const p = self.parentNode
            p.style.maxHeight = "none" // Click "read more" button.
            const readMore = p.querySelector(".read_more")

            if (readMore) {
                readMore.style.display = "none"
            }

            const url = self.getAttribute("data-img")
            const image = template(`<img src="${url}" alt="${gettext("image")}" class="img-thumbnail img-fluid" draggable="false">`)
            const expander = template(`<a rel="ugc nofollow noopener" title="${gettext("open full image in new tab")}" href="${url}" target="_blank" class="ml-3 position-relative" style="top: 2px;"></a>`)

            image.onerror = () => {
                showImageErrorMessage()
                image.style.display = "none"
                expander.style.display = "none"
                self.setAttribute("data-broken", "true")
            }

            self.after(expander)
            expander.after(image)
            self.setAttribute("aria-expanded", "true")
        } else {
            self.nextElementSibling.classList.toggle("d-none")
            self.nextElementSibling.nextElementSibling.classList.toggle("d-none")

            if (self.getAttribute("aria-expanded") === "true") {
                self.setAttribute("aria-expanded", "false")
            } else {
                self.setAttribute("aria-expanded", "true")
            }
        }
        self.setAttribute("data-loaded", "true")
    }
})

function deleteImage (slug) {
    return gqlc({
        query: "mutation($slug:String!){image{delete(slug:$slug){feedback}}}",
        variables: { slug }
    })
}

Handler("a[role=button].delete-image", "click", function () {
    if (confirm(gettext("Are you sure?"))) {
        const img = this.closest(".image-detail")
        deleteImage(img.getAttribute("data-slug"))
        img.remove()
    }
})

export { deleteImage }

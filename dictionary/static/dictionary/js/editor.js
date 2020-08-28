/* global gettext, pgettext */

import { Handle, Handler, one } from "./utils"
import { deleteImage } from "./image"
import Dropzone from "dropzone"

function insertAtCaret (el, insertValue) {
    const startPos = el.selectionStart
    if (startPos) {
        const endPos = el.selectionEnd
        const scrollTop = el.scrollTop
        el.value = el.value.substring(0, startPos) + insertValue + el.value.substring(endPos, el.value.length)
        el.focus()
        el.selectionStart = startPos + insertValue.length
        el.selectionEnd = startPos + insertValue.length
        el.scrollTop = scrollTop
    } else {
        el.value += insertValue
        el.focus()
    }
}

function insertMeta (type) {
    let fmt

    switch (type) {
        case "ref":
            fmt = [gettext("target topic, #entry or @author to reference:"), text => `(${pgettext("editor", "see")}: ${text})`]
            break
        case "thingy":
            fmt = [gettext("target topic, #entry or @author to thingy:"), text => `\`${text}\``]
            break
        case "swh":
            fmt = [gettext("what should be referenced in asterisk?"), text => `\`:${text}\``]
            break
        case "spoiler": {
            const spoiler = gettext("spoiler")
            fmt = [gettext("what to write between spoiler tags?"), text => `--\`${spoiler}\`--\n${text}\n--\`${spoiler}\`--`]
            break
        }
    }

    return { label: fmt[0], format: fmt[1] }
}

function replaceText (textarea, type) {
    const start = textarea.selectionStart
    const finish = textarea.selectionEnd
    const allText = textarea.value
    const sel = allText.substring(start, finish)
    if (!sel) {
        return false
    } else {
        if (type === "link") {
            const linkText = prompt(gettext("which address to link?"), "http://")
            if (linkText !== "http://") {
                textarea.value = allText.substring(0, start) + `[${linkText} ${sel}]` + allText.substring(finish, allText.length)
            }
        } else {
            textarea.value = allText.substring(0, start) + insertMeta(type).format(sel) + allText.substring(finish, allText.length)
        }
        textarea.focus()
        return true
    }
}

Handle("button#insert_image", "click", () => {
    const dropzone = one(".dropzone")
    dropzone.style.display = dropzone.style.display === "none" ? "" : "none"
})

Handle("button#insert_link", "click", () => {
    if (!replaceText(one("#user_content_edit"), "link")) {
        const linkText = prompt(gettext("which address to link?"), "http://")
        if (linkText && linkText !== "http://") {
            const linkName = prompt(gettext("alias for the link?"))
            if (linkName) {
                insertAtCaret(one("#user_content_edit"), `[${linkText} ${linkName}]`)
            }
        }
    }
})

Handler("button.insert", "click", function () {
    const type = this.getAttribute("data-type")
    if (!replaceText(one("#user_content_edit"), type)) {
        const meta = insertMeta(type)
        const text = prompt(meta.label)
        if (text) {
            insertAtCaret(one("#user_content_edit"), meta.format(text))
        }
    }
})

Dropzone.options.userImageUpload = {
    addRemoveLinks: true,
    paramName: "file",
    maxFilesize: 2.5, // MB
    acceptedFiles: "image/*",
    maxFiles: 10,
    dictRemoveFileConfirmation: gettext("Are you sure?"),
    dictDefaultMessage: gettext("click or drop files here to upload"),
    dictRemoveFile: gettext("delete image"),
    dictFileTooBig: gettext("File is too big ({{filesize}}MB). Max filesize: {{maxFilesize}}MB."),
    dictMaxFilesExceeded: gettext("You can not upload any more files."),
    dictUploadCanceled: gettext("Upload canceled."),
    dictCancelUploadConfirmation: gettext("Are you sure?"),

    success (file, response) {
        insertAtCaret(one("#user_content_edit"), `(${pgettext("editor", "image")}: ${response.slug})`)
    },

    removedfile (file) {
        file.previewElement.remove()
        const text = one("#user_content_edit")
        const slug = JSON.parse(file.xhr.response).slug
        text.value = text.value.replace(new RegExp(`\\(${pgettext("editor", "image")}: ${slug}\\)`, "g"), "")
        deleteImage(slug)
    }
}

// capture_page.js - Pea Princess (vet-flat) by Hsien Hao (Jacky) Chen - CC BY 4.0
// https://github.com/jacky18008/pea-princess
//
// Runs in the person's own browser, on a listing page they opened themselves, and hands
// back one text document with what that page holds: the title, the address bar, the meta
// tags, every JSON-LD block, every JSON data block, the inline data scripts (a page's own
// `name = {...}` assignment), the visible text, and the image links. It makes no network
// request of its own and reads nothing but the page in front of the person. The document
// is HTML inside a .txt file, which scripts/listing_fields.py reads as a saved page.
//
// iPhone / iPad (Safari only - the action below runs on Safari web pages; from another browser,
//   copy the link and open it in Safari first): a Shortcut in the share sheet.
//   Shortcuts app > + > name it "Hand page to Pea Princess" > (i) Show in Share Sheet, receive
//   "Safari web pages" > add the action "Run JavaScript on Web Page" (Settings > Shortcuts >
//   Advanced > Allow Running Scripts must be on) and paste this whole file into it > add
//   "Save File" (or "Share"). On a listing page: share button > the shortcut > the .txt lands
//   in Files (or goes straight to the chat app), and the person attaches it.
// Desktop: "Save Page As > Webpage, Complete" already carries the same data; this file is
//   only for people who prefer one click. Make a bookmark whose address is "javascript:"
//   followed by this file with the comment lines removed and "peaCaptureDownload();" at the end.
//
// Nothing here is written for one website: no site names, no page selectors.

function peaCapturePage(doc) {
  var d = doc || document;
  var esc = function (s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  };
  var head = [];
  var canonical = d.querySelector('link[rel="canonical"]');
  head.push("<title>" + esc(d.title || "") + "</title>");
  head.push('<link rel="canonical" href="' + esc((canonical && canonical.href) || d.location.href) + '">');
  head.push("<!-- captured from " + esc(d.location.href) + " at " + new Date().toISOString() +
            " by the person's own browser; no network request was made -->");
  var metas = d.querySelectorAll("meta[property], meta[name]");
  for (var i = 0; i < metas.length; i++) {
    var attr = metas[i].getAttribute("property") ? "property" : "name";
    var key = metas[i].getAttribute(attr), content = metas[i].getAttribute("content");
    if (key && content !== null) {
      head.push("<meta " + attr + '="' + esc(key) + '" content="' + esc(content) + '">');
    }
  }
  // Data the page carries for itself: JSON-LD, JSON blocks, and inline `x = {...}` assignments.
  var scripts = d.querySelectorAll("script");
  var kept = 0, bytes = 0, LIMIT = 4 * 1024 * 1024;
  var assignment = /^\s*(?:(?:var|let|const)\s+)?(?:window\.|self\.|globalThis\.)?[\w$.]+(?:\[[^\]]*\])?\s*=\s*[\[{]/;
  for (var j = 0; j < scripts.length; j++) {
    var type = (scripts[j].getAttribute("type") || "").toLowerCase();
    var text = scripts[j].textContent || "";
    if (!text.trim()) { continue; }
    var isJson = type.indexOf("json") >= 0;
    var isData = !isJson && (type === "" || type.indexOf("javascript") >= 0) &&
                 text.length > 200 && assignment.test(text.slice(0, 300));
    if (!(isJson || isData) || bytes + text.length > LIMIT) { continue; }
    bytes += text.length; kept += 1;
    head.push("<script" + (type ? ' type="' + esc(type) + '"' : "") + ">" +
              text.replace(/<\/script/gi, "<\\/script") + "<\/script>");   // "<\/" keeps this file safe inline
  }
  head.push("<!-- " + kept + " data block(s), " + bytes + " characters -->");
  // What the person sees, then every picture link on the page (for them to open, not to fetch).
  var body = [];
  var visible = (d.body && (d.body.innerText || d.body.textContent)) || "";
  body.push("<pre>" + esc(visible) + "</pre>");
  var seen = {}, links = [];
  var elements = d.querySelectorAll("img, source[srcset], a[href]");
  for (var k = 0; k < elements.length; k++) {
    var el = elements[k], u;
    if (el.tagName === "SOURCE") {
      u = (el.getAttribute("srcset") || "").split(",")[0].trim().split(/\s+/)[0];
    } else {
      u = el.getAttribute("src") || el.getAttribute("data-src") || el.getAttribute("href") || "";
    }
    if (!u || u.indexOf("data:") === 0 || u.indexOf("javascript:") === 0) { continue; }
    try { u = new URL(u, d.location.href).href; } catch (e) { continue; }
    if (el.tagName === "A" && !/\.(jpe?g|png|webp|gif|pdf)(\?|#|$)/i.test(u)) { continue; }
    if (seen[u]) { continue; }
    seen[u] = true; links.push(u);
  }
  body.push("<ul>" + links.slice(0, 300).map(function (u) {
    return '<li><a href="' + esc(u) + '">' + esc(u) + "</a></li>";
  }).join("\n") + "</ul>");
  return "<!doctype html>\n<html><head>\n<meta charset=\"utf-8\">\n" + head.join("\n") +
         "\n</head><body>\n" + body.join("\n") + "\n</body></html>\n";
}

// Desktop bookmarklet: the same document as a .txt download.
function peaCaptureDownload() {
  var out = peaCapturePage(document);
  var name = "listing-capture-" + new Date().toISOString().slice(0, 10) + ".txt";
  var blob = new Blob([out], { type: "text/plain;charset=utf-8" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  return name;
}

// iOS Shortcuts ("Run JavaScript on Web Page") supplies completion(); hand it the document.
if (typeof completion === "function") {
  completion(peaCapturePage(document));
}

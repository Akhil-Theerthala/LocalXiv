(function (root, factory) {
  const api = factory();
  root.XivKindle = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(globalThis, function () {
  "use strict";

  const MODERN_ID = /^\d{4}\.\d{4,5}(?:v\d+)?$/;
  const LEGACY_ID = /^[A-Za-z][A-Za-z.-]*\/\d{7}(?:v\d+)?$/;

  function parsePaperUrl(value) {
    try {
      const url = new URL(value);
      const hostname = url.hostname.toLowerCase();
      let site;
      if (hostname === "arxiv.org" || hostname === "www.arxiv.org") site = "arxiv";
      else if (hostname === "alphaxiv.org" || hostname === "www.alphaxiv.org") {
        site = "alphaxiv";
      } else return null;
      if (url.protocol !== "https:") return null;
      const path = decodeURIComponent(url.pathname);
      if (!path.startsWith("/abs/")) return null;
      const id = path.slice(5).replace(/\/$/, "");
      if (!MODERN_ID.test(id) && !LEGACY_ID.test(id)) return null;
      return { id, site };
    } catch {
      return null;
    }
  }

  function normalizePaperUrls(values) {
    const seen = new Set();
    const urls = [];
    for (const value of values) {
      const paper = parsePaperUrl(value);
      if (!paper || seen.has(paper.id)) continue;
      seen.add(paper.id);
      const origin = paper.site === "alphaxiv" ? "https://www.alphaxiv.org" : "https://arxiv.org";
      urls.push(`${origin}/abs/${paper.id}`);
    }
    return urls;
  }

  function cleanCollectionTitle(value) {
    const title = String(value || "")
      .split(/\s*\|\s*alphaXiv/i)[0]
      .replace(/\s+/g, " ")
      .trim();
    return !title || title.toLowerCase() === "alphaxiv" ? "alphaXiv Library" : title.slice(0, 160);
  }

  function pageContext(activeUrl, paperUrls, title) {
    const paper = parsePaperUrl(activeUrl);
    if (paper) return { kind: "paper", id: paper.id, site: paper.site };
    try {
      const url = new URL(activeUrl);
      if (
        url.protocol === "https:" &&
        (url.hostname === "alphaxiv.org" || url.hostname === "www.alphaxiv.org")
      ) {
        const urls = normalizePaperUrls(paperUrls);
        if (urls.length) return { kind: "collection", title: cleanCollectionTitle(title), urls };
      }
    } catch {
      // Unsupported page state below.
    }
    return { kind: "unsupported" };
  }

  function normalizeKindleEmail(value) {
    const email = String(value || "").trim();
    const match = email.match(/^([^@\s]+)@((?:free\.)?kindle\.com)$/i);
    return match ? `${match[1]}@${match[2].toLowerCase()}` : null;
  }

  function settingsSummary(email) {
    return normalizeKindleEmail(email) ? "Kindle address saved" : "Add Kindle address";
  }

  function actionLabel(context) {
    if (context.kind === "paper") return "Send paper";
    if (context.kind === "collection") {
      const count = context.urls.length;
      return `Compile and send ${count} ${count === 1 ? "paper" : "papers"}`;
    }
    return "Unavailable on this page";
  }

  function jobIdentity(request) {
    const urls = normalizePaperUrls(request?.urls || []);
    if (Array.isArray(request?.urls)) {
      return {
        job_label: cleanCollectionTitle(request.collection_title),
        paper_count: urls.length,
      };
    }
    const paper = parsePaperUrl(request?.url);
    return { job_label: `Paper ${paper?.id || "unknown"}`, paper_count: 1 };
  }

  async function storeTerminalJob(response, sessionStorage, identity = {}) {
    const job = {
      ...identity,
      state: response?.ok ? "success" : "error",
      message: response?.message || "Conversion failed.",
      epub_path: response?.epub_path,
    };
    if (response?.epub_path) {
      const stale = await sessionStorage.get(null);
      await sessionStorage.set({ jobState: job });
      const staleKeys = Object.keys(stale).filter((key) => key !== "jobState");
      if (staleKeys.length) await sessionStorage.remove(staleKeys);
      return job;
    }
    await sessionStorage.set({ jobState: job });
    return job;
  }

  return {
    actionLabel,
    cleanCollectionTitle,
    jobIdentity,
    normalizeKindleEmail,
    normalizePaperUrls,
    pageContext,
    parsePaperUrl,
    settingsSummary,
    storeTerminalJob,
  };
});

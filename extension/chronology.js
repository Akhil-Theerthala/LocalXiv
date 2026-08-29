(function (root, factory) {
  const api = factory();
  root.XivChronology = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(globalThis, function () {
  "use strict";

  const MODERN_ID = /^\d{4}\.\d{4,5}(?:v\d+)?$/;
  const LEGACY_ID = /^[A-Za-z][A-Za-z.-]*\/\d{7}(?:v\d+)?$/;
  const ATOM_NS = "http://www.w3.org/2005/Atom";
  const API_ORIGIN = "https://export.arxiv.org";
  const MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
  const REQUEST_INTERVAL_MS = 3000;
  const REQUEST_TIMEOUT_MS = 30000;

  function baseArxivId(value) {
    if (typeof value !== "string") return null;
    if (!MODERN_ID.test(value) && !LEGACY_ID.test(value)) return null;
    return value.replace(/v\d+$/, "");
  }

  function parseAtomEntryId(value) {
    try {
      const url = new URL(value);
      if (
        !["http:", "https:"].includes(url.protocol) ||
        !["arxiv.org", "www.arxiv.org"].includes(url.hostname.toLowerCase())
      ) {
        return null;
      }
      const path = decodeURIComponent(url.pathname);
      if (!path.startsWith("/abs/")) return null;
      return baseArxivId(path.slice(5).replace(/\/$/, ""));
    } catch {
      return null;
    }
  }

  function uniqueBaseIds(papers) {
    const ids = [];
    const seen = new Set();
    for (const paper of papers) {
      const id = baseArxivId(paper?.id);
      if (!id) throw new Error("A chronology paper has an invalid arXiv identifier.");
      if (seen.has(id)) continue;
      seen.add(id);
      ids.push(id);
    }
    return ids;
  }

  function chronologyFingerprint(papers) {
    return JSON.stringify(uniqueBaseIds(papers));
  }

  function buildLookupUrl(papers) {
    const ids = uniqueBaseIds(papers);
    const url = new URL("/api/query", API_ORIGIN);
    url.search = new URLSearchParams({
      id_list: ids.join(","),
      start: "0",
      max_results: String(ids.length),
    });
    return url.toString();
  }

  function parseAtomFeed(xmlText, DOMParserImpl = globalThis.DOMParser) {
    if (typeof DOMParserImpl !== "function") {
      throw new Error("DOMParser is unavailable for the arXiv chronology response.");
    }
    const documentValue = new DOMParserImpl().parseFromString(xmlText, "application/xml");
    if (documentValue.getElementsByTagName("parsererror").length) {
      throw new Error("The arXiv chronology response is not valid XML.");
    }

    return [...documentValue.getElementsByTagNameNS(ATOM_NS, "entry")].map((entry) => {
      const ids = entry.getElementsByTagNameNS(ATOM_NS, "id");
      if (ids.length !== 1) {
        throw new Error("An arXiv chronology entry must contain exactly one Atom id.");
      }
      const publishedValues = entry.getElementsByTagNameNS(ATOM_NS, "published");
      if (publishedValues.length !== 1) {
        throw new Error("An arXiv chronology entry must contain exactly one Atom published timestamp.");
      }

      const rawId = String(ids[0].textContent || "").trim();
      try {
        const url = new URL(rawId);
        if (
          ["arxiv.org", "www.arxiv.org"].includes(url.hostname.toLowerCase()) &&
          url.pathname.startsWith("/api/errors")
        ) {
          throw new Error("The arXiv chronology API returned an error entry.");
        }
      } catch (error) {
        if (error.message === "The arXiv chronology API returned an error entry.") throw error;
      }

      const id = parseAtomEntryId(rawId);
      if (!id) throw new Error("An arXiv chronology entry has an invalid id.");
      return {
        id,
        published: String(publishedValues[0].textContent || "").trim(),
      };
    });
  }

  function orderPapersByInitialSubmission(papers, records) {
    const requestedIds = uniqueBaseIds(papers);
    const requested = new Set(requestedIds);
    const timestamps = new Map();

    for (const record of records) {
      const id = baseArxivId(record?.id);
      if (!id || !requested.has(id)) {
        throw new Error(`Unknown chronology record for arXiv ${record?.id}.`);
      }
      if (timestamps.has(id)) {
        throw new Error(`Duplicate chronology record for arXiv ${id}.`);
      }
      const timestamp = Date.parse(record.published);
      if (Number.isNaN(timestamp)) {
        throw new Error(`Invalid published date for arXiv ${id}.`);
      }
      timestamps.set(id, timestamp);
    }

    for (const id of requestedIds) {
      if (!timestamps.has(id)) {
        throw new Error(`Missing chronology record for arXiv ${id}.`);
      }
    }

    return papers
      .map((paper, index) => {
        const timestamp = timestamps.get(baseArxivId(paper.id));
        const submitted = new Date(timestamp).toISOString();
        return {
          index,
          timestamp,
          paper: {
            ...paper,
            initialSubmittedAt: submitted,
            initialSubmittedDate: submitted.slice(0, 10),
          },
        };
      })
      .sort((left, right) => left.timestamp - right.timestamp || left.index - right.index)
      .map(({ paper }) => paper);
  }

  async function fetchInitialSubmissionRecords(papers, options = {}) {
    if (!Array.isArray(papers) || papers.length < 1 || papers.length > 50) {
      throw new Error("arXiv chronology requests require 1 to 50 papers.");
    }

    const fetchImpl = options.fetchImpl || globalThis.fetch;
    if (typeof fetchImpl !== "function") {
      throw new Error("Fetch is unavailable for the arXiv chronology request.");
    }

    const controller = new AbortController();
    const request = (async () => {
      const response = await fetchImpl(buildLookupUrl(papers), {
        signal: controller.signal,
        headers: { Accept: "application/atom+xml" },
      });
      if (!response.ok) {
        throw new Error(`The arXiv chronology request failed with HTTP ${response.status}.`);
      }

      const contentLength = Number(response.headers.get("content-length"));
      if (Number.isFinite(contentLength) && contentLength > MAX_RESPONSE_BYTES) {
        throw new Error("The arXiv chronology response is too large.");
      }
      const xmlText = await response.text();
      if (new TextEncoder().encode(xmlText).byteLength > MAX_RESPONSE_BYTES) {
        throw new Error("The arXiv chronology response is too large.");
      }
      return parseAtomFeed(xmlText, options.DOMParserImpl);
    })();

    let timeoutId;
    const timeout = new Promise((_resolve, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error("The arXiv chronology request timed out."));
        controller.abort();
      }, options.timeoutMs ?? REQUEST_TIMEOUT_MS);
    });
    try {
      return await Promise.race([request, timeout]);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async function resolveInitialSubmissionOrder(papers, options = {}) {
    const sessionStorage = options.sessionStorage || globalThis.chrome?.storage?.session;
    if (!sessionStorage) {
      throw new Error("Session storage is unavailable for arXiv chronology.");
    }
    const now = options.now || Date.now;
    const sleep = options.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    const fingerprint = chronologyFingerprint(papers);
    const state = await sessionStorage.get(["chronologyLastRequestAt", "chronologyCache"]);
    const cache = state.chronologyCache;

    if (!options.bypassCache && cache?.fingerprint === fingerprint) {
      try {
        return orderPapersByInitialSubmission(papers, cache.records);
      } catch {
        // Ignore invalid session data and replace it with a verified response.
      }
    }

    if (Number.isFinite(state.chronologyLastRequestAt)) {
      const remaining = Math.max(
        0,
        REQUEST_INTERVAL_MS - (now() - state.chronologyLastRequestAt),
      );
      if (remaining) await sleep(remaining);
    }

    const requestStartedAt = now();
    await sessionStorage.set({ chronologyLastRequestAt: requestStartedAt });
    const records = await fetchInitialSubmissionRecords(papers, options);
    const ordered = orderPapersByInitialSubmission(papers, records);
    await sessionStorage.set({ chronologyCache: { fingerprint, records } });
    return ordered;
  }

  return {
    baseArxivId,
    parseAtomEntryId,
    chronologyFingerprint,
    buildLookupUrl,
    parseAtomFeed,
    orderPapersByInitialSubmission,
    fetchInitialSubmissionRecords,
    resolveInitialSubmissionOrder,
  };
});

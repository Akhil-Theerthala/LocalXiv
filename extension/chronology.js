(function (root, factory) {
  const api = factory();
  root.XivChronology = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(globalThis, function () {
  "use strict";

  const MODERN_ID = /^\d{4}\.\d{4,5}(?:v\d+)?$/;
  const LEGACY_ID = /^[A-Za-z][A-Za-z.-]*\/\d{7}(?:v\d+)?$/;
  const ATOM_NS = "http://www.w3.org/2005/Atom";

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
    const url = new URL("https://export.arxiv.org/api/query");
    url.search = new URLSearchParams({
      id_list: ids.join(","),
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

  return {
    baseArxivId,
    parseAtomEntryId,
    chronologyFingerprint,
    buildLookupUrl,
    parseAtomFeed,
    orderPapersByInitialSubmission,
  };
});

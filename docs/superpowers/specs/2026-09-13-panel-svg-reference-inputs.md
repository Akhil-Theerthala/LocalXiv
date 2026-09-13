# Panel SVG reference inputs

These examples were supplied by the user during the 2026-09-13 design discussion. They show the scale and construction style intended for a single panel. Whitespace and attribute ordering are condensed here; their geometry, labels, values, and styling dependencies are retained.

Read this file when implementing or reviewing the construction guide in Task 2 of the [rebuild plan](../plans/2026-09-13-overview-workflow-rebuild.md). The [design](2026-09-13-overview-workflow-rebuild-design.md) owns workflow requirements.

These are reference inputs, not verified production fixtures. They depend on CSS variables and text classes defined outside the snippets. Convert those dependencies into explicit attributes, render the results in LocalXiv, and inspect them before adding production examples. Keep the instructional pattern while adapting typography to the shared drawing scale. Example IP addresses, counters, and protocol claims are illustrative reference content; do not copy them into unrelated paper explanations.

## Separate opposing flows

Two endpoint panels contain the participants. Separate upper and lower tracks distinguish the counters. Repeated tiles show increments, with dashed question-mark tiles marking unknown starting values.

```svg
<svg viewBox="0 0 680 320" role="img" aria-label="Two endpoint panels with a channel between them, and one arrow travelling in each direction. The upper arrow runs from the client to the server and carries the client's counter. Its first tile holds a question mark because nobody has seen that starting number, and the next two tiles hold 8,532,412 and 8,532,413. The lower arrow runs from the server to the client and carries the server's counter. Again the first tile holds a question mark, and the next two tiles hold 2,741,020 and 2,741,021. The two counters are separate, so neither side knows where the other one starts.">
  <rect x="12" y="64" width="164" height="144" rx="10" style="fill: var(--paper-sunk); stroke: var(--rule-strong); stroke-width: 1.5"/>
  <rect x="504" y="64" width="164" height="144" rx="10" style="fill: var(--paper-sunk); stroke: var(--rule-strong); stroke-width: 1.5"/>
  <text class="t-strong" x="92" y="127" text-anchor="middle">client</text>
  <text x="92" y="149" text-anchor="middle">192.168.1.24:51820</text>
  <text class="t-strong" x="588" y="127" text-anchor="middle">server</text>
  <text x="588" y="149" text-anchor="middle">203.0.113.9:443</text>
  <line x1="176" y1="88" x2="492" y2="88" style="stroke: var(--link); stroke-width: 2"/>
  <path d="M 492 81.5 L 504 88 L 492 94.5 Z" style="fill: var(--link)"/>
  <line x1="504" y1="184" x2="188" y2="184" style="stroke: var(--link); stroke-width: 2"/>
  <path d="M 188 177.5 L 176 184 L 188 190.5 Z" style="fill: var(--link)"/>
  <rect x="220" y="74" width="72" height="28" rx="4" style="fill: var(--paper-deep); stroke: var(--ink-faint); stroke-width: 1.75; stroke-dasharray: 4 3"/>
  <text class="t-strong" x="256" y="94" text-anchor="middle" style="font-size: 16px">?</text>
  <rect x="304" y="74" width="72" height="28" rx="4" style="fill: var(--paper-sunk); stroke: var(--rule); stroke-width: 1"/>
  <text x="340" y="92" text-anchor="middle">8,532,412</text>
  <rect x="388" y="74" width="72" height="28" rx="4" style="fill: var(--paper-sunk); stroke: var(--rule); stroke-width: 1"/>
  <text x="424" y="92" text-anchor="middle">8,532,413</text>
  <rect x="220" y="170" width="72" height="28" rx="4" style="fill: var(--paper-deep); stroke: var(--ink-faint); stroke-width: 1.75; stroke-dasharray: 4 3"/>
  <text class="t-strong" x="256" y="190" text-anchor="middle" style="font-size: 16px">?</text>
  <rect x="304" y="170" width="72" height="28" rx="4" style="fill: var(--paper-sunk); stroke: var(--rule); stroke-width: 1"/>
  <text x="340" y="188" text-anchor="middle">2,741,020</text>
  <rect x="388" y="170" width="72" height="28" rx="4" style="fill: var(--paper-sunk); stroke: var(--rule); stroke-width: 1"/>
  <text x="424" y="188" text-anchor="middle">2,741,021</text>
  <text class="t-small" x="340" y="64" text-anchor="middle">the client's counter</text>
  <text class="t-small" x="340" y="212" text-anchor="middle">the server's counter</text>
  <text class="t-small t-dim" x="220" y="124">nobody has seen this number yet</text>
  <text class="t-small" x="340" y="264" text-anchor="middle">two counters, and neither side has seen the other's starting value</text>
</svg>
```

## Map several facts into fewer messages

Rows align each fact with its destination. Two highlighted connections converge on the middle message, making the contribution visible through the mapping itself.

```svg
<svg viewBox="0 0 680 360" role="img" aria-label="Four facts on the left, three messages on the right, joined by lines. The client's starting number goes to message 1, which travels client to server. The server's starting number and the client's knowledge that its own number arrived both go to message 2, the middle message, which travels server to client and is drawn in the link colour and labelled two facts in one message. The server's knowledge that its number arrived goes to message 3, which travels client to server.">
  <text class="t-small t-dim" x="14" y="26">four facts to carry</text>
  <text class="t-small t-dim" x="368" y="26">three messages to carry them</text>
  <rect x="14" y="46" width="286" height="56" rx="6" style="fill: var(--paper-sunk); stroke: var(--rule)"/>
  <text class="t-strong" x="31" y="78" text-anchor="middle" style="font-size: 14px">1</text>
  <text x="48" y="69">the client's starting number</text><text x="48" y="87">reaches the server</text>
  <rect x="14" y="116" width="286" height="56" rx="6" style="fill: var(--paper-sunk); stroke: var(--rule)"/>
  <text class="t-strong" x="31" y="148" text-anchor="middle" style="font-size: 14px">2</text>
  <text x="48" y="139">the server's starting number</text><text x="48" y="157">reaches the client</text>
  <rect x="14" y="186" width="286" height="56" rx="6" style="fill: var(--paper-sunk); stroke: var(--rule)"/>
  <text class="t-strong" x="31" y="218" text-anchor="middle" style="font-size: 14px">3</text>
  <text x="48" y="209">the client learns</text><text x="48" y="227">its number arrived</text>
  <rect x="14" y="256" width="286" height="56" rx="6" style="fill: var(--paper-sunk); stroke: var(--rule)"/>
  <text class="t-strong" x="31" y="288" text-anchor="middle" style="font-size: 14px">4</text>
  <text x="48" y="279">the server learns</text><text x="48" y="297">its number arrived</text>
  <rect x="368" y="48" width="152" height="52" rx="6" style="fill: var(--paper); stroke: var(--rule)"/>
  <text class="t-strong" x="382" y="69">message 1</text><text x="382" y="86">client to server</text>
  <rect x="368" y="153" width="152" height="52" rx="6" style="fill: var(--paper); stroke: var(--link); stroke-width: 1.5"/>
  <text class="t-strong" x="382" y="174">message 2</text><text x="382" y="191">server to client</text>
  <rect x="368" y="258" width="152" height="52" rx="6" style="fill: var(--paper); stroke: var(--rule)"/>
  <text class="t-strong" x="382" y="279">message 3</text><text x="382" y="296">client to server</text>
  <text class="t-small" x="528" y="174" style="fill: var(--link); font-weight: 600">two facts</text>
  <text class="t-small" x="528" y="191" style="fill: var(--link); font-weight: 600">in one message</text>
  <line x1="300" y1="74" x2="368" y2="74" style="stroke: var(--rule-strong); stroke-width: 1.25"/><circle cx="368" cy="74" r="2.2" style="fill: var(--rule-strong)"/>
  <line x1="300" y1="144" x2="368" y2="167" style="stroke: var(--link); stroke-width: 1.5"/><circle cx="368" cy="167" r="2.4" style="fill: var(--link)"/>
  <line x1="300" y1="214" x2="368" y2="191" style="stroke: var(--link); stroke-width: 1.5"/><circle cx="368" cy="191" r="2.4" style="fill: var(--link)"/>
  <line x1="300" y1="284" x2="368" y2="284" style="stroke: var(--rule-strong); stroke-width: 1.25"/><circle cx="368" cy="284" r="2.2" style="fill: var(--rule-strong)"/>
  <text class="t-small" x="14" y="342">the first message has nothing yet to acknowledge, and the last carries only that acknowledgement</text>
</svg>
```

## Track values across a request and reply

Keep endpoint identities stable and show the source/destination roles exchanging. Highlight the same port numbers at both stages so the reader sees what changes and what is preserved.

```svg
<svg viewBox="0 0 680 360" role="img" aria-label="A laptop and a server exchange a request and a reply. The request from 192.168.1.24:51820 to 203.0.113.9:443 carries four values, two for each endpoint. The reply carries the same four values with the endpoints exchanged, so the client port 51820 comes back as the destination port of the reply.">
  <rect x="16" y="32" width="156" height="296" rx="10" style="fill: var(--paper-sunk); stroke: var(--rule)"/>
  <rect x="508" y="32" width="156" height="296" rx="10" style="fill: var(--paper-sunk); stroke: var(--rule)"/>
  <text class="t-strong" x="94" y="64" text-anchor="middle">laptop</text><text x="94" y="84" text-anchor="middle">192.168.1.24</text>
  <text class="t-strong" x="586" y="64" text-anchor="middle">server</text><text x="586" y="84" text-anchor="middle">203.0.113.9</text>
  <rect x="26" y="154" width="136" height="68" rx="8" style="fill: var(--paper); stroke: var(--rule)"/>
  <text class="t-small" x="94" y="184" text-anchor="middle">browser socket</text>
  <text class="t-strong" x="94" y="212" text-anchor="middle" style="fill: var(--link); font-size: 14px">51820</text>
  <rect x="518" y="154" width="136" height="68" rx="8" style="fill: var(--paper); stroke: var(--rule)"/>
  <text class="t-small" x="586" y="184" text-anchor="middle">web program socket</text>
  <text class="t-strong" x="586" y="212" text-anchor="middle" style="fill: var(--link); font-size: 14px">443</text>
  <text x="340" y="52" text-anchor="middle">request</text>
  <line x1="176" y1="68" x2="500" y2="68" style="stroke: var(--link); stroke-width: 2"/>
  <path d="M 496 62 L 508 68 L 496 74 Z" style="fill: var(--link)"/>
  <rect x="176" y="90" width="160" height="50" rx="8" style="fill: var(--paper-sunk); stroke: var(--rule-strong)"/>
  <text class="t-small" x="256" y="108" text-anchor="middle">SRC</text>
  <text x="256" y="130" text-anchor="middle">192.168.1.24<tspan class="t-strong" style="fill: var(--link)">:51820</tspan></text>
  <rect x="344" y="90" width="160" height="50" rx="8" style="fill: var(--paper-sunk); stroke: var(--rule-strong)"/>
  <text class="t-small" x="424" y="108" text-anchor="middle">DST</text>
  <text x="424" y="130" text-anchor="middle">203.0.113.9<tspan class="t-strong" style="fill: var(--link)">:443</tspan></text>
  <rect x="176" y="208" width="160" height="50" rx="8" style="fill: var(--paper-sunk); stroke: var(--rule-strong)"/>
  <text class="t-small" x="256" y="226" text-anchor="middle">DST</text>
  <text x="256" y="248" text-anchor="middle">192.168.1.24<tspan class="t-strong" style="fill: var(--link)">:51820</tspan></text>
  <rect x="344" y="208" width="160" height="50" rx="8" style="fill: var(--paper-sunk); stroke: var(--rule-strong)"/>
  <text class="t-small" x="424" y="226" text-anchor="middle">SRC</text>
  <text x="424" y="248" text-anchor="middle">203.0.113.9<tspan class="t-strong" style="fill: var(--link)">:443</tspan></text>
  <text class="t-small" x="311" y="178">same number, moved</text>
  <line x1="299" y1="144" x2="299" y2="204" style="stroke: var(--link); stroke-width: 1.5"/>
  <circle cx="299" cy="144" r="2.2" style="fill: var(--link)"/><circle cx="299" cy="204" r="2.2" style="fill: var(--link)"/>
  <line x1="464" y1="144" x2="464" y2="204" style="stroke: var(--link); stroke-width: 1.5"/>
  <circle cx="464" cy="144" r="2.2" style="fill: var(--link)"/><circle cx="464" cy="204" r="2.2" style="fill: var(--link)"/>
  <line x1="504" y1="286" x2="186" y2="286" style="stroke: var(--link); stroke-width: 2"/>
  <path d="M 184 280 L 172 286 L 184 292 Z" style="fill: var(--link)"/>
  <text x="340" y="302" text-anchor="middle">reply</text>
</svg>
```

## Construction documentation

Use the [W3Schools SVG reference](https://www.w3schools.com/graphics/svg_reference.asp) as a source for concise notes on supported shapes, paths, text/tspans, groups, and paint attributes. Verify behaviour with rendered fixtures. Preserve attribution in the production guide. Model requests receive the selected notes and examples directly, without a browsing step.

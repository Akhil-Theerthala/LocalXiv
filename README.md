<p align="center">
  <img src="app/assets/icon.png" alt="LocalXiv logo" width="112">
</p>

# LocalXiv

Read arXiv papers comfortably. On your Mac or Kindle.

LocalXiv turns arXiv and alphaXiv links into a paper library on your Mac. Adjust the reading layout, explore optional visual explanations, and export an EPUB for your Kindle. Keep the original paper beside the explanation so you can check what it actually says.

**[Download v0.0.17 for Mac](https://github.com/Akhil-Theerthala/LocalXiv/releases/tag/v0.0.17)** · Apple Silicon · macOS 26 or newer

Free and open source. No AI account is needed to import, read, or export papers. Optional AI features use your own provider and API key.

## From a paper link to a reading session

- Paste an arXiv or alphaXiv link, or search by title, author, or topic, and save the paper to your local library.
- Read with your choice of font, text size, line length, line spacing, and a Light, Sepia, or Dark theme, including rendered equations.
- Hover a citation, figure, table, or equation to see it where you are reading. Click it to go there, and press **Back** to return to the same paragraph.
- Pick up where you stopped. Each paper reopens at its view, chapter, and paragraph, and the Library shows which papers are new, in progress, or read.
- Use an **Overview** to explore a paper visually, or a **Blog** for a longer explanation whose citations show the passage they come from.
- Export the paper or an available explanation as an EPUB, or send it to Kindle through Apple Mail.

The app includes *Attention Is All You Need* with a saved Overview and Blog. You can explore that example before connecting an AI provider.

<details>
<summary>See a figure from the included example</summary>

<p align="center">
  <img src="docs/attention_figure.png" alt="Generated three-panel Overview of the Transformer encoder, multi-head attention, and decoder from Attention Is All You Need" width="680">
</p>

This is a generated illustration, not a figure authored by the paper's researchers. It was generated on 2026-09-18 by the Overview workflow through the figure library with deepseek-flash in five requests, at 63 text runs per million square units. The bundled sample's saved Overview is older; see its [source and generation provenance](app/sample/attention/README.md).

</details>

LocalXiv is an early preview. Conversion can be imperfect, and AI explanations can contain mistakes even after automated review.

## Start reading

1. Download a DMG from the releases page and drag **LocalXiv** into **Applications**.
2. Open LocalXiv and paste an arXiv or alphaXiv link.
3. Open the saved paper. Click **Aa** in the toolbar to change the font, text size, line length, line spacing, and theme.

The packaged app includes its conversion tools. You do not need Homebrew, Python, or an AI account to import and read papers.

The current public preview is ad hoc signed and is not notarized by Apple. macOS may block the first launch. See the [installation and update instructions](docs/macos-release.md) and the notes attached to your downloaded release.

Conversion is imperfect, especially for unusual equations, tables, and layouts. LocalXiv retains the original paper and can fall back to it when EPUB conversion fails.

## Understand a paper

The reader separates the retained paper from generated explanations:

| View | What it provides |
| --- | --- |
| **Paper** | The retained paper, with adjustable reading settings. |
| **Overview** | A visual explanation of the contribution, mechanism, and evidence. |
| **Blog** | A longer explanation with source citations and optional focused drawings. |

Generated explanations are aids to reading. Check important claims against the source: each Blog citation shows its passage when you hover it, and on a wide window it opens the Paper beside the explanation. Every Overview and Blog names the model that made it and the date. Generation may take several minutes or fail, and support varies by provider and model.

To enable AI, choose **LocalXiv → Settings… → AI**, choose a provider, enter a model and API key, then click **Test Connection** and **Save**. Presets are available for OpenAI, OpenRouter, DeepSeek, Gemini, and Anthropic. **Custom** accepts other compatible API endpoints; compatibility is not guaranteed for every model.

Overview generation after import is opt-in. Blog generation is manual and works without an existing Overview. Blog figures are laid out by the application from a model-authored Scene panel, the same way the Overview is; a figure that still fails after bounded corrections is omitted. Language and length settings control the explanation.

An Overview is one dense column of up to four panels. The model extracts a digest of the paper and a scene tree of cards, groups, grids, steps, and bars; the application lays the scene out and routes the arrows. See the [Overview scene layout design](docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md).

## Read on Kindle

Open **Share** in the toolbar to export an EPUB, or choose **Send to Kindle…** to send through Apple Mail. You can choose the paper or an available generated explanation.

For Mail delivery, add your Send-to-Kindle email in **Settings → Kindle**, configure Apple Mail, and approve your sending address in your Amazon account. Confirm delivery on the Kindle itself.

## Your library and AI connection

- Papers and settings are stored under `~/Library/Application Support/LocalXiv/library`.
- Removing the app leaves the library in place. Removing a paper inside LocalXiv deletes its retained files and associated explanations. Previously exported copies remain.
- API keys are stored in macOS Keychain. AI requests use your configured provider and may incur that provider's charges.
- AI generation sends selected paper content to the provider.
- Importing papers requires network access. Reading saved papers and exporting their EPUBs do not require AI credentials.

## Built with GPT-6 Astra in Codex

LocalXiv was developed primarily with GPT-6 Astra in Codex. That work spans the Mac reader, paper conversion and export, AI explanation workflows, tests, and release tooling. This repository contains the implementation and [recorded verification work](docs/verification/2026-09-16-svg-reliability.md).

For visitors from the [Product Hunt GPT-6 Astra Challenge](https://www.producthunt.com/contests/gpt-6-astra-challenge), Astra's role is in building LocalXiv. The model used inside the app is selected separately in **Settings → AI**. You can use the reading and export workflow without connecting any model.

## Development

The desktop app uses a native AppKit window (sidebar, toolbar, menus, and a Settings window) around a WebKit reader, and a local Python service. SQLite stores the library and job records. Conversion and AI generation run as separate jobs, so a failed explanation does not invalidate a retained paper.

See [development setup and checks](docs/development.md) and [macOS release tooling](docs/macos-release.md). The included sample has its own [source and generation provenance](app/sample/attention/README.md); it is not evidence that every new generation will succeed.

To report a problem, [open an issue](https://github.com/Akhil-Theerthala/LocalXiv/issues) with your app version, macOS version, paper link, and the step that failed. For AI failures, include the provider and model, but never an API key.

## License

LocalXiv's original code is licensed under [AGPL-3.0-or-later](LICENSE). Third-party components retain their own licenses, listed in [NOTICE](NOTICE) and [dependency licenses](docs/dependency-licenses.md).

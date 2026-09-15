<p align="center">
  <img src="app/assets/icon.png" alt="LocalXiv logo" width="112">
</p>

# LocalXiv

Read arXiv papers on your Mac. Take them to your Kindle.

LocalXiv turns arXiv and alphaXiv links into a local paper library with adjustable typography, rendered equations, and EPUB export. Optional AI features provide visual overviews, longer explanations, and answers to questions about a paper.

**[Download for Mac](https://github.com/Akhil-Theerthala/LocalXiv/releases)** · Apple Silicon · macOS 26 or newer

LocalXiv is an early preview. This branch contains work toward v0.0.11; use the releases page for published builds. AI explanations are experimental and can contain mistakes even after automated review.

## Start reading

1. Download a DMG from the releases page and drag **LocalXiv** into **Applications**.
2. Open LocalXiv and paste an arXiv or alphaXiv link.
3. Open the saved paper. Adjust the font, text size, margins, and appearance to suit your reading.

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

You can also ask questions about the paper. Generated explanations and answers are aids to reading; check important claims against the source. Generation may take several minutes or fail, and support varies by provider and model.

To enable AI, open **Settings → AI connection**, choose a provider, enter a model and API key, then test and save the connection. Presets are available for OpenAI, OpenRouter, DeepSeek, and Gemini. **Custom** accepts other compatible API endpoints; compatibility is not guaranteed for every model.

Overview generation after import is opt-in. Blog generation is manual and works without an existing Overview. The v0.0.11 workflow draws focused Blog figures separately; an unsuccessful drawing may be omitted after bounded repair attempts. Language and length settings control the explanation.

## Read on Kindle

Open **Share** to export an EPUB, or expand **Send to Kindle** to send through Apple Mail. You can choose the paper or an available generated explanation.

For Mail delivery, add your Kindle email in **Settings → Kindle delivery**, configure Apple Mail, and approve your sending address in your Amazon account. Confirm delivery on the Kindle itself.

## Your library and AI connection

- Papers and settings are stored under `~/Library/Application Support/LocalXiv/library`.
- Removing the app leaves the library in place. Removing a paper inside LocalXiv deletes its retained files and associated explanations and chat history; previously exported copies remain.
- API keys are stored in macOS Keychain. AI requests use your configured provider and may incur that provider's charges.
- AI generation and questions send selected paper content to the provider. Image-enabled workflows can also send paper figures and generated drawings. Related-paper recommendations use the provider too.
- Importing papers requires network access. Reading saved papers and exporting their EPUBs do not require AI credentials.

## Development

LocalXiv was developed primarily with GPT-6 Astra in Codex. The model used inside the app is selected separately in AI settings.

The desktop app uses a Swift/AppKit launcher, a WebKit reader, and a local Python service. SQLite stores the library and job records. Conversion and AI generation run as separate jobs, so a failed explanation does not invalidate a retained paper.

| Area | Start here |
| --- | --- |
| App requests and jobs | [app/server.py](app/server.py) |
| Library and saved generations | [papers/library.py](papers/library.py) |
| Import and conversion recovery | [papers/convert.py](papers/convert.py) |
| Retained source selection | [papers/reading.py](papers/reading.py) |
| Overview generation | [papers/overview_workflow.py](papers/overview_workflow.py) |
| Blog generation | [papers/agent_overviews.py](papers/agent_overviews.py) |
| Figure authoring and validation | [papers/panel_authoring.py](papers/panel_authoring.py), [papers/html_figures.py](papers/html_figures.py) |

See [development setup and checks](docs/development.md), [macOS release tooling](docs/macos-release.md), and the [Blog workflow status and pilot limitations](docs/blog_refactor.md). The included sample has its own [source and generation provenance](app/sample/attention/README.md); it is not evidence that every new generation will succeed.

To report a problem, [open an issue](https://github.com/Akhil-Theerthala/LocalXiv/issues) with your app version, macOS version, paper link, and the step that failed. For AI failures, include the provider and model, but never an API key.

## License

LocalXiv's original code is licensed under [AGPL-3.0-or-later](LICENSE). Third-party components retain their own licenses, listed in [NOTICE](NOTICE) and [dependency licenses](docs/dependency-licenses.md).

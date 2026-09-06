# Run LocalXiv from source

Use an Apple Silicon Mac with macOS 26 or newer for the current release build. Install Homebrew before you begin.

1. Install Apple Command Line Tools if they are missing:

```sh
xcode-select --install
```

2. Clone the repository:

```sh
git clone https://github.com/Akhil-Theerthala/LocalXiv.git
cd LocalXiv
```

3. Install the conversion tools:

```sh
brew install python@3.14 pandoc latexml librsvg ghostscript epubcheck node
```

4. Install the locked JavaScript dependencies:

```sh
npm ci --ignore-scripts --omit=dev
```

5. Build and install the development app:

```sh
./install-app.sh
```

6. Open the installed app:

```sh
open "$HOME/Applications/LocalXiv.app"
```

The development installer copies the runtime code into `~/Library/Application Support/LocalXiv/app`. Run the installer again after source changes. Let active jobs finish and stop the old background service before replacing its code.

To test the reader without installing the native app, start an isolated library:

```sh
python3 -m app.server --port 8765 --data-dir /tmp/localxiv-dev --open
```

Keep release builds separate from the development install. Follow [Build and publish a macOS DMG](macos-release.md) to create a portable app.

# LocalXiv intro video

A 48-second 1920x1080 video that introduces LocalXiv with real app screenshots. [Remotion](https://www.remotion.dev) animates it.

## Render

Run these commands in `tools/intro-video`. The repository `.venv` must exist.

```bash
npm install
npx remotion browser ensure
node capture.mjs
npm run render
```

`capture.mjs` starts a temporary LocalXiv server with the bundled sample paper, then saves screenshots to `public/`. It makes no AI provider call, and it does not touch your library or Keychain. The script changes the settings reply in its own browser, so the saved Overview and Blog tabs show.

`npm run render` writes `dist/intro-video/localxiv-intro.mp4`. Run `npm run studio` to preview and edit the timeline.

## Edit

`src/Intro.jsx` holds the whole video. `SHOTS` sets the screenshot order, timing, and camera zoom. `CAPTIONS` sets the text above the window.

## License

Remotion is free for individuals and small companies. Larger companies need a company license. See [remotion.dev/license](https://www.remotion.dev/license).

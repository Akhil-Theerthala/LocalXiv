# LocalXiv intro video

A 44-second 1920x1080 video at 60 fps that introduces LocalXiv with real app screenshots and its own music. [Remotion](https://www.remotion.dev) animates it.

## Render

Run these commands in `tools/intro-video`. The repository `.venv` and the root `node_modules` must exist, because the capture runs the app.

```bash
npm install
npx remotion browser ensure
node capture.mjs
node music.mjs
npm run render
```

`capture.mjs` starts a temporary LocalXiv server with the bundled sample paper, then saves screenshots and element positions to `public/`. It makes no AI provider call, and it does not touch your library or Keychain. The script changes the settings reply in its own browser, so the saved Overview and Blog tabs show.

`music.mjs` synthesizes `public/music.wav` from code. It uses no samples or recordings, so the music needs no license.

`npm run render` writes `dist/intro-video/localxiv-intro.mp4`. Run `npm run studio` to preview the video and each scene on its own.

## Edit

`src/timeline.mjs` holds the beat grid that the video and the music share: 120 BPM, the length of each scene in beats, and the beats of cues such as the Add paper click. Change a scene length or a cue there, then run `node music.mjs` again so the sound stays on the picture.

| File | Contents |
| --- | --- |
| `src/Intro.jsx` | The full video: background, captions, window, e-reader, end card, and music. |
| `src/stage.jsx` | The app window, its layout for each scene, and the in-window camera. |
| `src/brand.jsx` | Colours, fonts, easing, the animated icon, and captions. |
| `src/scenes/` | One file for each scene. |

## License

Remotion is free for individuals and small companies. Larger companies need a company license. See [remotion.dev/license](https://www.remotion.dev/license).

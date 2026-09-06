# Native window and activity history

Date: 2026-09-06.

The previous app bundle executed a shell launcher that called Python's `webbrowser.open`. Safari opened because it was the default browser. The job panel rendered the most recent six jobs without separating completed work, so repeated import checks remained as permanent cards.

The installed bundle now contains an arm64 Mach-O executable compiled from `app/macos/PapersToKindle.swift`. It owns an AppKit window, application menu, and WebKit view. It starts or reuses the existing authenticated loopback service and opens the same local library. The source converter and provider settings are unchanged. Explicit external links can open the default browser; launching the application does not use Safari.

Successful and cancelled jobs appear in collapsed Recent activity. Running, failed, and interrupted jobs remain visible. Opening the history preserves access to previous export links. A newly requested export starts its download once when ready, without replaying historical downloads on launch or polling.

The native wrapper implements WebKit download delegates and a native Save dialog. A download writes to a new temporary file beside the destination and replaces an existing file only after successful completion. The API contract follows Apple's [download destination documentation](https://developer.apple.com/documentation/webkit/wkdownloaddelegate/download(_:decidedestinationusing:suggestedfilename:completionhandler:)) and [navigation-to-download callback](https://developer.apple.com/documentation/webkit/wknavigationdelegate/webview(_:navigationresponse:didbecome:)).

## Verification

- Swift compiled successfully for macOS 11.3 or newer; the installed executable was verified as Mach-O arm64 and the bundle was locally signed.
- 19 Python tests passed for launch routing, local handoff, HTTP boundaries, jobs, and real EPUB export behavior.
- All 64 JavaScript tests passed, with added assertions for collapsed history, visible active/failing jobs, same-origin download links, and exactly-once downloads for newly requested exports.
- Shell syntax and `git diff --check` passed.
- Opened the actual installed native app using UI automation. Its own app/window identity, two-paper library, compact activity row, existing overview, and embedded paper reader were observed. No new model request or Mail submission was made.
- An existing paper export completed inside the native app. Final end-to-end Save-dialog/file-destination verification was not completed because the user was interacting with the window; controls were left with the user. The updated automatic-download UI loads when the app is reopened.

The background local service stays available after the window/app closes so pending jobs can finish. No login item or launch daemon is installed.

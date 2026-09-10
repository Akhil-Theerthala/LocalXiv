import AppKit
import WebKit

// Local, script-free HTML rasterization. Only our measurement script runs in WebKit.
@MainActor final class Snapshot: NSObject, WKNavigationDelegate {
    let output: String
    let web: WKWebView
    let window: NSWindow
    init(input: String, output: String) {
        self.output = output
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        config.defaultWebpagePreferences.allowsContentJavaScript = false
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: 960, height: 800), configuration: config)
        window = NSWindow(contentRect: web.frame, styleMask: .borderless, backing: .buffered, defer: false)
        super.init()
        window.contentView = web
        web.navigationDelegate = self
        do { web.loadHTMLString(try String(contentsOfFile: input, encoding: .utf8), baseURL: nil) }
        catch { fail(error.localizedDescription) }
    }
    func fail(_ message: String) -> Never { fputs(message + "\n", stderr); exit(1) }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { fail(error.localizedDescription) }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { fail(error.localizedDescription) }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        let js = """
        (() => {
          const root=document.querySelector('main'), issues=[], texts=[];
          const frame=root.getBoundingClientRect();
          for(const e of root.querySelectorAll('*')) {
            if(['title','desc','defs','marker'].includes(e.tagName.toLowerCase())) continue;
            const r=e.getBoundingClientRect();
            if(r.width && (r.left < -1 || r.right > 961)) issues.push('Outside page: '+e.textContent.slice(0,80));
            if(e.tagName.toLowerCase()==='text') {
              const s=e.closest('svg').getBoundingClientRect();
              if(r.left<s.left-1 || r.right>s.right+1 || r.top<s.top-1 || r.bottom>s.bottom+1) issues.push('SVG text clipped: '+e.textContent);
              if(parseFloat(getComputedStyle(e).fontSize)*s.width/e.closest('svg').viewBox.baseVal.width < 14) issues.push('Small text: '+e.textContent);
              texts.push({r,text:e.textContent});
            }
          }
          for(let i=0;i<texts.length;i++) for(let j=i+1;j<texts.length;j++) {
            const a=texts[i].r,b=texts[j].r;
            if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2 && Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2) issues.push('Overlapping text: '+texts[i].text+' / '+texts[j].text);
          }
          return {width:960,height:Math.ceil(frame.bottom),issues:[...new Set(issues)]};
        })()
        """
        web.evaluateJavaScript(js) { value, error in
            if let error { self.fail(error.localizedDescription) }
            guard let checks = value as? [String: Any], let height = checks["height"] as? Double, height > 0, height <= 6000 else { self.fail("Invalid render dimensions") }
            do { try JSONSerialization.data(withJSONObject: checks).write(to: URL(fileURLWithPath: self.output + ".checks.json")) }
            catch { self.fail(error.localizedDescription) }
            self.web.setFrameSize(NSSize(width: 960, height: height))
            let shot = WKSnapshotConfiguration()
            shot.rect = NSRect(x: 0, y: 0, width: 960, height: height)
            shot.snapshotWidth = 1920
            self.web.takeSnapshot(with: shot) { image, error in
                guard let tiff=image?.tiffRepresentation, let bitmap=NSBitmapImageRep(data:tiff), let png=bitmap.representation(using:.png, properties:[:]) else { self.fail(error?.localizedDescription ?? "Snapshot failed") }
                do { try png.write(to: URL(fileURLWithPath:self.output + ".png")) } catch { self.fail(error.localizedDescription) }
                let pdf=WKPDFConfiguration(); pdf.rect=shot.rect
                self.web.createPDF(configuration:pdf) { result in
                    do { try result.get().write(to: URL(fileURLWithPath:self.output + ".pdf")); exit(0) }
                    catch { self.fail(error.localizedDescription) }
                }
            }
        }
    }
}
MainActor.assumeIsolated {
    let application = NSApplication.shared
    application.setActivationPolicy(.prohibited)
    guard CommandLine.arguments.count == 3 else { exit(2) }
    let renderer = Snapshot(input:CommandLine.arguments[1], output:CommandLine.arguments[2])
    DispatchQueue.main.asyncAfter(deadline:.now()+45) { renderer.fail("Rendering timed out") }
    withExtendedLifetime(renderer) { application.run() }
}

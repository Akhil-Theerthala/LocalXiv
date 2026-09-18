import AppKit
import WebKit

// Local, script-free HTML rasterization. Only our measurement script runs in WebKit.
//
// Two measurement modes share this binary. `localxiv-render-mode` `measure` reports rendered
// text widths. Any other mode declares a content-sized SVG canvas: the renderer resolves its
// intrinsic size, rescales it to `localxiv-display-width` when that meta tag is present,
// measures and renders at 1:1 display units, and tiles the raster when it is large.
@MainActor final class Snapshot: NSObject, WKNavigationDelegate {
    let output: String
    let web: WKWebView
    let window: NSWindow
    // Raster resource bounds. Above either bound the page is captured as tiles at the same
    // scale and assembled in AppKit; text is never downsampled to fit.
    let maximumRasterPixels = 32_000_000.0
    let maximumDimension = 8192.0
    let tileSize = 2048.0
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

    func write(_ checks: [String: Any]) {
        do { try JSONSerialization.data(withJSONObject: checks).write(to: URL(fileURLWithPath: self.output + ".checks.json")) }
        catch { fail(error.localizedDescription) }
    }

    func png(_ image: NSImage) -> Data? {
        guard let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff) else { return nil }
        bitmap.size = image.size
        return bitmap.representation(using: .png, properties: [:])
    }

    // One image from one snapshot call at an explicit device scale.
    func capture(_ rect: NSRect, scale: Double, completion: @escaping (CGImage?) -> Void) {
        let shot = WKSnapshotConfiguration()
        shot.rect = rect
        shot.snapshotWidth = NSNumber(value: rect.width * scale)
        web.takeSnapshot(with: shot) { image, error in
            _ = error
            completion(image?.cgImage(forProposedRect: nil, context: nil, hints: nil))
        }
    }

    func writePDF(_ rect: NSRect, then: @escaping () -> Void) {
        let pdf = WKPDFConfiguration()
        pdf.rect = rect
        web.createPDF(configuration: pdf) { result in
            do { try result.get().write(to: URL(fileURLWithPath: self.output + ".pdf")) }
            catch { self.fail(error.localizedDescription) }
            then()
        }
    }

    // Content-sized page: measure the SVG canvas, then rasterize it whole, or as tiles at the
    // same scale when one allocation would exceed the safe raster bounds.
    func captureCanvas(mode: String) {
        let js = """
        (() => {
          const mode='\(mode)';
          const main=document.querySelector('main'), svg=main.querySelector('svg');
          const vb=(svg.getAttribute('viewBox')||'').trim().split(/[\\s,]+/).map(Number);
          let width=(vb.length===4 && vb[2]>0) ? vb[2] : 0, height=(vb.length===4 && vb[3]>0) ? vb[3] : 0;
          if(!width||!height){const r=svg.getBoundingClientRect();width=r.width;height=r.height;}
          // A page may declare the width the reader sees. Only the display size changes: the
          // authored viewBox and every drawn coordinate keep their value, so the
          // getScreenCTM()-based text measurements below report the real displayed size.
          const display=parseFloat(document.querySelector('meta[name="localxiv-display-width"]')?.content);
          if(display>0){height=height*display/width;width=display;}
          svg.style.width=width+'px'; svg.style.height=height+'px';
          svg.setAttribute('width',width); svg.setAttribute('height',height);
          const frame=svg.getBoundingClientRect(), issues=[], issueDetails=[], texts=[], textRuns=[], elements=[];
          const counts=new Map();
          const location=e=>{
            if(e.id) return '#'+e.id;
            const tag=e.tagName.toLowerCase(), count=(counts.get(tag)||0)+1;
            counts.set(tag,count);
            return '/svg/'+tag+'['+count+']';
          };
          const add=(code,path,message,constraint,actual,limit)=>{
            issues.push(message);
            issueDetails.push({code,path,message,constraint,actual,limit});
          };
          const markerBounds=e=>{
            const reference=e.getAttribute('marker-start') || e.getAttribute('marker-end');
            const match=reference?.match(/^url\\(#([A-Za-z_][A-Za-z0-9_.:-]*)\\)$/);
            const marker=match && document.getElementById(match[1]);
            if(!marker || typeof e.getTotalLength!=='function') return null;
            try {
              const atStart=Boolean(e.getAttribute('marker-start'));
              const point=e.getPointAtLength(atStart ? 0 : e.getTotalLength()).matrixTransform(e.getScreenCTM());
              const matrix=e.getScreenCTM(), transformScale=Math.max(Math.hypot(matrix.a,matrix.b),Math.hypot(matrix.c,matrix.d));
              const units=marker.getAttribute('markerUnits')==='userSpaceOnUse' ? 1 : parseFloat(getComputedStyle(e).strokeWidth)||1;
              const extent=Math.max(parseFloat(marker.getAttribute('markerWidth'))||3,
                parseFloat(marker.getAttribute('markerHeight'))||3)*units*transformScale;
              return {left:point.x-extent,right:point.x+extent,top:point.y-extent,bottom:point.y+extent};
            } catch (_) { return null; }
          };
          const visualBounds=e=>{
            try {
              const box=e.getBBox({fill:true,stroke:true,markers:true}), matrix=e.getScreenCTM();
              const points=[[box.x,box.y],[box.x+box.width,box.y],[box.x,box.y+box.height],
                [box.x+box.width,box.y+box.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(matrix));
              const bounds={left:Math.min(...points.map(p=>p.x)),right:Math.max(...points.map(p=>p.x)),
                top:Math.min(...points.map(p=>p.y)),bottom:Math.max(...points.map(p=>p.y))};
              const marker=markerBounds(e);
              if(marker) return {left:Math.min(bounds.left,marker.left),right:Math.max(bounds.right,marker.right),
                top:Math.min(bounds.top,marker.top),bottom:Math.max(bounds.bottom,marker.bottom)};
              return bounds;
            } catch (_) { return e.getBoundingClientRect(); }
          };
          for(const e of svg.querySelectorAll('*')) {
            const tag=e.tagName.toLowerCase();
            if(['title','desc','defs','marker'].includes(tag) || e.closest('defs,marker')) continue;
            const shape=['rect','circle','ellipse','line','polyline','polygon','path'].includes(tag);
            if(!shape && tag!=='text') continue;
            const r=shape ? visualBounds(e) : e.getBoundingClientRect();
            const path=location(e);
            elements.push({path,tag,left:r.left-frame.left,top:r.top-frame.top,
              right:r.right-frame.left,bottom:r.bottom-frame.top});
            if((r.width || shape) && (r.left < frame.left-1 || r.right > frame.right+1 || r.top < frame.top-1 || r.bottom > frame.bottom+1)) {
              const overflow=Math.max(frame.left-r.left,r.right-frame.right,frame.top-r.top,r.bottom-frame.bottom,0);
              add('out_of_bounds',path,'Outside the panel canvas: '+(e.textContent||'').slice(0,80),
                'maximum_canvas_overflow_px',overflow,0);
            }
            if(tag==='text') {
              // Canvas units are the authored units: the composed overview carries its own
              // panel scale, so the measured size here is the size a reader sees at 100%.
              for(const run of [e,...e.querySelectorAll('tspan')]) {
                if(![...run.childNodes].some(n=>n.nodeType===Node.TEXT_NODE && n.textContent.trim())) continue;
                const matrix=run.getScreenCTM();
                const sourceSize=parseFloat(getComputedStyle(run).fontSize);
                const transformScale=Math.hypot(matrix.c,matrix.d);
                const size=sourceSize*transformScale;
                const runPath=run===e ? path : location(run);
                textRuns.push({path:runPath,displayed_size_px:size,text:run.textContent.trim()});
                if(size < 14) {
                  const required=Math.ceil(14/Math.max(1e-6,transformScale)*2)/2;
                  add('text_too_small',runPath,'Small text in the panel canvas ('+size.toFixed(1)+
                    ' units; minimum 14): '+run.textContent+'. Raise its source font size from '+sourceSize+
                    ' to at least '+required+' units, or use fewer labels.',
                    'minimum_displayed_font_px',size,14);
                }
              }
              texts.push({r,text:e.textContent,path,scale:Math.hypot(e.getScreenCTM()?.c||1,e.getScreenCTM()?.d||0)||1,
                user_width:(()=>{try{return e.getBBox().width}catch(_){return r.width}})()});
            }
          }
          const containers=[...svg.querySelectorAll('rect')]
            .map(e=>({e,r:e.getBoundingClientRect()}))
            .filter(item=>item.r.width>=12 && item.r.height>=12);
          for(const item of texts) {
            const cx=(item.r.left+item.r.right)/2, cy=(item.r.top+item.r.bottom)/2;
            const inside=containers.filter(c=>cx>=c.r.left && cx<=c.r.right && cy>=c.r.top && cy<=c.r.bottom);
            if(!inside.length) continue;
            const container=inside.reduce((a,b)=>a.r.width*a.r.height<=b.r.width*b.r.height?a:b);
            const overflow=Math.max(container.r.left-item.r.left,item.r.right-container.r.right,
              container.r.top-item.r.top,item.r.bottom-container.r.bottom,0);
            if(overflow>2) add('out_of_bounds',item.path,
              'Label is '+item.user_width.toFixed(0)+' units wide but its container '
              +location(container.e)+' is '+(container.r.width/item.scale).toFixed(0)+' units wide. '
              +'It escapes by '+overflow.toFixed(1)+'px: '+item.text
              +'. Widen the container by about '+(item.user_width-container.r.width/item.scale).toFixed(0)
              +' units, shorten the label, or wrap it into tspan lines that each fit.',
              'maximum_text_container_overflow_px',overflow,2);
          }
          for(let i=0;i<texts.length;i++) for(let j=i+1;j<texts.length;j++) {
            const a=texts[i].r,b=texts[j].r;
            const width=Math.min(a.right,b.right)-Math.max(a.left,b.left);
            const height=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
            const shorterWidth=Math.min(a.width,b.width), shorterHeight=Math.min(a.height,b.height);
            if(width>0.3*shorterWidth && height>0.3*shorterHeight)
              add('text_overlap',texts[i].path+'|'+texts[j].path,'Overlapping text: '+texts[i].text+' / '+texts[j].text,'maximum_text_overlap_area_px2',width*height,0);
          }
          return {mode:mode,width:width,height:height,canvas:{width:width,height:height},
            reading_width:0,reading_scale:1,minimum_label_px:14,text_runs:textRuns,elements:elements,
            issues:[...new Set(issues)],issue_details:issueDetails};
        })()
        """
        web.evaluateJavaScript(js) { value, error in
            if let error { self.fail(error.localizedDescription) }
            guard let checks = value as? [String: Any], let width = checks["width"] as? Double,
                  let height = checks["height"] as? Double, width > 0, height > 0,
                  width <= 20000, height <= 20000 else { self.fail("Invalid render dimensions") }
            self.write(checks)
            self.web.setFrameSize(NSSize(width: width, height: height))
            let pixels = width * height
            let deviceScale = pixels * 4 <= 16_000_000 ? 2.0 : 1.0
            let tileColumns = Int(ceil(width / self.tileSize)), tileRows = Int(ceil(height / self.tileSize))
            let single = width * deviceScale <= self.maximumDimension && height * deviceScale <= self.maximumDimension
                && pixels * deviceScale * deviceScale <= self.maximumRasterPixels
            if single || tileColumns * tileRows > 64 || width * height <= self.tileSize * self.tileSize {
                self.capture(NSRect(x: 0, y: 0, width: width, height: height), scale: deviceScale) { image in
                    guard let image, let png = self.pngFromCGImage(image) else { self.fail("Snapshot failed") }
                    do { try png.write(to: URL(fileURLWithPath: self.output + ".png")) } catch { self.fail(error.localizedDescription) }
                    self.writePDF(NSRect(x: 0, y: 0, width: width, height: height)) { exit(0) }
                }
                return
            }
            let pixelsWide = Int((width * deviceScale).rounded()), pixelsHigh = Int((height * deviceScale).rounded())
            guard let context = CGContext(data: nil, width: pixelsWide, height: pixelsHigh, bitsPerComponent: 8,
                    bytesPerRow: 0, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { self.fail("Snapshot failed") }
            context.setFillColor(CGColor(gray: 1, alpha: 1))
            context.fill(CGRect(x: 0, y: 0, width: pixelsWide, height: pixelsHigh))
            var pending = tileColumns * tileRows
            for column in 0..<tileColumns { for row in 0..<tileRows {
                let x = Double(column) * self.tileSize, y = Double(row) * self.tileSize
                let tileWidth = min(self.tileSize, width - x), tileHeight = min(self.tileSize, height - y)
                // The web view's snapshot rect counts from the page top; AppKit draws from the bottom.
                let rect = NSRect(x: x, y: y, width: tileWidth, height: tileHeight)
                self.capture(rect, scale: deviceScale) { image in
                    guard let image else { self.fail("Snapshot failed") }
                    context.draw(image, in: CGRect(x: x * deviceScale, y: (height - y - tileHeight) * deviceScale,
                                                   width: tileWidth * deviceScale, height: tileHeight * deviceScale))
                    pending -= 1
                    if pending == 0 {
                        guard let assembled = context.makeImage(),
                              let png = NSBitmapImageRep(cgImage: assembled).representation(using: .png, properties: [:]) else { self.fail("Snapshot failed") }
                        do { try png.write(to: URL(fileURLWithPath: self.output + ".png")) } catch { self.fail(error.localizedDescription) }
                        self.writePDF(NSRect(x: 0, y: 0, width: width, height: height)) { exit(0) }
                    }
                }
            }}
        }
    }

    func pngFromCGImage(_ image: CGImage) -> Data? {
        let representation = NSBitmapImageRep(cgImage: image)
        return representation.representation(using: .png, properties: [:])
    }

    // Text measurement mode: report the rendered width of each labelled span in the same
    // WebKit text stack the rasterizer uses, so application-owned wrapping matches the panel.
    func captureMeasure() {
        let js = """
        (() => {
          const spans=[...document.querySelectorAll('main span')];
          return {mode:'measure',width:0,height:0,
            widths:spans.map(s=>({key:s.dataset.key,width:s.getBoundingClientRect().width})),
            text_runs:[],elements:[],issues:[],issue_details:[]};
        })()
        """
        web.evaluateJavaScript(js) { value, error in
            if let error { self.fail(error.localizedDescription) }
            guard let checks = value as? [String: Any] else { self.fail("Invalid text measurement") }
            self.write(checks)
            exit(0)
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        let js = "document.querySelector('meta[name=\"localxiv-render-mode\"]')?.content || ''"
        web.evaluateJavaScript(js) { value, error in
            if let error { self.fail(error.localizedDescription) }
            let mode = (value as? String) ?? ""
            if mode.isEmpty { self.fail("The page declares no localxiv-render-mode") }
            else if mode == "measure" { self.captureMeasure() }
            else { self.captureCanvas(mode: mode) }
        }
    }
}
MainActor.assumeIsolated {
    let application = NSApplication.shared
    application.setActivationPolicy(.prohibited)
    guard CommandLine.arguments.count == 3 else { exit(2) }
    let renderer = Snapshot(input:CommandLine.arguments[1], output:CommandLine.arguments[2])
    DispatchQueue.main.asyncAfter(deadline:.now()+240) { renderer.fail("Rendering timed out") }
    withExtendedLifetime(renderer) { application.run() }
}

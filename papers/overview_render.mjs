import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {render, wrapText, estimateTextWidth, rect, textEl, arrow} from 'excalidrawer';
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
// Model supplies meaning. Geometry keeps two/three steps in a row and four in a square.
const elements = [];
const metricScales = [];
const illustrationAssets = new Map();
function illustration(asset, id, x, y, w) {
  const h=w*asset.height/asset.width;
  illustrationAssets.set(id,asset);
  return rect(id,x,y,w,h,'transparent',{roughness:0,strokeColor:'transparent'});
}
function text(id,value,x,y,width,size=24,color='#292d23') {
  const wrapped = wrapText(value,width,size), lines = wrapped.split('\n');
  if (lines.some(line => estimateTextWidth(line,size) > width)) throw new Error('Shorten an unbroken label in '+id);
  const height = lines.length*size*1.4;
  elements.push({shape:'text',id,text:wrapped,at:[x,y],size:[width,height],fontSize:size,textColor:color});
  return height;
}
try {
  if (spec.layout === 'bento') {
    // Stage 3: fit text before placing cards; every row closes without holes.
    const width = spec.packing.orientation === 'portrait' ? 420 : 1120, gap = 16, pad = 28;
    let y = 16;
    function measure(value, w, size) {
      const wrapped = wrapText(value, w, size);
      if (wrapped.split('\n').some(line => estimateTextWidth(line,size)>w)) throw new Error('Unbreakable bento text: '+value+' at width '+w);
      return {value:wrapped, height:wrapped.split('\n').length*size*1.4, size};
    }
    function visualParts(visual, w, id) {
      if (!visual) return {elements:[], height:0};
      const parts=[];
      function addText(suffix, value, x, y, tw, size=20) {
        const t=measure(value,tw,size);
        parts.push(textEl(id+suffix,x,y,tw,t.height,t.value,size,{fontFamily:2,textAlign:'left',strokeColor:'#3d5130',roughness:0}));
        return t.height;
      }
      let bottom=0;
      if (visual.kind==='illustration') {
        const part=illustration(visual._asset,id+'image',0,0,w);
        parts.push(part);
        bottom=part.height;
      } else if (visual.kind==='flow') {
        const gap=32, horizontalWidth=(w-gap*(visual.steps.length-1))/visual.steps.length;
        const vertical=w<440 || visual.steps.some(s=>s.split(/\s+/).some(word=>estimateTextWidth(word,20)>horizontalWidth-20));
        const bw=vertical?w:horizontalWidth;
        const bh=Math.max(...visual.steps.map(s=>measure(s,bw-20,20).height))+24;
        visual.steps.forEach((step,i)=>{
          const x=vertical?0:i*(bw+gap), sy=vertical?i*(bh+gap):0;
          parts.push(rect(id+'step'+i,x,sy,bw,bh,'#ffffff',{roughness:0,strokeColor:'#78856d',strokeWidth:1}));
          addText('label'+i,step,x+10,sy+12,bw-20);
          if (i) parts.push(arrow(id+'arrow'+i,vertical?bw/2:x-gap+5,vertical?sy-gap+5:bh/2,
            [[0,0],vertical?[0,gap-10]:[gap-10,0]],{roughness:0,strokeColor:'#3d5130'}));
        });
        bottom=vertical?visual.steps.length*(bh+gap)-gap:bh;
      } else {
        const parsed=visual.items.map(item=>item.value.match(/^(\d+(?:\.\d+)?)\s*([^\d]*)$/));
        const numeric=parsed.every(value=>value && value[2].trim()===parsed[0][2].trim());
        const values=numeric?parsed.map(value=>Number(value[1])):[];
        const maximum=numeric?Math.max(...values):0;
        if (maximum>0) metricScales.push({id,baseline:0,unit:parsed[0][2].trim(),items:visual.items.map((item,i)=>({label:item.label,value:values[i],barWidth:w*values[i]/maximum,origin:0}))});
        const valueSize=34, valueWidth=Math.max(...visual.items.map(item=>estimateTextWidth(item.value,valueSize)))+4;
        const stacked=w-valueWidth-24<180;
        for (const [i,item] of visual.items.entries()) {
          if (stacked) {
            bottom+=addText('label'+i,item.label,0,bottom,w)+4;
            bottom+=addText('value'+i,item.value,0,bottom,w,valueSize)+12;
          } else {
            bottom+=Math.max(addText('label'+i,item.label,0,bottom,w-valueWidth-24),
              addText('value'+i,item.value,w-valueWidth,bottom,valueWidth,valueSize))+12;
          }
          if (maximum>0) {
            parts.push(rect(id+'track'+i,0,bottom,w,10,'#d3d9cc',{roughness:0,strokeColor:'transparent'}));
            if (values[i]>0) parts.push(rect(id+'bar'+i,0,bottom,w*values[i]/maximum,10,'#708561',{roughness:0,strokeColor:'transparent'}));
            bottom+=30;
          }
        }
        if (maximum>0) bottom+=addText('baseline','Bars start at zero.',0,bottom,w,18);
      }
      bottom+=16;
      bottom+=addText('caption',visual.caption,0,bottom,w,18);
      return {elements:parts,height:bottom};
    }
    for (const row of spec.packing.rows) {
      const available=width-gap*(row.columns.length-1);
      const columns=row.columns.map(column=>{
        const w=available*column.span/12;
        const panels=column.cards.map(i=>{
          const card=spec.nodes[i], body=measure(card.body,w-2*pad,24);
          const heading=measure(card.title,w-2*pad,i===spec.focus?34:28);
          const visual=visualParts(card.visual,w-2*pad,'visual'+i+'-');
          return {i,w,body,heading,visual,height:2*pad+body.height+heading.height+18+(visual.height?24+visual.height:0)};
        });
        return {w,panels,height:panels.reduce((sum,p)=>sum+p.height,0)+gap*(panels.length-1)};
      });
      const h=Math.max(...columns.map(c=>c.height));
      let x=16;
      for (const column of columns) {
        let cy=y;
        for (const p of column.panels) {
          const ph=p.height+(h-column.height)/column.panels.length;
          const focus=p.i===spec.focus;
          const palettes={contribution:['#d6dfc7','#3d5130'],mechanism:['#e0e9ee','#34566a'],
            evidence:['#e5e8dd','#3d5130'],limitation:['#efe3d9','#76543d'],context:['#f3f1eb','#3d5130']};
          const [fill,ink]=palettes[focus?'contribution':spec.nodes[p.i].role || 'context'];
          elements.push(rect('panel'+p.i,x,cy,p.w,ph,fill,{roughness:0,strokeColor:'transparent',roundness:{type:3}}));
          let ty=cy+pad;
          for (const [name,t] of [['heading',p.heading],['body',p.body]]) {
            elements.push(textEl(name+p.i,x+pad,ty,p.w-2*pad,t.height,t.value,t.size,{fontFamily:2,textAlign:'left',verticalAlign:'top',strokeColor:name==='heading'?ink:'#292d23',roughness:0}));
            ty+=t.height+18;
          }
          for (const part of p.visual.elements) elements.push({...part,x:part.x+x+pad,y:part.y+ty+6});
          cy+=ph+gap;
        }
        x+=column.w+gap;
      }
      y+=h+gap;
    }

  } else if (spec.layout === 'illustration') {
    const top=30+text('title',spec.title,24,16,720,28);
    const part=illustration(spec._asset,'illustration',24,top,720);
    elements.push(part);
    text('takeaway',spec.takeaway,24,top+part.height+24,720,24);
  } else {
  const comparison = spec.layout === 'comparison', square = spec.nodes.length === 4;
  const columns = square ? 2 : spec.nodes.length, panelWidth = 380, gap = 155;
  const width = columns*panelWidth+(columns-1)*gap;
  const top = 42 + text('title',spec.title,24,16,width,28);
  const sizes = spec.nodes.map(panel => ({
    title:wrapText(panel.title,panelWidth-40,24).split('\n').length*24*1.4,
    body:wrapText(panel.body,panelWidth-40,20).split('\n').length*20*1.4
  }));
  const height = Math.ceil(Math.max(...sizes.map(size=>size.title+size.body))+64);
  let bottom = top;
  spec.nodes.forEach((panel,i) => {
    const column = square && i>1 ? 3-i : i, row = square && i>1 ? 1 : 0;
    const x = 24+column*(panelWidth+gap), y = top+row*(height+125);
    const focus = spec.focus === i;
    elements.push({shape:'rect',id:'panel'+i,at:[x,y],size:[panelWidth,height],fill:focus?'#e7edda':'#faf8f0',stroke:focus?'#466038':'#777d70'});
    text('heading'+i,panel.title,x+20,y+20,panelWidth-40,24,focus?'#466038':'#292d23');
    text('body'+i,panel.body,x+20,y+40+sizes[i].title,panelWidth-40,20);
    if (!comparison && i) {
      const down = square && i===2, reverse = square && i===3;
      elements.push({shape:'arrow',id:'arrow'+i,from:'panel'+(i-1),to:'panel'+i,fromSide:down?'bottom':reverse?'left':'right',toSide:down?'top':reverse?'right':'left',head:'arrow',stroke:'#777d70'});
      if (down) text('transition'+i,spec.arrows[i-1],x+panelWidth/2+25,y-104,panelWidth/2-25,16);
      else text('transition'+i,spec.arrows[i-1],reverse?x+panelWidth+10:x-gap+10,y+height/2+24,gap-20,16);
    }
    bottom = Math.max(bottom,y+height);
  });
  bottom += 35;
  bottom += text('takeaway',spec.takeaway,24,bottom,width,25,'#466038')+20;
  // Full scope remains in the article/EPUB caption; repeating it inside the image makes the figure taller.
  }
  const result = await render(elements,{formats:['svg','excalidraw'],scale:2});
  if (spec.layout === 'bento') {
    const scene=new Map(JSON.parse(result.outputs.excalidraw).elements.map(e=>[e.id,e]));
    for (const scale of metricScales) scale.items.forEach((item,i)=>{
      const track=scene.get(scale.id+'track'+i), bar=scene.get(scale.id+'bar'+i);
      if (item.value>0 && (!bar || Math.abs(bar.width-item.barWidth)>0.001 || bar.x!==track.x || bar.y!==track.y)) throw new Error('Chart geometry does not match its values');
    });
    // This renderer version centers SVG text regardless of the editable scene alignment.
    const positions=elements.filter(e=>e.type==='text').flatMap(e=>e.text.split('\n').map(()=>e.x));
    let cursor=0;
    result.outputs.svg=result.outputs.svg.replace(/<text\s[^>]*>/g,tag=>tag.replace(/x="[^"]*"/, 'x="'+positions[cursor++]+'"').replace('text-anchor="middle"','text-anchor="start"'));
  }
  if (illustrationAssets.size) {
    const scene=JSON.parse(result.outputs.excalidraw);
    scene.files ||= {};
    for (const [id,asset] of illustrationAssets) {
      const e=scene.elements.find(e=>e.id===id);
      Object.assign(e,{type:'image',fileId:id,status:'saved',scale:[1,1],crop:null});
      scene.files[id]={id,dataURL:asset.png,mimeType:'image/png',created:0,lastRetrieved:0};
      result.outputs.svg=result.outputs.svg.replace('</svg>',
        `<image x="${e.x}" y="${e.y}" width="${e.width}" height="${e.height}" href="${asset.svg}"/></svg>`);
    }
    result.outputs.excalidraw=JSON.stringify(scene);
  }
  // Use the portable runtime's converter for every PNG, avoiding optional npm native binaries.
  result.outputs.png=execFileSync('rsvg-convert',['--zoom=2'],{input:result.outputs.svg,maxBuffer:32*1024*1024});
  if (result.warnings.length) throw new Error(JSON.stringify(result.warnings));
  for (const [format,content] of Object.entries(result.outputs)) fs.writeFileSync(process.argv[2]+'.'+format,content);
  process.stdout.write(JSON.stringify({renderer:'excalidrawer@0.5.12',warnings:[],element_count:result.elementCount,metric_scales:metricScales,
    illustrations:[...illustrationAssets.values()].map(({renderer,source,alt})=>({renderer,source,alt}))}));
} catch(error) { process.stderr.write(error.message); process.exitCode=1; }

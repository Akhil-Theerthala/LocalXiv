import fs from 'node:fs';
import {render, wrapText, estimateTextWidth} from 'excalidrawer';
const spec = JSON.parse(fs.readFileSync(0, 'utf8'));
// Model supplies meaning. Geometry keeps two/three steps in a row and four in a square.
const elements = [];
function text(id,value,x,y,width,size=24,color='#292d23') {
  const wrapped = wrapText(value,width,size), lines = wrapped.split('\n');
  if (lines.some(line => estimateTextWidth(line,size) > width)) throw new Error('Shorten an unbroken label in '+id);
  const height = lines.length*size*1.4;
  elements.push({shape:'text',id,text:wrapped,at:[x,y],size:[width,height],fontSize:size,textColor:color});
  return height;
}
try {
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
  const result = await render(elements,{formats:['excalidraw','svg','png'],scale:2});
  if (result.warnings.length) throw new Error(JSON.stringify(result.warnings));
  for (const [format,content] of Object.entries(result.outputs)) fs.writeFileSync(process.argv[2]+'.'+format,content);
  process.stdout.write(JSON.stringify({renderer:'excalidrawer@0.5.12',warnings:[],element_count:result.elementCount}));
} catch(error) { process.stderr.write(error.message); process.exitCode=1; }

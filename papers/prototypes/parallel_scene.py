"""One semantic layout: a shared input, parallel operations and a combined output."""
from html import escape
import textwrap

def render_parallel_scene(scene):
    if not isinstance(scene,dict) or scene.get('kind')!='parallel-composition':
        raise ValueError('Scene kind must be parallel-composition.')
    def label(item,key,limit):
        value=item.get(key)
        if not isinstance(value,str) or not value.strip() or len(value)>limit:
            raise ValueError('Scene '+key+' must contain 1–'+str(limit)+' characters. Shorten the annotation, not the font.')
        return value
    shared=label(scene,'input',42)
    combine=label(scene,'combine',30); result=label(scene,'output',48)
    context=label(scene,'context',100)
    branches=scene.get('branches')
    if not isinstance(branches,list) or not 2<=len(branches)<=3:
        raise ValueError('Parallel composition needs two or three branches.')
    for branch in branches:
        if not isinstance(branch,dict): raise ValueError('Each branch needs an operation and result.')
        label(branch,'operation',30); label(branch,'result',48)
    def lines(value,x,y,width,size=24):
        return ''.join('<text x="'+str(x)+'" y="'+str(y+i*28)+'" font-size="'+str(size)+'">'+escape(line)+'</text>'
                       for i,line in enumerate(textwrap.wrap(value,width=width)))
    def arrow(points):
        x,y=points[-1]
        return '<polyline points="'+' '.join(str(a)+','+str(b) for a,b in points)+'" fill="none" stroke="#627168" stroke-width="2"/><polygon points="'+str(x)+','+str(y)+' '+str(x-9)+','+str(y-5)+' '+str(x-9)+','+str(y+5)+'" fill="#627168"/>'
    parts=['<svg viewBox="0 0 880 660"><title>Shared input, parallel operations, combined output</title>']
    rows=[40,170,300] if len(branches)==3 else [105,265]
    for y in rows:
        parts.append(arrow([(200,250),(220,250),(220,y+55),(250,y+55)]))
        parts.append('<polyline points="660,'+str(y+55)+' 720,'+str(y+55)+' 720,500 660,500" fill="none" stroke="#627168" stroke-width="2"/>')
    parts.append('<polygon points="660,500 669,495 669,505" fill="#627168"/>')
    parts.append('<rect x="10" y="175" width="190" height="160" rx="10" fill="#f1e3d8"/>')
    parts.append(lines(shared,24,212,13))
    for y,branch in zip(rows,branches):
        parts.append('<rect x="250" y="'+str(y)+'" width="410" height="110" rx="10" fill="#e1ebf1"/>')
        parts.append(lines(branch['operation'],266,y+30,30))
        parts.append(lines(branch['result'],266,y+64,26))
    parts.append('<rect x="250" y="450" width="410" height="110" rx="10" fill="#dce8cf"/>')
    parts.append(lines(combine,266,480,30)+lines(result,266,514,26))
    parts.append(lines(context,10,605,60))
    parts.append('</svg>')
    return ''.join(parts)

"""Shared presentation settings, local prompt edits and complete figure exports."""
from copy import deepcopy
import json,re,textwrap

DEFAULTS=dict(subtitle=None,footnote='',font='Arial',font_size=13,title_size=24,label_size=12,
    legend='top',value_labels='auto',markers=True,line_width=2.5,marker_size=32,
    bar_size=18,gridlines=True,background='#ffffff',series_colors={},
    label_angle='auto',decimals=None,number_format='auto',tick_count=5,
    separate_panels=False,reference_value=None,reference_label='Reference',
    layout='Full slide · 16:9')

def effective(result,presentation):
    import streamlit as st
    return {**DEFAULTS,**presentation,**st.session_state.get('chart_formats',{}).get(result['result_id'],{})}

def commit(result,presentation):
    import streamlit as st
    rid=result['result_id'];s=st.session_state
    old=s.get('chart_formats',{}).get(rid)
    if old!=presentation:
        undo=dict(s.get('chart_undo',{}));undo[rid]=(undo.get(rid,[])+[deepcopy(old)])[-20:];s.chart_undo=undo
        s.chart_formats={**s.get('chart_formats',{}),rid:deepcopy(presentation)}

def color_series(result,presentation=None):
    """Use the actual rendered color domains, including overrides and constants."""
    from .charts import panels
    from .responses import presentation_for
    p={**DEFAULTS,**(presentation or presentation_for(result))};out={}
    def collect(node,spec):
        if not isinstance(node,dict):return
        mark=node.get('mark',{});kind=mark.get('type') if isinstance(mark,dict) else mark
        if kind in {'line','bar'}:
            color=node.get('encoding',{}).get('color',{})
            scale=color.get('scale',{});domain=scale.get('domain',[]);palette=scale.get('range',[])
            if domain and palette:out.update({n:palette[i%len(palette)] for i,n in enumerate(domain)})
            elif 'value' in color:
                field='series_label' if kind=='line' else 'institution'
                for data in spec.get('datasets',{}).values():
                    for row in data:
                        if field in row:out[row[field]]=color['value']
        for layer in node.get('layer',[]):collect(layer,spec)
    for panel in panels(result,p):
        spec=styled(panel,p);collect(spec,spec)
    return out


def series_names(result,presentation=None):
    return list(color_series(result,presentation))

def normalize_edit_question(q):
    """Normalize request politeness, never the quoted text or data selection."""
    q=q.strip().rstrip('.!?').strip()
    return re.sub(r'^(?:(?:can|could|would) you\s+)?(?:please\s+)?','',q,flags=re.I)


def edit_text(value):
    value=value.strip()
    if len(value)>=2 and (value[0],value[-1]) in {('"','"'),("'","'"),('“','”'),('‘','’')}:return value[1:-1].strip()
    return value


def edit_clauses(q):
    """Split commands outside quotes; apostrophes in names are not quotes."""
    parts=[];start=0;quote=None;i=0
    closes={'"':'"',"'":"'",'“':'”','‘':'’'}
    verbs=r'(?:make|set|change|show|hide|label|use|remove|highlight|move|rename|reset|sort|order|switch|rotate)'
    while i<len(q):
        ch=q[i]
        if quote:
            if ch==quote and not (ch in {"'",'’'} and i>0 and i+1<len(q) and q[i-1].isalnum() and q[i+1].isalnum()):quote=None
        elif ch in closes and (i==0 or q[i-1].isspace() or q[i-1] in '(:='):
            quote=closes[ch]
        elif ch in ',;' and not (ch==',' and i>0 and i+1<len(q) and q[i-1].isdigit() and q[i+1].isdigit()):
            parts.append(q[start:i].strip());start=i+1
        elif ch.isspace() and (m:=re.match(r'\s+and\s+(?='+verbs+r'\b)',q[i:],re.I)):
            parts.append(q[start:i].strip());i+=m.end();start=i;continue
        i+=1
    parts.append(q[start:].strip())
    return [re.sub(r'^and\s+','',p,flags=re.I) for p in parts if p]

def extra_edits(question,previous):
    """Return settings or None; a compound edit succeeds atomically."""
    if not previous or 'result' not in previous:return None
    q=normalize_edit_question(question)
    changes={}
    # Commas within quoted titles/numbers are preserved. Split explicit conjunctions.
    clauses=edit_clauses(q)
    colors=r'(blue|red|green|gray|grey|orange|purple|black|navy|#[0-9a-f]{6})'
    for clause in clauses:
        c=clause.strip();low=c.lower();m=None
        if (m:=re.fullmatch(r'(?:(?:make|set|change|highlight) )?(.+?)(?: color)?(?: to| in)? '+colors,c,re.I)):
            target=m[1].strip(' "“”')
            target=re.sub(r'^the color of\s+','',target,flags=re.I)
            target=re.sub(r"(?:['’]s)?\s+(?:line|bar|series)$",'',target,flags=re.I)
            names=series_names(previous['result'],previous.get('presentation'))
            matches=[n for n in names if target.casefold() in n.casefold()]
            if len(matches)!=1:return None
            changes.setdefault('series_colors',{}).update({matches[0]:m[2].lower()})
            changes['color']=None
        elif (m:=re.fullmatch(r'(?:set|change)(?: the)? (font size|title size|label size|line width|marker size|bar width|tick count|decimals|font)(?: to)? (.+)',c,re.I)):
            key={'font':'font','font size':'font_size','title size':'title_size','label size':'label_size','line width':'line_width','marker size':'marker_size','bar width':'bar_size','tick count':'tick_count','decimals':'decimals'}[m[1].lower()]
            v=m[2].strip(' "“”');bounds={'font_size':(10,32),'title_size':(14,48),'label_size':(10,28),'line_width':(1,8),'marker_size':(10,200),'bar_size':(8,40),'tick_count':(2,12),'decimals':(0,4)}
            if key=='font':
                if v.lower() not in {'arial','calibri','georgia','times new roman','verdana'}:return None
                changes[key]=v.title()
            else:
                try:value=float(re.sub(r'\s*(?:px|pt|pixels|points)$','',v))
                except ValueError:return None
                if not bounds[key][0]<=value<=bounds[key][1] or key not in {'line_width'} and value!=int(value):return None
                changes[key]=value if key=='line_width' else int(value)
        elif (m:=re.fullmatch(r'(?:set|change)(?: the)? subtitle to (.+)',c,re.I)):changes['subtitle']=edit_text(m[1])
        elif low in {'hide subtitle','remove subtitle'}:changes['subtitle']=''
        elif (m:=re.fullmatch(r'(?:add|set|change)(?: the| a)? footnote(?: to)? (.+)',c,re.I)):changes['footnote']=edit_text(m[1])
        elif low in {'hide footnote','remove footnote'}:changes['footnote']=''
        elif re.fullmatch(r'(?:show|hide) (?:the )?(?:point )?markers',low):changes['markers']=low.startswith('show')
        elif re.fullmatch(r'(?:show|hide|remove) (?:the )?gridlines',low):changes['gridlines']=low.startswith('show')
        elif re.fullmatch(r'(?:hide|remove) (?:the )?legend',low):changes['legend']='none'
        elif low in {'use direct labels','show direct labels'}:changes['legend']='direct'
        elif (m:=re.fullmatch(r'(?:move|set|change|show)(?: the)? legend(?: position)?(?: to| at)?(?: the)? (top|bottom|left|right)',low)):changes['legend']=m[1]
        elif (m:=re.fullmatch(r'(?:label|show labels for)(?: only)? (?:the )?(latest(?: year| values?)?|endpoints|all(?: values| points)?|no points)',low)):
            changes['value_labels']='latest' if m[1].startswith('latest') else 'endpoints' if m[1]=='endpoints' else 'none' if m[1]=='no points' else 'all'
        elif low in {'hide value labels','remove value labels'}:changes['value_labels']='none'
        elif low in {'use separate panels','show separate panels','separate the panels'}:changes['separate_panels']=True
        elif low in {'combine panels','use combined panels'}:changes['separate_panels']=False
        elif low in {'use presentation preset','use presentation style'}:changes.update(font_size=18,title_size=28,label_size=16,value_labels='latest',legend='direct')
        elif low in {'use full slide layout','use full-slide layout'}:changes['layout']='Full slide · 16:9'
        elif low in {'use half slide layout','use half-slide layout'}:changes['layout']='Half slide · 4:3'
        elif (m:=re.fullmatch(r'(?:use|set)(?: the)? (?:number format to )?(compact|standard) number(?:s| formatting)?',low)):changes['number_format']='compact' if m[1]=='compact' else 'auto'
        elif (m:=re.fullmatch(r'(?:add|set)(?: a| the)? reference line(?: at| to)? ([+-]?[\d,.]+)(?: labeled ["“]?(.+?)["”]?)?',c,re.I)):
            changes.update(reference_value=float(m[1].replace(',','')),reference_label=m[2] or 'Reference')
        elif low in {'remove reference line','hide reference line'}:changes['reference_value']=None
        elif (m:=re.fullmatch(r'(?:make|set|change)(?: the)? background(?: to)? (white|transparent|#[0-9a-f]{6})',low)):changes['background']=m[1]
        else:return None
    if not changes:return None
    if 'series_colors' in changes:changes['series_colors']={**previous.get('presentation',{}).get('series_colors',{}),**changes['series_colors']}
    return changes

def number_pattern(unit,p):
    if p.get('number_format')=='compact':return '.3~s'
    decimals=p.get('decimals')
    return (',' if unit!='ratio' else '')+'.'+str(decimals if decimals is not None else 1 if unit in {'percent','FTE','percentage points'} else 4 if unit=='ratio' else 0)+'f'

def styled(panel,p):
    """Style a copied Vega-Lite specification; source rows remain untouched."""
    from .charts import PALETTE,formatted
    from .units import is_currency
    spec=deepcopy(panel['chart'].to_dict());temporal=p['chart_type']=='line'
    legend=p.get('legend','top');labels=p.get('value_labels','auto');unit=panel['unit']
    def walk(node):
        if not isinstance(node,dict):return
        enc=node.get('encoding',{})
        for channel in ['x','y']:
            axis=enc.get(channel,{}).get('axis')
            if axis is not None:
                if 'labelLineHeight' in axis:axis['labelLineHeight']=p.get('font_size',13)+3
                if enc[channel].get('type')=='quantitative':
                    axis['format']=number_pattern(unit,p);axis['tickCount']=p.get('tick_count',5)
                    axis['grid']=p.get('gridlines',True)
        for channel in ['color','strokeDash']:
            e=enc.get(channel)
            if e and 'field' in e:
                e['legend']=None if legend in {'none','direct'} else dict(orient=legend,title=None,labelLimit=320)
                if channel=='strokeDash' and 'value' not in enc.get('color',{}):e['legend']=None
                if channel=='color' and 'scale' in e:
                    existing=e['scale'].get('range',PALETTE)
                    e['scale']['range']=[p.get('series_colors',{}).get(n,p.get('color') or existing[i%len(existing)]) for i,n in enumerate(e['scale']['domain'])]
        mark=node.get('mark')
        if isinstance(mark,dict):
            if mark['type']=='line':mark.update(strokeWidth=p.get('line_width',2.5),point={'size':p.get('marker_size',32)} if p.get('markers',True) else False)
            elif mark['type']=='bar':mark['size']=p.get('bar_size',18)
            elif mark['type']=='text':mark['fontSize']=p.get('label_size',12)
        if isinstance(mark,dict) and mark['type']=='text' and enc.get('text',{}).get('field')=='display_value' and (p.get('decimals') is not None or p.get('number_format')=='compact'):
            expression=("'$' + " if is_currency(unit) else '')+f"format(datum.plot_value, '{number_pattern(unit,p)}')"+(" + '%'" if unit=='percent' else '')
            node.setdefault('transform',[]).append({'calculate':expression,'as':'formatted_label'})
            enc['text']={'field':'formatted_label','type':'nominal'}
        for layer in node.get('layer',[]):walk(layer)
    walk(spec)
    # Make raw values visible outside interactive tooltips.
    if temporal and (labels not in {'auto','none'} or legend=='direct'):
        source=spec if 'layer' not in spec else spec['layer'][0]
        enc=deepcopy(source['encoding']);enc.pop('strokeDash',None);enc.pop('detail',None)
        transforms=[{'filter':'isValid(datum.plot_value)'},{'joinaggregate':[{'op':'max','field':'observation_year','as':'last_year'},{'op':'min','field':'observation_year','as':'first_year'}],'groupby':['series_label']}]
        pattern=number_pattern(unit,p)
        suffix='%' if unit=='percent' else ''
        label_expr=("'$' + " if is_currency(unit) else '')+f"format(datum.plot_value, '{pattern}') + '{suffix}'"
        if legend=='direct':label_expr='datum.series_label' if labels=='none' else f"datum.series_label + ' · ' + {label_expr}"
        if labels!='all' or legend=='direct':transforms.append({'filter':'datum.observation_year == datum.last_year'+(' || datum.observation_year == datum.first_year' if labels=='endpoints' and legend!='direct' else '')})
        transforms.append({'calculate':label_expr,'as':'format_label'})
        enc['text']={'field':'format_label','type':'nominal'}
        layer=dict(mark=dict(type='text',align='left' if legend=='direct' else 'center',dx=10 if legend=='direct' else 0,dy=0 if legend=='direct' else -14,fontSize=p.get('label_size',12)),encoding=enc,transform=transforms)
        spec['layer']=[{k:spec.pop(k) for k in ['mark','encoding'] if k in spec},layer]
        if legend=='direct':spec['padding']['right']=240
    elif not temporal and labels=='none':
        spec['layer']=[layer for layer in spec.get('layer',[]) if layer.get('mark',{}).get('type')!='text']
    if p.get('reference_value') is not None:
        axis='y' if temporal else 'x';value=p['reference_value']
        if 'layer' not in spec:spec['layer']=[{k:spec.pop(k) for k in ['mark','encoding'] if k in spec}]
        spec['layer'].append({'data':{'values':[{'reference':value,'caption':p.get('reference_label','Reference')}]},'mark':{'type':'rule','strokeDash':[5,4],'color':'#52616D'},'encoding':{axis:{'field':'reference','type':'quantitative'}}})
        spec['layer'].append({'data':{'values':[{'reference':value,'caption':p.get('reference_label','Reference')}]},'mark':{'type':'text','align':'left','dx':8,'dy':-9,'color':'#52616D'},'encoding':{axis:{'field':'reference','type':'quantitative'},'text':{'field':'caption'}}})
    config=spec.setdefault('config',{});config['font']=p.get('font','Arial')
    config.setdefault('axis',{}).update(labelFontSize=p.get('font_size',13),titleFontSize=p.get('font_size',13))
    config.setdefault('legend',{})['labelFontSize']=p.get('font_size',13)
    config.setdefault('text',{})['font']=p.get('font','Arial')
    spec['background']=p.get('background','#ffffff')
    return spec

def figure_spec(panel,p,result,width=1200,height=675):
    """A complete fixed-size figure; title/source/caveats travel with the plot."""
    from .result_text import evidence_summary,visible_warnings
    spec=styled(panel,p);spec.pop('autosize',None)
    spec['width']=max(200,width-330 if p.get('legend')=='direct' else width-140)
    spec['height']=max(180,height-260,spec.get('height',0) if p['chart_type']=='bar' else 0)
    subtitle=p.get('subtitle') if p.get('subtitle') is not None else panel['subtitle']
    sources=evidence_summary(result)['sources']
    source_lines=['Source: IPEDS · '+ ' · '.join(str(row.get(k,'')) for k in ['IPEDS release','Survey','Year coverage','Table']) for row in sources]
    # Summarize annual sources without misrepresenting reporting periods.
    families={(r.get('Survey'),re.sub(r'20\d{2}|19\d{2}','{year}',str(r.get('Table','')))) for r in sources}
    if len(source_lines)>3 and len(families)==1:
        surveys=list(dict.fromkeys(str(r.get('Survey','')) for r in sources));tables=[str(r.get('Table','')) for r in sources]
        source_lines=['Source: IPEDS · '+'; '.join(surveys)+' · '+tables[0]+' through '+tables[-1], 'Source releases: '+str(sources[0].get('IPEDS release',''))+' through '+str(sources[-1].get('IPEDS release',''))]
    notes=source_lines+([p['footnote'].strip()] if p.get('footnote','').strip() else [])+[panel['note']]+visible_warnings(result)+evidence_summary(result).get('source_notes',[])
    footer=[line for note in notes for line in textwrap.wrap(note,max(65,int(width/8)))]
    title={'text':textwrap.wrap(panel['title'],max(35,int(width/18))),'subtitle':textwrap.wrap(subtitle,max(50,int(width/11))) if subtitle else [],'anchor':'start','fontSize':p.get('title_size',24),'subtitleFontSize':p.get('font_size',13),'offset':24,'color':'#203747'}
    # vconcat keeps provenance inside the exported image, with no page controls.
    config=spec.pop('config',{});background=spec.pop('background','white');spec.pop('$schema',None)
    datasets=spec.pop('datasets',{})
    foot={'data':{'values':[{'note':n,'row':i} for i,n in enumerate(footer)]},'mark':{'type':'text','align':'left','baseline':'top','fontSize':11,'color':'#52616D'},'encoding':{'x':{'value':0},'y':{'field':'row','type':'ordinal','axis':None},'text':{'field':'note'}},'width':width-80,'height':max(25,len(footer)*16)}
    return {'$schema':'https://vega.github.io/schema/vega-lite/v6.json','title':title,'vconcat':[spec,foot],'datasets':datasets,'spacing':24,'padding':30,'config':config,'background':background,'usermeta':{'canvas_width':width,'canvas_height':height}}

def export_figure(spec,kind='png',scale=2):
    import vl_convert as vlc
    import xml.etree.ElementTree as ET
    svg=vlc.vegalite_to_svg(spec);root=ET.fromstring(svg)
    width=spec['usermeta']['canvas_width'];height=spec['usermeta']['canvas_height']
    natural_w=float(root.attrib['width']);natural_h=float(root.attrib['height']);factor=min(width/natural_w,height/natural_h)
    root.set('x',str((width-natural_w*factor)/2));root.set('y',str((height-natural_h*factor)/2))
    root.set('width',str(natural_w*factor));root.set('height',str(natural_h*factor))
    background=spec.get('background','white')
    outer=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="{background}"/>'+ET.tostring(root,encoding='unicode')+'</svg>'
    if kind=='svg':return outer.encode('utf-8')
    return vlc.svg_to_png(outer,scale=scale)

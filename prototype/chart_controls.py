"""Discoverable chart editor and export preview, sharing settings with chat."""
from copy import deepcopy
import streamlit as st
from .charts import DEFAULTS,effective,commit,color_series,figure_spec,export_figure

@st.cache_data(show_spinner=False,max_entries=32)
def image_bytes(spec,kind,scale):return export_figure(spec,kind,scale)

def undo(result):
    rid=result['result_id'];stack=st.session_state.get('chart_undo',{}).get(rid,[])
    if stack:
        old=stack.pop();formats=dict(st.session_state.get('chart_formats',{}))
        if old is None:formats.pop(rid,None)
        else:formats[rid]=old
        st.session_state.chart_formats=formats

def editor(result,p,key):
    heading,close=st.columns([5,1],vertical_alignment='center')
    heading.markdown('**Format chart**')
    if close.button('×',key=key+'_format_close',help='Close chart formatting',type='tertiary'):
        st.session_state[key+'_format_open']=False
        st.rerun()
    tabs=st.tabs(['Layout','Text','Style','Axes'])
    def control(kind,label,field,**args):
        widget_key=key+'_format_'+field
        val=p.get(field,DEFAULTS.get(field))
        if kind=='selectbox':
            options=args['options'];val=val if val in options else options[0]
        st.session_state[widget_key]=val
        def update():
            change=deepcopy(p);change[field]=st.session_state[widget_key];commit(result,change)
        return getattr(st,kind)(label,key=widget_key,on_change=update,**args)
    with tabs[0]:
        control('selectbox','Chart type','chart_type',options=['line','bar'])
        control('selectbox','Bar order','sort',options=['auto','ascending','descending','alphabetical'])
        control('selectbox','Export layout','layout',options=['Full slide · 16:9','Half slide · 4:3'])
        control('checkbox','Separate series into panels','separate_panels')
        if st.button('Use presentation preset',key=key+'_preset'):
            commit(result,{**p,'font_size':18,'title_size':28,'label_size':16,'legend':'direct','value_labels':'latest'});st.rerun()
        if st.button('Presentation preview',key=key+'_layout_preview'):preview(result,p,key)
        st.caption('Export includes the title, source and material notes. Each panel can be downloaded separately.')
    with tabs[1]:
        # None means use the automatic title/subtitle. Empty subtitle hides it.
        for field in ['title','subtitle','x_label','y_label']:
            widget_key=key+'_format_'+field;st.session_state[widget_key]=p.get(field) or ''
            def update_text(f=field,k=widget_key):
                change=deepcopy(p);change[f]=st.session_state[k] if f=='subtitle' else st.session_state[k] or None;commit(result,change)
            st.text_input({'title':'Chart title','subtitle':'Subtitle','x_label':'X-axis title','y_label':'Y-axis title'}[field],key=widget_key,on_change=update_text,placeholder='Automatic' if field!='subtitle' else 'Automatic until edited')
        footnote_key=key+'_format_footnote'
        st.session_state[footnote_key]=p.get('footnote','')
        def update_footnote():commit(result,{**p,'footnote':st.session_state[footnote_key]})
        st.text_area('Footnote',key=footnote_key,on_change=update_footnote,help='Add your own note below the chart. Sources and required data notes remain visible.')
        control('selectbox','Font','font',options=['Arial','Calibri','Georgia','Times New Roman','Verdana'])
        control('number_input','Axis and legend font size','font_size',min_value=10,max_value=32,step=1)
        control('number_input','Title font size','title_size',min_value=14,max_value=48,step=1)
        control('number_input','Value-label font size','label_size',min_value=10,max_value=28,step=1)
    with tabs[2]:
        from .charts import PALETTE
        rendered_colors=color_series(result,p)
        for i,(name,rendered_color) in enumerate(rendered_colors.items()):
            widget_key=key+'_series_'+str(i);st.session_state[widget_key]=rendered_color
            def recolor(n=name,k=widget_key):
                change=deepcopy(p);change['color']=None;change['series_colors']={**rendered_colors,n:st.session_state[k]};commit(result,change)
            # Chat accepts named colors; picker requires hexadecimal.
            value=st.session_state[widget_key]
            if not value.startswith('#'):
                named={'blue':'#0000ff','red':'#ff0000','green':'#008000','gray':'#808080','grey':'#808080','orange':'#ffa500','purple':'#800080','black':'#000000','navy':'#000080'}
                st.session_state[widget_key]=named.get(value,PALETTE[i%4])
            st.color_picker(name,key=widget_key,on_change=recolor)
        control('selectbox','Value labels','value_labels',options=['auto','none','latest','endpoints','all'])
        control('selectbox','Legend','legend',options=['top','bottom','left','right','none','direct'])
        control('checkbox','Show point markers','markers')
        control('checkbox','Show numeric gridlines','gridlines')
        control('slider','Line width','line_width',min_value=1.0,max_value=8.0,step=.5)
        control('slider','Marker size','marker_size',min_value=10,max_value=200,step=2)
        control('slider','Bar width','bar_size',min_value=8,max_value=40,step=1)
        control('selectbox','Background','background',options=list(dict.fromkeys(['#ffffff','transparent',p.get('background','#ffffff')])))
        bg_key=key+'_background_color';st.session_state[bg_key]=p.get('background') if str(p.get('background')).startswith('#') else '#ffffff'
        def recolor_background():commit(result,{**p,'background':st.session_state[bg_key]})
        st.color_picker('Background color',key=bg_key,on_change=recolor_background)
    with tabs[3]:
        if p['chart_type']=='line':
            st.caption('Every reporting period stays visible. Numeric limits apply to the Y-axis.')
        else:
            st.caption('Numeric limits apply to the horizontal value (X) axis.')
        control('selectbox','Number format','number_format',options=['auto','compact'])
        control('selectbox','Decimal places','decimals',options=[None,0,1,2,3,4],format_func=lambda x:'Automatic' if x is None else str(x))
        control('number_input','Suggested numeric tick count','tick_count',min_value=2,max_value=12,step=1)
        # Validate both bounds atomically; partial/invalid inputs never reach chart scales.
        with st.form(key+'_bounds'):
            lo=st.number_input('Numeric minimum',value=float(p['y_min']) if p.get('y_min') is not None else 0.0)
            hi=st.number_input('Numeric maximum',value=float(p['y_max']) if p.get('y_max') is not None else 100.0)
            if st.form_submit_button('Apply numeric limits'):
                percentage=all(r['unit']=='percent' for r in result['rows'])
                if lo>=hi or percentage and not 0<=lo<hi<=100:st.error('Choose increasing bounds, within 0–100 for percentages.')
                else:commit(result,{**p,'y_min':lo,'y_max':hi});st.rerun()
        if st.button('Reset numeric limits',key=key+'_reset_limits'):commit(result,{**p,'y_min':None,'y_max':None});st.rerun()
        with st.form(key+'_reference'):
            ref=st.number_input('Reference line value',value=float(p.get('reference_value') or 0))
            caption=st.text_input('Reference line label',value=p.get('reference_label','Reference'))
            if st.form_submit_button('Add / update reference line'):commit(result,{**p,'reference_value':ref,'reference_label':caption});st.rerun()
        if st.button('Remove reference line',key=key+'_remove_reference'):commit(result,{**p,'reference_value':None});st.rerun()
    a,b=st.columns(2)
    if a.button('Undo',key=key+'_undo',disabled=not st.session_state.get('chart_undo',{}).get(result['result_id'])):undo(result);st.rerun()
    if b.button('Reset formatting',key=key+'_reset'):
        from .responses import presentation_for
        commit(result,{**DEFAULTS,**presentation_for(result)});st.rerun()
    st.caption('Changes apply immediately. Your data and calculations stay the same.')

@st.dialog('Presentation preview',width='large')
def preview(result,p,key):
    from .intent_checks import check_result,IntentMismatch
    try:check_result(result)
    except IntentMismatch as exc:
        st.warning(str(exc));return
    from .charts import panels
    st.caption('Preview and download the complete figure, including its source and important notes.')
    st.html('<style>[role="dialog"] [data-testid="stImage"] img {max-height: max(220px, calc(100dvh - 330px)); width: auto !important; max-width:100%; object-fit:contain; margin:0 auto;}</style>')
    layout_col,type_col,resolution_col,download_col=st.columns([2,1,1.6,1.4],vertical_alignment='bottom')
    with layout_col:layout=st.selectbox('Slide layout',['Full slide · 16:9','Half slide · 4:3'],index=0 if p.get('layout','').startswith('Full') else 1,key=key+'_preview_layout')
    with type_col:kind=st.selectbox('File type',['PNG','SVG'],key=key+'_preview_kind')
    with resolution_col:resolution=st.selectbox('Resolution',['Standard','High resolution'],index=1,key=key+'_preview_resolution')
    p={**p,'layout':layout};available=panels(result,p)
    index=st.selectbox('Chart panel',range(len(available)),format_func=lambda i:f"{i+1}. {available[i]['title']} — {available[i]['subtitle']}",key=key+'_preview_panel') if len(available)>1 else 0
    width,height=(1200,675) if layout.startswith('Full') else (800,600)
    scale=2 if resolution=='High resolution' else 1
    try:
        spec=figure_spec(available[index],p,result,width,height)
        png=image_bytes(spec,'png',scale)
        payload=png if kind=='PNG' else image_bytes(spec,'svg',scale)
        with download_col:st.download_button('Download chart',payload,file_name=f"ipeds-{result['result_id']}-panel-{index+1}.{kind.lower()}",mime='image/png' if kind=='PNG' else 'image/svg+xml',key=key+'_download_image',on_click='ignore')
        st.image(png,width='stretch')
        st.caption(f'{width*scale} × {height*scale} pixels' if kind=='PNG' else 'Vector SVG · scales without losing sharpness')
    except Exception as exc:
        st.error('The chart image could not be rendered. Your data and chart settings have been retained.')
        st.caption(str(exc))

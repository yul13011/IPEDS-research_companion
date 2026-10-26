"""Explore IPEDS, conversation and optional researcher tools."""
import json
from contextlib import contextmanager
import pandas as pd
import streamlit as st
from .catalog import BASE, DATA, search, IVY, institutions
from .analytics import Plan, execute, measures
from .agent import api_key, DEFAULT_MODEL, MODEL_LABELS
from .model_policy import AUTOMATIC,DEFAULT_STRATEGY
MODEL_OPTIONS={AUTOMATIC:'Automatic · Haiku for routine work, Sonnet for source planning',**MODEL_LABELS}
from .institution_confirmation import ask
from .components import render_result, render_evidence, render_catalog_proposal
from .exports import _safe
from .responses import finalize_answer,adjust_presentation,presentation_for
from .progress import report,reporting
from .workflows import (topics, execute_example, example_by_id, institution_index,
    institution_matches, institution_label, measure_matches, extract_plan, compatible_wide)


def navigate(page='Ask & Analyze',tool=None):
    st.session_state.main_page=page;st.session_state.active_tool=tool


def copy_widget(widget,target):st.session_state[target]=st.session_state[widget]
def set_step(step):st.session_state.extract_step=step
def open_topic(topic):
    st.session_state.topic_id=topic;st.session_state.topic_open=True
def close_topic():st.session_state.topic_open=False
def toggle_panel(panel):st.session_state[panel]=not st.session_state[panel]
def queue_example(example_id):
    st.session_state.pending_action={'type':'example','id':example_id};navigate()


def queue_analysis_choice(brief_id, option_id):
    from .analysis_clarification import latest
    brief=latest(st.session_state.history)
    if brief and brief['id']==brief_id and brief['status'] in {'pending','failed'}:
        st.session_state.pending_action={'type':'chat','question':option_id};navigate()


def seed_builder():
    s=st.session_state
    if s.last_plan and s.last_plan.get('version') not in {1,2} and s.last_plan.get('kind')!='catalog_clarification':
        p=s.last_plan
        try:s.extract_ids=institutions(p['institutions'],max(Plan(**p).validate()))
        except ValueError:pass
        s.extract_metrics=p['metrics'][:];s.extract_years=p['years'][:]
        s.extract_time_basis=p.get('time_basis','observation')
        s.extract_year_mode='One year' if len(p['years'])==1 else 'Selected years'
    s.extract_step=0;navigate(tool='builder')


def see_definition(query):st.session_state.definition_seed=query;navigate(tool='definitions')
def clear_conversation():
    s=st.session_state;s.history=[];s.last_plan=None;s.pending_action=None;s.ideas_epoch+=1;s.transcript_revision+=1;s.pop('request_error',None);s.pop('institution_pending',None);s.pop('confirmed_institutions',None)
    s.pop('chart_formats',None);s.pop('chart_undo',None)
def add_ivy():
    s=st.session_state;s.extract_ids=list(dict.fromkeys(s.extract_ids+IVY));s.builder_inst_widget=s.extract_ids[:]
def toggle_measure(metric):
    s=st.session_state
    s.extract_metrics=[m for m in s.extract_metrics if m!=metric] if metric in s.extract_metrics else s.extract_metrics+[metric]


def show_work_status(slot,message):
    slot.caption(message)


@contextmanager
def working_status():
    slot=st.empty()
    try:
        with st.spinner(''),reporting(lambda message:show_work_status(slot,message)):
            report('Starting your request…')
            yield
    finally:slot.empty()


def run_pending():
    # Widget reruns can interrupt any Streamlit output while a query is running.
    # Keep the submitted request until it has either committed or failed;
    # RerunException/StopException deliberately bypass the exception handlers.
    s=st.session_state;pending=s.get('pending_action')
    if not pending:return
    s.pop('request_error',None)
    try:
        with working_status():
            if pending['type']=='example':
                question=example_by_id(pending['id'])['question'];answer=execute_example(pending['id'])
            elif pending['type']=='extract':
                result=execute(Plan(**pending['plan']));s.extract_result=result
                question='Data extract: '+', '.join(measures()[m]['label'] for m in pending['plan']['metrics'])
                answer={'intent':'analyze','plan':result['plan'],'result':result,'message':'Extract created from a validated selection.','mode':'extract builder'}
            else:
                question=pending['question']
                from .working_analysis import recent_result
                previous=recent_result(s.history)
                if previous:
                    from .charts import effective
                    previous={**previous,'presentation':effective(previous['result'],previous.get('presentation') or presentation_for(previous['result']))}
                choices={**s.get('confirmed_institutions',{}),**pending.get('institution_choices',{})}
                if s.use_ai:
                    from .intent_router import handle
                    answer=handle(question,previous,s.model_choice,s.history,ask,
                                  overrides=s.get('chart_formats',{}),institution_choices=choices)
                else:
                    from .purpose import prepare,direct
                    answer=direct(prepare(question))
                    if answer is None:
                        report('Checking whether this is a display change…')
                        answer=adjust_presentation(question,previous)
                from .working_analysis import results
                for edited in results(answer or {}):
                  if edited.get('mode')=='presentation adjustment':
                    from .charts import commit
                    commit(edited['result'],edited['presentation'])
                    s.chart_overrides.pop(edited['result']['result_id'],None)
                if answer is None:
                    args={'conversation':s.history}
                    if choices:args['institution_choices']=choices
                    answer=ask(question,s.last_plan,s.use_ai,s.model_choice,**args)
                if answer.get('institution_identity'):s.confirmed_institutions={**s.get('confirmed_institutions',{}),**answer['institution_identity']['confirmed_choices']}
                if answer.get('institution_confirmation'):s.institution_pending=answer['institution_confirmation']
            if answer.get('mode')!='presentation adjustment':answer=finalize_answer(answer,question)
        s.history=(s.history+[{'question':question,'answer':answer}])[-30:]
        # Revision identifies completed exchanges/clarification controls;
        # it must never become the transcript container's identity.
        s.transcript_revision+=1
        if answer.get('working_analysis',{}).get('artifact'):
            s.last_plan=answer['working_analysis']['artifact']['subject']['plan']
        elif answer.get('observation_plan'):s.last_plan=answer['result'].get('observation_plan',answer['observation_plan']) if answer.get('result') else answer['observation_plan']
        elif answer.get('catalog_plan'):s.last_plan=answer['catalog_plan']
        elif answer.get('plan'):s.last_plan=answer['plan']
        elif answer.get('catalog_context'):s.last_plan=answer['catalog_context']
        elif answer.get('catalog_plan'):s.last_plan=answer['catalog_plan']
        elif answer.get('catalog_matches') is not None:s.last_plan=None
        s.ideas_epoch+=1
        s.pending_action=None
    except ValueError as exc:
        s.request_error=str(exc);s.pending_action=None
    except Exception as exc:
        if 'specified API usage limits' in str(exc):
            s.request_error='The Anthropic account has reached its configured API usage limit. AI requests require restored account access; offline examples and the extract builder remain available.'
        elif type(exc).__name__ in {'NotFoundError','PermissionDeniedError','AuthenticationError'}:
            s.request_error='The selected model is not available to this API credential. Check account/model access under About this prototype, or use offline examples and the extract builder.'
        else:s.request_error='The request could not finish. No partial result was published. Check model/network access or use the extract builder.'
        s.pending_action=None


def example_buttons(topic,prefix,compact=False):
    for ex in topic['examples']:
        with st.container(key='example_row_'+prefix+'_'+ex['id']):
            if compact:
                st.caption(ex['purpose'].upper())
                st.button(ex['question'],key=prefix+'_'+ex['id'],on_click=queue_example,args=(ex['id'],),width='stretch')
            else:
                category,question=st.columns([1,4],vertical_alignment='center')
                category.caption(ex['purpose'].upper())
                question.button(ex['question'],key=prefix+'_'+ex['id'],on_click=queue_example,args=(ex['id'],),width='stretch')


def render_ideas():
    s=st.session_state;content=topics();mapping={t['id']:t for t in content}
    with st.container(border=True,key='ideas_panel',height='stretch'):
        title,collapse=st.columns([5,1],vertical_alignment='center')
        title.subheader('Need ideas?')
        collapse.button('‹',key='collapse_ideas',on_click=toggle_panel,args=('ideas_open',),help='Collapse ideas panel')
        st.caption('Choose a topic, then try a sample question.')
        selected=st.selectbox('Choose a topic',list(mapping),index=list(mapping).index(s.topic_id),format_func=lambda t:mapping[t]['subtitle'],key='ideas_topic_widget',on_change=copy_widget,args=('ideas_topic_widget','topic_id'))
        example_buttons(mapping[selected],'ideas',compact=True)


def render_download_views(result,key):
    with st.expander('Extract layout: one row per institution and year'):
        try:
            wide=compatible_wide(result)
            st.caption('Compatible measures are columns. Status columns retain missing/not-collected information. Units and methodology are in the main Excel/provenance downloads.')
            st.dataframe(wide,hide_index=True,width='stretch')
            st.download_button('Download institution-year CSV',wide.map(_safe).to_csv(index=False).encode('utf-8-sig'),file_name='ipeds-'+result['result_id']+'-institution-year.csv',mime='text/csv',key=key+'_wide')
        except ValueError as exc:st.info(str(exc))


def render_institution_confirmation():
    from .institution_confirmation import candidates
    s=st.session_state;p=s.institution_pending;selected={};epoch=s.transcript_revision
    for i,item in enumerate(p['unresolved']):
        st.write('Institution: '+item['text'])
        selector=st.empty()
        refine=st.text_input('None of these? Refine by name, city/state or UNITID',key=f'inst_refine_{epoch}_{i}')
        options=candidates(refine) if refine.strip() else item['candidates']
        if not options:st.caption('No plausible matches. Enter a fuller name, location or UNITID above.')
        selected[item['key']]=selector.selectbox('Which institution did you mean?',options,index=None,placeholder='Select an institution',format_func=institution_label,key=f'inst_choice_{epoch}_{i}_{refine}')
    a,b=st.columns(2)
    if a.button('Continue',key='institution_continue'):
        if any(v is None for v in selected.values()):st.warning('Select an institution for each name, or refine the search.')
        else:
            s.confirmed_institutions={**s.get('confirmed_institutions',{}),**p['choices'],**selected}
            s.pop('institution_pending',None)
            s.history=s.history[:-1]
            s.pending_action={'type':'question','question':p['question'],'institution_choices':{**p['choices'],**selected}}
            st.rerun()
    if b.button('Cancel',key='institution_cancel'):
        s.pop('institution_pending',None)
        s.history[-1]['answer']={'intent':'clarify','message':'Cancelled. No analysis ran.'}
        s.transcript_revision+=1;st.rerun()


def render_answer(answer,key,compact=True):
    s=st.session_state
    if answer.get('result'):
        from .intent_checks import check_result,IntentMismatch
        try:check_result(answer['result'])
        except IntentMismatch as exc:
            st.warning(str(exc));return
    if answer.get('interpreted_as'):st.caption('Interpreted as: '+answer['interpreted_as'])
    if answer.get('message'):st.write(answer['message'])
    for index,task in enumerate(answer.get('task_results',[]),1):
        st.markdown('**'+str(index)+'. '+task['request']+'**')
        st.caption(task['status'].replace('_',' ').capitalize())
        render_answer(task['answer'],key+'_task_'+task['id'],compact=True)
    if answer.get('coverage'):
        with st.expander('Verified source coverage',expanded=False):st.json(answer['coverage'])
    for index,section in enumerate(answer.get('documentation_sections',[])):
        with st.expander('Requested definition and documentation',expanded=True):
            render_answer(section,key+'_documentation_'+str(index),compact=True)
    if answer.get('institution_identity',{}).get('labels'):st.caption('Institution: '+'; '.join(label.split(' · UNITID')[0] for label in answer['institution_identity']['labels']))
    brief=answer.get('analysis_brief')
    if brief and brief.get('options'):
        from .analysis_clarification import latest
        current=latest(s.get('history',[]))
        if brief['status'] in {'pending','failed'} and current is brief:
            for col,option in zip(st.columns(len(brief['options'])),brief['options']):
                col.button(('Try optional proxy ' if brief.get('coverage_gap') else 'Use ')+option['id'],key=key+'_choice_'+option['id'],on_click=queue_analysis_choice,args=(brief['id'],option['id']))
            st.caption('Optional: try a proxy, revise the request, or ask another question.' if brief.get('coverage_gap') else 'Choose an option, or type a change to refine it.')
        if not answer.get('result'):
            with st.popover('Analysis scope & definitions'):
                st.write(brief['goal'])
                for decision in brief['confirmed_decisions']:
                    st.write(decision['interpretation'])
                for option in brief['options']:
                    if brief.get('selected_option') and option['id']!=brief['selected_option']:continue
                    st.markdown('**'+option['id']+'. '+option['label']+'**')
                    for note in option['qualifications']:st.write(note)
                    for definition in option['evidence']['definitions']:
                        st.caption(definition.get('table_name','')+' · '+definition.get('variable_name',''))
                        st.write(definition.get('long_description') or definition.get('title',''))
    if 'result' in answer:
        result=answer['result'];rid=result['result_id'];presentation=answer.get('presentation') or presentation_for(result)
        show=s.chart_overrides.get(rid,presentation['chart_type']!='none')
        render_result(result,key,show_chart=show,presentation=presentation,compact=compact)
        for index,related in enumerate(answer.get('related_analyses',[])):
            render_answer(related,key+'_related_'+str(index),compact=compact)
        if result.get('result_schema_version')==2:return
        if compact:return
        render_download_views(result,key)
        a,b=st.columns(2)
        if a.button('Show table only' if show else 'Visualize this data',key=key+'_visualize'):
            s.chart_overrides={**s.chart_overrides,rid:not show};st.rerun()
        b.button('Edit institutions, measures or years',key=key+'_edit',on_click=seed_builder)
    elif 'catalog_proposal' in answer:render_catalog_proposal(answer['catalog_proposal'],key)
    elif 'catalog_matches' in answer:
        with st.popover('Definitions & sources'):
            for record in answer['catalog_matches']:
                st.markdown('**'+record['title']+'**')
                st.caption(record['release_id']+' · '+(record['table_name'] or '')+' · '+(record['variable_name'] or ''))
                st.write(record['body'][:1800])
    elif 'evidence' in answer:
        if answer.get('mode') in {'data discovery','source definition'}:
            if answer.get('discovery_narrative',{}).get('status')=='fallback':
                st.caption('The AI rewrite was unavailable or did not pass checks. Showing the verified catalog details.')
            with st.popover('Definitions & sources'):
                if answer.get('discovery',{}).get('template_message'):
                    with st.expander('Detailed catalog coverage'):st.write(answer['discovery']['template_message'])
                render_evidence(answer['evidence'],key)
                if answer.get('discovery_narrative') or answer.get('discovery',{}).get('interpretation'):
                    with st.expander('Answer construction and source checks'):
                        st.json({'interpretation':answer.get('discovery',{}).get('interpretation'),
                            'narrative':answer.get('discovery_narrative'),'model_usage':answer.get('model_usage'),'latency':answer.get('latency')})
        else:render_evidence(answer['evidence'],key)
    if not compact and answer.get('model_usage'):
        with st.expander('Model usage and estimated API cost'):
            u=answer['model_usage']
            cost=f"${u['estimated_api_usd']:.5f}" if u.get('estimated_api_usd') is not None else 'unavailable (provider usage not returned)'
            st.write(f"{MODEL_OPTIONS.get(u['model'],u['model'])} · {u['calls']} call(s) · {u['latency_seconds']:.1f}s · estimated {cost}")
            token_text=lambda name:f"{u[name]:,}" if u.get(name) is not None else 'unavailable'
            st.caption(f"Input: {token_text('input_tokens')}; output including reasoning: {token_text('output_tokens')}; cache read: {token_text('cache_read_input_tokens')}. {u.get('pricing_basis','Configured API estimate; unavailable usage is not treated as zero.')}")
            if answer.get('model_policy'):st.json(answer['model_policy'],expanded=False)


def render_home():
    s=st.session_state
    st.title('Discover what college data can tell you')
    st.write('Explore admissions, enrollment, costs, outcomes, and more using federal IPEDS data.')
    st.button('Ask a question →',type='primary',key='home_ask',on_click=navigate)
    st.caption('10 annual releases · 2015–16 Final through 2024–25 Provisional')
    st.subheader('Start with a topic');st.write('Choose a topic to learn what is available and find questions to try.')
    content=topics()
    for start in [0,3]:
        for col,topic in zip(st.columns(3),content[start:start+3]):
            with col:
                with st.container(border=True,key='home_card_'+topic['id'],height='stretch' if start==0 else 'content'):
                    st.subheader(topic['icon']+' '+topic['title']);st.caption(topic['subtitle']);st.write(topic['summary'])
                    st.button('Explore topic →',key='topic_'+topic['id'],on_click=open_topic,args=(topic['id'],))
        if s.topic_open and s.topic_id in [t['id'] for t in content[start:start+3]]:
            topic=next(t for t in content if t['id']==s.topic_id)
            with st.container(border=True,key='topic_details'):
                heading,close=st.columns([20,1],vertical_alignment='center')
                heading.subheader(topic['title'] if topic['title'].casefold()==topic['subtitle'].casefold() else topic['title']+' · '+topic['subtitle'])
                close.button('×',key='close_topic',on_click=close_topic,help='Close topic')
                st.write(topic['description']);st.info(topic['scope'])
                example_buttons(topic,'home')
                st.button('Ask your own question about '+topic['subtitle'].lower(),key='home_own',on_click=navigate)
    st.caption('IPEDS is collected by the National Center for Education Statistics. Explore all supplied topics; Ask & Analyze can answer additional questions when their source definitions and calculations can be verified.')


def render_chat():
    s=st.session_state
    pending=s.get('pending_action')
    if pending:
        if 'scroll_request' not in pending:
            s.scroll_request_serial=s.get('scroll_request_serial',0)+1
            pending['scroll_request']=s.scroll_request_serial
        for state_key in list(s):
            if state_key.endswith('_format_open'):s[state_key]=False
    pending_slot=None
    heading,control=st.columns([8.5,1.5],vertical_alignment='top')
    with heading.container(key='chat_heading'):
        st.title('What would you like to learn?')
    control.button('Hide Menu' if s.app_banner_open else 'Expand Menu',icon=':material/keyboard_arrow_up:' if s.app_banner_open else ':material/keyboard_arrow_down:',icon_position='right',key='hide_app_banner' if s.app_banner_open else 'show_app_banner',on_click=toggle_panel,args=('app_banner_open',),help='Collapse header and introduction' if s.app_banner_open else 'Expand header and introduction')
    with st.container(key='chat_introduction'):
        st.write('Ask about one or many institutions, for one year, selected years, or a range.')
    st.markdown('<div class="intro-rule"></div>',unsafe_allow_html=True)
    with st.container(key='panel_restore_controls'):
        controls_left,controls_right=st.columns(2)
        if not s.ideas_open:controls_left.button('› Ideas',key='show_ideas',on_click=toggle_panel,args=('ideas_open',))
        if not s.tools_open:
            with controls_right.container(horizontal=True,horizontal_alignment='right'):
                st.button('Tools ‹',key='show_tools',on_click=toggle_panel,args=('tools_open',))
    # Keep column identities/positions fixed across reruns. Moving the transcript
    # to a different column leaves stale old content visible until reconciliation.
    with st.container(key='panel_visibility'):
        hidden=[]
        if not s.ideas_open:hidden.append('[data-testid="stColumn"]:has(.st-key-ideas_panel)')
        if not s.tools_open:hidden.append('[data-testid="stColumn"]:has(.st-key-tools_panel)')
        st.html('<style>'+(','.join(hidden)+'{display:none!important}' if hidden else '')+'</style>')
    panels=st.columns([1,4.5,1],gap='medium')
    with panels[0]:render_ideas()
    with panels[1],st.container(key='chat_workspace',height='stretch'):
        if s.get('request_error'):st.error(s.request_error)
        editing=any(s.get(k) for k in s if k.endswith('_format_open'))
        from .transcript_scroll import render as scroll_transcript
        scroll_transcript(s.get('scroll_request_serial',0),editing)
        with st.container(height=500,border=False,key='conversation_messages',autoscroll=False):
            for i,item in enumerate(s.history):
                with st.chat_message('user'):st.write(item['question'])
                with st.chat_message('assistant'):render_answer(item['answer'],f'answer_{i}_{item["answer"].get("result",{}).get("result_id","discovery")}')
            if s.get('institution_pending'):
                with st.chat_message('assistant'):render_institution_confirmation()
            if pending:
                question=example_by_id(pending['id'])['question'] if pending['type']=='example' else pending.get('question','Preparing your data extract…')
                with st.chat_message('user'):st.write(question)
                pending_slot=st.empty()
        with st.container(horizontal=True,vertical_alignment='center',gap='small',key='chat_composer'):
            question=st.chat_input('Ask a follow-up question…' if s.history else 'Ask a question about IPEDS data…',max_chars=4000,key='followup_question' if s.history else 'initial_question',disabled=bool(pending or s.get('institution_pending')))
            if s.history or s.get('request_error') or s.get('institution_pending'):
                st.button('Clear conversation',key='clear_chat',type='tertiary',icon=':material/delete_sweep:',on_click=clear_conversation,disabled=bool(pending),help='Clear messages, errors and remembered conversation choices.')
        if question and question.strip():s.pending_action={'type':'question','question':question};st.rerun()
        if not s.history:
            st.caption('Request a table, CSV extract or chart. '+(MODEL_OPTIONS[s.model_choice]+' · AI interprets each typed request, including chart edits.' if s.use_ai else 'Offline starter parser; use the builder for precise selections.'))
    with panels[-1],st.container(border=True,key='tools_panel'):
            title,collapse=st.columns([5,1],vertical_alignment='center')
            title.subheader('Analysis tools')
            collapse.button('›',key='collapse_tools',on_click=toggle_panel,args=('tools_open',),help='Collapse analysis tools panel')
            render_tools()
    if pending_slot is not None:
        # Redraw the entire workspace before a slow provider call. Otherwise
        # Streamlit leaves the previous page stale/dimmed throughout the wait.
        # The placeholder keeps the spinner in the assistant's transcript bubble.
        with pending_slot.container(),st.chat_message('assistant'):
            run_pending()
        st.rerun()


def render_tools():
    s=st.session_state
    if not s.get('development_mode',False):
        st.info('**Under development**\n\nThese tools are not ready for use. Please use the chat to ask questions, analyze data and create charts.')
        return
    with st.container():
        st.caption('Development mode · unfinished tools are visible for testing.')
        st.caption('Build an extract or look up a definition.')
        with st.container(border=True,key='extract_tool',gap='small'):
            st.markdown('<div class="tool-card-copy"><h3>Build a data extract</h3><p>Choose institutions, measures, and years. Preview and download data.</p></div>',unsafe_allow_html=True)
            st.button('Open builder →',key='open_builder',on_click=seed_builder,width='stretch')
        with st.container(border=True,key='definitions_tool',gap='small'):
            st.markdown('<div class="tool-card-copy"><h3>Browse definitions</h3><p>Find source tables, variables, and definitions in the IPEDS codebooks.</p></div>',unsafe_allow_html=True)
            st.button('Search definitions →',key='open_definitions',on_click=navigate,args=('Ask & Analyze','definitions'),width='stretch')
        st.caption('Your conversation is preserved when you open a tool.')
        if s.history:st.button('New conversation',key='new_conversation',on_click=clear_conversation)


def render_definitions():
    s=st.session_state
    st.button('← Back to conversation',key='definitions_back',on_click=navigate)
    st.button('Return to extract builder',key='definitions_builder',on_click=navigate,args=('Ask & Analyze','builder'))
    st.title('Browse definitions');st.write('Search documentation to learn what a field means and which table contains it. Use the conversation or extract builder for institution statistics.')
    if s.definition_seed:s.codebook_search_query=s.definition_seed;s.definition_seed=''
    with st.form('codebook_search_form'):
        query=st.text_input('Topic, table, or variable name',value='graduate enrollment',key='codebook_search_query',max_chars=4000)
        years=st.multiselect('Release years (empty = all ten)',list(range(2015,2025)),default=[2024],key='codebook_search_years')
        include=st.checkbox('Also search coded categories and release documentation',key='codebook_search_other')
        submitted=st.form_submit_button('Search codebooks')
    if submitted:
        s.pop('codebook_search_result',None)
        if not query.strip():st.info('Enter a topic, table, or variable name.')
        else:
            try:s.codebook_search_result={'query':query,'years':years,'records':search(query,years,40,kinds=None if include else ['table_definition','variable_definition'])}
            except Exception:st.error('The local catalog search could not finish. Try a narrower query.')
    if 'codebook_search_result' in s:
        r=s.codebook_search_result;st.write('**Results for '+r['query']+'**');render_evidence(r['records'],'codebook_browse',select_one=True)


def render_builder():
    s=st.session_state;specs=measures();content=topics();mapping={t['id']:t for t in content}
    st.button('← Back to conversation',key='builder_back',on_click=navigate)
    st.title('Build a data extract');st.write('Choose your institutions, measures, and time period. Preview before downloading.')
    steps=['Institutions','Measures','Years','Preview & download']
    for i,(col,label) in enumerate(zip(st.columns(4),steps)):
        col.button(str(i+1)+' · '+label,key='step_'+str(i),on_click=set_step,args=(i,),type='primary' if s.extract_step==i else 'secondary',width='stretch')
    with st.container(border=True):
        if s.extract_step==0:
            st.subheader('Institutions — select one or more')
            st.caption('Type in the selection field to autocomplete a name or UNITID, then explicitly choose a match. Each label includes city/state and UNITID. Names use the latest available record and are checked in each requested year.')
            query=st.text_input('Find an institution',placeholder='Optional narrower filter: type Smith and press Enter',key='institution_query')
            matches=institution_matches(query) if query.strip() else sorted(institution_index(),key=lambda i:institution_index()[i]['name'])
            options=list(dict.fromkeys(s.extract_ids+matches))
            if 'builder_inst_widget' not in s:s.builder_inst_widget=s.extract_ids[:]
            st.multiselect('Institutions — type to search and select one or more',options,format_func=institution_label,key='builder_inst_widget',on_change=copy_widget,args=('builder_inst_widget','extract_ids'),max_selections=30,placeholder='Type Yale, Smith, or a UNITID; choose exact matches')
            if query and not matches:st.info('No name match. Try fewer words or a UNITID.')
            st.button('Add Ivy League comparison group',key='add_ivy',on_click=add_ivy)
            st.caption(f'{len(s.extract_ids)} institution(s) selected · up to 30 per request. Group members remain individually removable.')
        elif s.extract_step==1:
            left,right=st.columns([3,1])
            with left:
                st.subheader('What data do you need?')
                query=st.text_input('Search a concept, question, or variable name',placeholder='Try admission rate, graduate enrollment, or APPLCN',key='measure_query')
                topic=st.radio('Topic filter',['all']+list(mapping),format_func=lambda t:'All topics' if t=='all' else mapping[t]['subtitle'],horizontal=True,key='measure_topic')
                count=st.slider('Maximum matches shown',3,36,6,step=3,key='measure_limit')
                matches=measure_matches(query,topic,count)
                st.caption('Top reviewed measures. Refine the search or increase the limit. Your selections stay across searches.')
                if not matches:st.info('No reviewed match. Explore source definitions below.')
                for metric in matches:
                    spec=specs[metric]
                    with st.container(border=True):
                        title,action=st.columns([4,1]);title.markdown('**'+spec['label']+'**')
                        title.caption('Ready to extract · '+spec['unit']+' · observations '+min(spec['annual'])+'–'+max(spec['annual']))
                        action.button('✓ Added' if metric in s.extract_metrics else '+ Add',key='measure_add_'+metric,on_click=toggle_measure,args=(metric,),disabled=metric not in s.extract_metrics and len(s.extract_metrics)>=12)
                        with st.expander('Definition & sources',key='measure_detail_'+metric):
                            st.write(spec['definition']);st.write('Source columns: '+', '.join(spec['columns']))
                            st.caption('Formula: '+spec['expression']+' · Annual tables: '+', '.join(dict.fromkeys(a['table'] for a in spec['annual'].values())))
                with st.expander('Explore source variables not yet mapped'):
                    st.caption('Discovery only. Definitions need a reviewed analytical plan before they can be added to an extract.')
                    if query.strip():
                        for record in search(query,[2024],limit=6,kinds=['variable_definition','table_definition']):
                            st.write('**'+record['title']+'** · '+record['table_name']+' · '+(record['variable_name'] or 'table'))
                            st.button('Inspect source definition',key='inspect_'+str(record['record_id']),on_click=see_definition,args=(record['variable_name'] or record['table_name'],))
                    else:st.caption('Enter a search above to see source candidates.')
            with right:
                st.subheader('Your extract');st.caption(f'{len(s.extract_metrics)} measure(s) selected · up to 12')
                for metric in s.extract_metrics:st.button(specs[metric]['label']+' ×',key='remove_'+metric,on_click=toggle_measure,args=(metric,),width='stretch')
                st.caption('Next: choose one year, selected years, or a range.')
        elif s.extract_step==2:
            st.subheader('Choose your time period')
            if 'builder_basis_widget' not in s:s.builder_basis_widget=s.extract_time_basis
            basis=st.selectbox('What do the years mean?',['observation','entry_cohort','class'],format_func=lambda x:{'observation':'Observation year / reporting-period end','entry_cohort':'Entering cohort — six-year graduation only','class':'Nominal class-of — admissions/SAT only'}[x],key='builder_basis_widget',on_change=copy_widget,args=('builder_basis_widget','extract_time_basis'))
            options=list(range(2009,2019)) if basis=='entry_cohort' else list(range(2019,2029)) if basis=='class' else list(range(2015,2025))
            if 'builder_year_mode_widget' not in s:s.builder_year_mode_widget=s.extract_year_mode
            mode=st.radio('Select years',['One year','Selected years','Year range'],horizontal=True,key='builder_year_mode_widget',on_change=copy_widget,args=('builder_year_mode_widget','extract_year_mode'))
            current=[y for y in s.extract_years if y in options] or [options[-1]]
            if mode=='One year':ys=[st.selectbox('Year',options,index=options.index(current[-1]),key='extract_one_year_'+basis)]
            elif mode=='Selected years':ys=st.multiselect('Years — select one or more',options,default=current,key='extract_selected_years_'+basis)
            else:
                a,b=st.columns(2);start=a.selectbox('From',options,index=0,key='extract_from_'+basis);end=b.selectbox('Through',options,index=len(options)-1,key='extract_through_'+basis)
                ys=list(range(start,end+1)) if end>=start else []
                if end<start:st.warning('Choose an end year on or after the start year.')
            s.extract_years=ys
            st.info(f'{len(ys)} year(s) selected. Observations: 2015–2024; graduation entering cohorts: 2009–2018. Latest release provisional.')
            if s.extract_metrics:
                with st.expander('Reporting-period and population definitions'):
                    for m in s.extract_metrics:st.write('**'+specs[m]['label']+'** — '+specs[m]['definition'])
        else:
            st.subheader('Preview your selection')
            st.write('**Institutions:** '+('; '.join(institution_index()[i]['name'] for i in s.extract_ids) or 'None selected'))
            st.write('**Measures:** '+(', '.join(specs[m]['label'] for m in s.extract_metrics) or 'None selected'))
            st.write('**Years:** '+(', '.join(map(str,s.extract_years)) or 'None selected')+' · '+s.extract_time_basis)
            try:
                plan=extract_plan(s.extract_metrics,s.extract_ids,s.extract_years,s.extract_time_basis)
                st.caption(f'Up to {len(s.extract_ids)*len(s.extract_metrics)*len(s.extract_years)} cells. Missing/not-collected cells stay explicit. Preview and downloads use the same result.')
                if st.button('Preview data',type='primary',key='preview_extract'):
                    s.pending_action={'type':'extract','plan':plan.__dict__};st.rerun()
            except ValueError as exc:st.info(str(exc))
            if s.get('request_error'):st.error(s.request_error)
            if s.extract_result:
                st.subheader('Latest generated extract');st.caption('This result retains its original executed scope below. Editing selections does not change it until Preview data runs again.')
                render_answer({'result':s.extract_result},'builder_result',compact=False)
        st.divider();back,forward=st.columns(2)
        back.button('← Previous step',key='previous_step',on_click=set_step,args=(max(0,s.extract_step-1),),disabled=s.extract_step==0)
        forward.button('Next: '+steps[min(3,s.extract_step+1)]+' →',key='next_step',on_click=set_step,args=(min(3,s.extract_step+1),),disabled=s.extract_step==3,type='primary')


def render_about():
    s=st.session_state
    st.button('← Back to conversation',key='about_back',on_click=navigate)
    st.title('About this prototype');st.write('Local IPEDS codebook discovery and source-reviewed analytical extracts across ten annual releases.')
    st.info('Local source releases: 2015–16 through 2024–25; latest release provisional. Observation periods and entering cohorts vary by survey. Verified national and sector aggregates are available; unresolved methods remain under review.')
    with st.expander('Model settings',expanded=True):
        st.selectbox('Model strategy',list(MODEL_OPTIONS),index=list(MODEL_OPTIONS).index(s.model_choice),format_func=lambda x:MODEL_OPTIONS[x],key='settings_model',on_change=copy_widget,args=('settings_model','model_choice'))
        st.caption('Automatic uses Haiku for interpretation and reviewed numerical planning, Sonnet for catalog planning and discovery writing. A rejected interpretation gets one Sonnet retry. All source and chart checks remain active.')
        st.toggle('Use conversational AI',value=s.use_ai,disabled=not bool(api_key()),key='settings_ai',on_change=copy_widget,args=('settings_ai','use_ai'))
        st.caption('AI sends your question, up to 12 recent conversation turns with analytical plans and bounded definitions, and relevant codebook excerpts to Anthropic. Memory lasts for this session; New conversation clears it. Queries and calculations stay local. Access depends on your API account.')
    with st.expander('Developer settings'):
        st.toggle('Enable development mode',value=s.development_mode,key='settings_development_mode',on_change=copy_widget,args=('settings_development_mode','development_mode'),help='Show unfinished Analysis Tools controls for development and testing.')
        st.caption('Applies to this browser session. Turn it off to hide the unfinished Analysis Tools controls.')
    st.subheader('Evaluation and coverage');st.write('229 Yale matches and 13 retained numeric discrepancies across 242 supported comparisons; 36 cells await the race-unknown rule. Retrieval agreement does not certify arbitrary conversation accuracy.')
    path=BASE/'evaluations/results/yale_cases.json'
    if path.exists():
        differences=[r for r in json.loads(path.read_text(encoding='utf-8')) if r['status']=='mismatch']
        st.dataframe(pd.DataFrame(differences)[['family','metric','observation_year','expected','actual','difference']],hide_index=True,width='stretch')
    for file in ['prototype_verification.json','prototype_live_smoke.json','prototype_model_comparison.json']:
        path=BASE/'evaluations'/file
        if path.exists():
            with st.expander(file.replace('_',' ').replace('.json','')):st.json(json.loads(path.read_text(encoding='utf-8')))


def main():
    st.set_page_config(page_title='IPEDS Research Companion',page_icon='📚',layout='wide',initial_sidebar_state='collapsed')
    page_styles='''[data-testid="stMainBlockContainer"]{max-width:none;padding-left:2rem;padding-right:2rem}
    @media(max-width:750px){[data-testid="stMainBlockContainer"]{padding-left:1rem;padding-right:1rem}}''' if st.session_state.get('main_page')=='Ask & Analyze' else ''
    st.markdown('''<style>.block-container{max-width:1400px;padding-top:3.5rem;padding-bottom:2rem}
    .stApp,header[data-testid="stHeader"]{background:#F8F7F3}
    div[data-testid="stVerticalBlockBorderWrapper"]{background:white;border-radius:14px}
    h1,h2,h3{color:#183344;letter-spacing:-.025em}div[data-testid="stChatMessage"]{background:white;border:1px solid #dce5df;border-radius:14px}
    div[data-testid="stMetricValue"]{font-size:1.65rem}div[data-testid="stForm"]{background:white}
    .brand{font-size:20px;font-weight:750;color:#183344;line-height:1.2}.eyebrow{display:inline-block;margin-left:.6rem;font-size:10px;font-weight:400;text-transform:uppercase;letter-spacing:.06em;color:#55716a}
    .banner-rule{border-bottom:1px solid #dce5df;margin:.2rem 0 .6rem}
    .intro-rule{border-bottom:1px solid #e1e6e3;margin:0 0 .35rem}
    [class*="st-key-example_row_"] button{justify-content:flex-start;text-align:left}
    [class*="st-key-example_row_"] button>div{justify-content:flex-start}
    [class*="st-key-example_row_"] button p{text-align:left}
    [class*="st-key-example_row_"] [data-testid="stCaptionContainer"]{color:#65736f;font-size:.75rem;letter-spacing:.04em}
    .st-key-main_navigation button{border:0;border-radius:0;background:transparent;box-shadow:none;color:#65736f;border-bottom:3px solid transparent}
    .st-key-main_navigation button[kind="primary"]{color:#183344;border-bottom-color:#28766b;font-weight:700}
    .st-key-main_navigation button:hover{background:#edf2ef;color:#183344}
    .st-key-close_topic button{border:0;background:transparent;min-height:2rem;padding:0;width:2rem;color:#65736f}
    .st-key-close_topic button p{font-size:1.4rem}
    .st-key-collapse_ideas button,.st-key-collapse_tools button{width:1.8rem;min-width:1.8rem;min-height:1.8rem;padding:0;border-color:#c9d6d0;background:transparent;color:#55716a}
    .st-key-collapse_ideas button p,.st-key-collapse_tools button p{font-size:1.4rem}
    .st-key-show_ideas button,.st-key-show_tools button{min-height:1.8rem;padding:.15rem .6rem;font-size:.8rem}
    .st-key-extract_tool,.st-key-definitions_tool{padding:1.15rem!important}
    .tool-card-copy h3{padding:0;margin:0 0 .9rem;font-size:1.3rem;line-height:1.35}
    .tool-card-copy p{margin:0;line-height:1.65}
    /* The transcript takes the remaining space; the composer never scrolls with it. */
    .st-key-hide_app_banner button,.st-key-show_app_banner button{width:8rem;min-width:8rem;min-height:1.5rem;height:1.5rem;padding:0 .25rem;border:0;background:transparent;color:#7b8784;box-shadow:none}
    .st-key-hide_app_banner button:hover,.st-key-show_app_banner button:hover{background:#edf2ef;color:#183344}
    .st-key-hide_app_banner button p,.st-key-show_app_banner button p{font-family:"Source Sans",sans-serif;font-size:.875rem;font-weight:400;line-height:1.6}
    [data-testid="stMainBlockContainer"]{--banner-reclaimed:0px}
    [data-testid="stMainBlockContainer"]:has(.st-key-show_app_banner){--banner-reclaimed:3rem}
    /* Keep banner children mounted: an empty keyed block can retain stale
       content during reconciliation. Collapse the actual layout wrappers. */
    [data-testid="stMainBlockContainer"]:has(.st-key-show_app_banner) [data-testid="stLayoutWrapper"]:has(>.st-key-app_header),
    [data-testid="stMainBlockContainer"]:has(.st-key-show_app_banner) [data-testid="stLayoutWrapper"]:has(>.st-key-chat_introduction),
    [data-testid="stMainBlockContainer"]:has(.st-key-show_app_banner) .st-key-chat_heading{display:none!important}
    .st-key-chat_workspace{height:calc(100dvh - 20rem + var(--banner-reclaimed));min-height:240px;gap:1rem}
    .st-key-chat_workspace>[data-testid="stLayoutWrapper"]:has(>.st-key-conversation_messages){flex:1 1 0;min-height:0;height:0!important}
    .st-key-conversation_messages{height:100%!important;min-height:0;overscroll-behavior:contain;scrollbar-gutter:stable;overflow-x:hidden;scroll-behavior:auto;overflow-anchor:none;container-type:size;container-name:conversation}
    .st-key-chat_workspace>[data-testid="stLayoutWrapper"]:has(>.st-key-transcript_scroll_driver){display:none}
    [class*="st-key-"][class*="_format_panel"]{max-height:min(480px,70dvh);overflow-y:auto}
    @container conversation (min-height:0px){
      [class*="st-key-"][class*="_format_panel"]{height:min(480px,max(0px,calc(100cqh - 3rem)))!important;max-height:max(0px,calc(100cqh - 3rem))}
    }
    .st-key-chat_workspace>[data-testid="stElementContainer"]{flex-shrink:0}
    @media(max-width:750px){
      [data-testid="stMainBlockContainer"]:has(.st-key-show_app_banner) .st-key-chat_workspace{height:calc(100dvh - 14rem + var(--banner-reclaimed))}
    }
    @media(min-width:751px){
      [data-testid="stMainBlockContainer"]:has(.st-key-chat_workspace){height:calc(100dvh - 3.75rem);min-height:560px;padding-bottom:.5rem}
      [data-testid="stMainBlockContainer"]:has(.st-key-chat_workspace)>[data-testid="stVerticalBlock"]{height:100%;min-height:0}
      [data-testid="stMainBlockContainer"]:has(.st-key-chat_workspace)>[data-testid="stVerticalBlock"]>*{flex-shrink:0}
      [data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>[data-testid="stLayoutWrapper"]:has(.st-key-chat_workspace){flex:1 1 0;min-height:0}
      [data-testid="stHorizontalBlock"]:has(.st-key-chat_workspace),
      [data-testid="stColumn"]:has(.st-key-chat_workspace),
      [data-testid="stColumn"]:has(.st-key-chat_workspace)>[data-testid="stVerticalBlock"],
      [data-testid="stLayoutWrapper"]:has(>.st-key-chat_workspace){height:100%;min-height:0}
      .st-key-chat_workspace{height:100%;min-height:0}
      [data-testid="stColumn"]:has(.st-key-ideas_panel),[data-testid="stColumn"]:has(.st-key-tools_panel){height:100%;min-height:0;overflow-y:auto}
    }
    @media(max-width:750px){.block-container{padding-left:1rem;padding-right:1rem}.brand{font-size:19px}}''' + page_styles + '</style>',unsafe_allow_html=True)
    if not (DATA/'metadata_catalog.sqlite').exists():st.error('Local metadata catalog missing. See ingestion/README.md.');st.stop()
    s=st.session_state
    defaults={'main_page':'Explore IPEDS','app_banner_open':True,'transcript_revision':0,'history':[],'last_plan':None,'topic_id':'admissions','topic_open':False,'active_tool':None,'pending_action':None,'ideas_epoch':0,'extract_step':0,'extract_ids':[],'extract_metrics':[],'extract_years':[2024],'extract_time_basis':'observation','extract_year_mode':'One year','extract_result':None,'model_choice':DEFAULT_STRATEGY,'use_ai':bool(api_key()),'chart_results':[],'definition_seed':''}
    for k,v in defaults.items():
        if k not in s:s[k]=v
    if 'development_mode' not in s:s.development_mode=False
    if 'chart_overrides' not in s:s.chart_overrides={}
    for panel in ['ideas_open','tools_open']:
        if panel not in s:s[panel]=True
    is_chat=s.main_page=='Ask & Analyze' and not s.active_tool
    # A persistent header boundary prevents downstream blocks shifting on collapse.
    with st.container(key='app_header'):
        if is_chat or s.app_banner_open or s.main_page=='Explore IPEDS':
            brand,nav,about,collapse=st.columns([4,4,2,.5],vertical_alignment='top')
            with brand:st.markdown('<div class="brand">IPEDS Research Companion<span class="eyebrow">Local prototype</span></div>',unsafe_allow_html=True)
            with nav:
                with st.container(key='main_navigation'):
                    for col,page,key in zip(st.columns(2),['Explore IPEDS','Ask & Analyze'],['nav_explore','nav_ask']):
                        col.button(page,key=key,on_click=navigate,args=(page,),type='primary' if s.main_page==page else 'secondary',width='stretch')
            with about:st.button('About this prototype',key='nav_about',on_click=navigate,args=('Ask & Analyze','about'),width='stretch')
            if not is_chat and s.main_page!='Explore IPEDS':
                collapse.button('⌃',key='hide_app_banner',on_click=toggle_panel,args=('app_banner_open',),help='Collapse header and introduction')
            st.markdown('<div class="banner-rule"></div>',unsafe_allow_html=True)
        elif not is_chat:
            _,_,_,restore=st.columns([4,4,2,.5],vertical_alignment='top')
            restore.button('⌄',key='show_app_banner',on_click=toggle_panel,args=('app_banner_open',),help='Expand header and introduction')
    if not is_chat:run_pending()
    if s.main_page=='Explore IPEDS':render_home()
    elif s.active_tool=='builder':render_builder()
    elif s.active_tool=='definitions':render_definitions()
    elif s.active_tool=='about':render_about()
    else:render_chat()

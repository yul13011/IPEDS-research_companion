"""Executable application capabilities shared by interpretation and coverage."""
CHART_TYPES=('line','bar','none')


def describe():
    return {'charts':{'line':'Line charts for numerical series',
        'bar':'Horizontal bars, including grouped comparisons',
        'none':'Tables or numerical answers without a chart'},
        'scope':'Only the data loaded in this app; no external data retrieval.',
        'task_limit':6,'coverage':'Loaded releases, reviewed measures and source-documented fields; reported values are a separate check.'}


def answer(requested=''):
    supported=requested in CHART_TYPES if requested else True
    message='I can produce line charts and horizontal bar charts, including grouped bars, or show a table.'
    if requested and not supported:message='The requested chart type ('+requested+') is not supported. '+message
    return {'intent':'capability','mode':'application capabilities','message':message,
        'capability':{'requested_chart':requested,'supported':supported,**describe()}}

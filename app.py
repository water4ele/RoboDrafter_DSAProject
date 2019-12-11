import string, os, sys

from bottle import request, route, run, FormsDict
from bottle import template as view

import robodrafter

# Helper functions
def fill_template(template_str, data):
    ''' Fill ${tag}-demimited tags in `template_str` with data from `data` '''
    tpl = string.Template(template_str)
    return tpl.safe_substitute(data)

# Routes

@route('/', method='GET')
def home():
    '''
    This is the initial view, before the user has clicked "Submit"
    '''

    return view('robo_draft',
        #summary_text='',
        use_text='',
        source_text='',
        # Use an empty FormsDict on initial load so data fields are empty
        form=FormsDict(),
        )

@route('/', method='POST')
def result():
    '''
    This is the result view, after the user has clicked "Submit"
    '''
    data = {k: v for k, v in request.forms.items() if v}
    # summary_text_template = robodrafter.generate_summary_text_template()
    # summary_text = fill_template(summary_text_template, data)
    use_text_template = robodrafter.generate_use_text_template(usesSentences)
    use_text = fill_template(use_text_template, data)

    source_text_template = robodrafter.generate_source_text_template(sourceSentences)
    source_text = fill_template(source_text_template, data)

    return view('robo_draft',
        #summary_text = summary_text,
        use_text=use_text,
        source_text=source_text,
        form=request.forms,
        )

# Main
def initialize():
    global sourceSentences, usesSentences
    python_work_dir = os.path.dirname(os.path.realpath(__file__))
    dataFolder = os.path.abspath(python_work_dir + "/DSA-data1")
    (sourceSentences, usesSentences) = robodrafter.processLiquidity(dataFolder)

if __name__ == '__main__':
    initialize()
    run(host='localhost', port=8080, debug=True, reloader=True)

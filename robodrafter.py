from utility import  GetAllParts, TagUseSentences, TagSourceSentences,GeneratePoints_source,GeneratePoints_use
from functools import reduce
def processLiquidity(FolderPath):
    (beforeTableList,sourcesList, usesList) = GetAllParts(FolderPath)
    labledSourceSentences = [TagSourceSentences(reduce(lambda a, b: a + b, sourcesList, []))]
    sourceSentences = reduce(lambda a, b: a + b, labledSourceSentences, [])
    labledUseSentences = [TagUseSentences(reduce(lambda a, b: a + b, usesList, []))]
    useSentences = reduce(lambda a, b: a + b, labledUseSentences, [])
    return (sourceSentences, useSentences)
def generate_source_text_template(sourceSentences):
    # You should create this template dynamically. This one is just an example.
    # Do use this format of ${variable_name} for the template tags
    template_str = GeneratePoints_source(sourceSentences)
    return template_str

def generate_use_text_template(usesSentences):
    # You should create this template dynamically. This one is just an example.
    # Do use this format of ${variable_name} for the template tags
    template_str  = GeneratePoints_use(usesSentences)
    return template_str

# def generate_summary_text_template():
#     template_str = "We access  ${company_name} as adequate."
#     return template_str
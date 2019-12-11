from nltk import word_tokenize, FreqDist
# from nltk.corpus import stopwords
import os, string, re
import numpy as np
# from scipy.spatial import distance as ssd
# from scipy.cluster.hierarchy import linkage, fcluster
from functools import reduce
from constants import useClusters, sourceClusters, useTags, sourceTags


def GetCompanyNames(companyName):
    # remove anything after comma
    origForm = companyName.split(',')[0]
    companyNames = [origForm]
    stripOffWords = ["Inc.", "S.A.", "Corp.", "Ltd", "LLC", "AG", "AB", "PJSC", "PLC", "Co.", "Group", "AS", "N.V.", "Bhd.", "GmbH", "S.A.S.", "KG", "Holding", "Financial", "L.P.", "LP","Ltd.", "SpA", "Trust", "Tbk.", "Tbk", "Limited", "C.V.","Partnership","Commercial", "School", "Hospital", "Investment", "International", "Services", "Resources","Partners"]
    nextForm = origForm
    endFlag = False
    while not endFlag:
        if len(word_tokenize(nextForm))==1:
            break
        endFlag = True
        for s in stripOffWords:
            nextForm = nextForm.replace(" "+s,"")
            if nextForm not in companyNames:
                companyNames.append(nextForm)
                endFlag = False
                break
    return companyNames


def RemoveHeader(aText):
    check1 = aText.lower().find('\n\nwww.standardandpoors.com')
    if check1 != -1:
        check = check1 + 3
        for i in range(3):
            check = aText.lower().find('\n\n', check) + 3
            if check == 2:
                print('Something is wrong when removing headers')
        unwantedStr = aText[check1:check + 1]
        cleanedText = aText.replace(unwantedStr, ' ')
    else:
        cleanedText = aText
    return cleanedText


def ExtractLiquidity(filePath):
    file = open(filePath, encoding="utf8")
    contents = file.read()
    companyIdx = contents.lower().find('\n')
    companyName = contents[0:companyIdx]
    pfIdx = contents.lower().find('criteria - corporates - project finance')
    if pfIdx != -1:
        file.close()
        return (companyName, 'project finance')
    tableIndex = contents.lower().find('table of contents')
    if tableIndex == -1:
        file.close()
        return (companyName, 'NoTableofContents')
    line1 = contents.lower().find('\n', tableIndex)
    line2 = contents.lower().find('\n', line1 + 1)
    firstSection = contents[line1 + 1:line2] + '\n'
    firstSectionIdx = contents.lower().find(firstSection.lower(), line2)
    liqTableIndex = contents.lower().find("\nliquidity\n", tableIndex) + 2
    if liqTableIndex > firstSectionIdx:
        file.close()
        return (companyName, 'NoLiquidityInTable')
    approximity = contents[liqTableIndex:liqTableIndex + 60]
    newline1 = approximity.find('\n')
    newline2 = approximity.find('\n', newline1 + 1)
    nextItem = approximity[newline1 + 1:newline2] + '\n'
    if nextItem == '\n':
        file.close()
        return (companyName, 'NoNextItem')
    startIdx = contents.lower().find('\nliquidity:', liqTableIndex + 60)
    endIdx = contents.lower().find(nextItem.lower(), startIdx)
    if (startIdx == -1 or endIdx == -1):
        startIdx = contents.lower().find('\nliquidity\n', liqTableIndex + 60)
        endIdx = contents.lower().find(nextItem.lower(), startIdx)
    if startIdx == -1:
        file.close()
        return (companyName, 'NoLiquiditySection')
    LiqSection = contents[startIdx:endIdx]
    if LiqSection == '':
        if contents.lower().find('project finance') != -1:
            LiqSection = 'project finance'
    while LiqSection.lower().find('www') != -1:
        LiqSection = RemoveHeader(LiqSection)
    file.close()
    return (companyName, LiqSection)


def TagData(aText, companyName):
    replaced0 = aText.replace(companyName, '${company_name}')
    replaced00 = re.sub('\d+(\.)?\d*( x|x)', '${ratio}', replaced0)
    replaced1 = re.sub('((US|C|HK|R)?\$|€|BHD|RMB|£|RUB|HK|IDR|SEK|NOK|GEL|KRW|CHF)?\d+(,)?(\.)?\d*(\s)?\w+(illion)',
                       '${currency}${monetary} ${unit}', replaced00)
    replaced2 = re.sub(
        '(January|Feburary|March|April|May|June|July|August|September|November|December|Jan.|Feb.|Dec.)(\s)[1-3]?[0-9](,)?(\s)\d\d\d\d',
        '${date}', replaced1)
    replaced3 = re.sub('(second-quarter|end-)(\s)?\d\d\d\d',
                       '${date}', replaced2)
    replaced4 = re.sub('(January|Feburary|March|April|May|June|July|August|September|November|December)(\s)\d\d\d\d',
                       '${month}', replaced3)
    replaced5 = re.sub('\d\d\d\d', '${year}', replaced4)
    replaced6 = re.sub('next(\s)(\d+|\w+)(\s)(months|years)', '${duration}', replaced5)
    replaced7 = re.sub('in(\s)the(\s)(\d+|\w+) (months|years)', '${duration}', replaced6)
    return replaced7


def ExtractAllValid(FolderPath):
    exceptions = ['', 'project finance', 'NoLiquidityInTable', 'NoTableofContents', 'NoLiquiditySection', 'NoNextItem']
    allFilesPath = [FolderPath + '//' + x for x in os.listdir(FolderPath) if x[-4:] == '.txt']
    # totalFiles = len(allFilesPath)
    allExtracts1 = [ExtractLiquidity(x) for x in allFilesPath]
    allExtracts = [(x, TagData(y, x)) for (x, y) in allExtracts1 if not y in exceptions]
    return allExtracts


def ExtractAllEmpty(FolderPath):
    # Only extract empty cases, no need to look at known exceptions
    allFilesPath = [FolderPath + x for x in os.listdir(FolderPath) if x[-4:] == '.txt']
    allExtracts1 = [ExtractLiquidity(x) for x in allFilesPath]
    allExtracts = [(x, y) for (x, y) in allExtracts1 if y == '']
    return allExtracts


def CombineAllExtracts(allExtracts):
    result = ""
    for currExtract in allExtracts:
        result = result + " " + currExtract
    return result


# GetMostFrequentWords or phrases
def GetMostFrequentWords(extracted, textProcesser, filterFun, topN):
    allwords = textProcesser(extracted)  # textProcesser take in a piece of text and return words or phrases (n-gram)
    # remove punctuation, numeric value and ignoreWords
    cleanedWords = [word.lower() for word in allwords if filterFun(word.lower())]
    all_words = FreqDist(cleanedWords)
    return all_words.most_common()[:topN]


# User defined n-gram as textProcesser
def GetNGram(s, n):
    s = s.lower()
    # Replace all none alphanumeric characters with spaces
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)
    # Break sentence in the token, remove empty tokens
    tokens = [token for token in s.split(" ") if token != ""]
    # Use the zip function to help us generate n-grams
    # Concatentate the tokens into ngrams and return
    ngrams = zip(*[tokens[i:] for i in range(n)])
    return [" ".join(ngram) for ngram in ngrams]


# Extract Bullet Point
def GetTextInBetween(text, beginStr, endStr):
    index1 = text.find(beginStr)
    if index1 == -1:
        return ''
    else:
        index2 = text.find(endStr, index1)
        return text[index1:index2]


def GetFirstItem(extract, beginMark, endMark):
    return GetTextInBetween(extract, beginMark, endMark)


def GetAllItem(extract, beginMark, endMark):
    first = GetFirstItem(extract, beginMark, endMark)
    if first == '':
        return []
    else:
        return [first] + GetAllItem(extract.replace(first, ''), beginMark, endMark)


def GetAllBullet(extract):
    return GetAllItem(extract, '•', '\n')


def ExtractBeforeTable(liquidityText):
    index = liquidityText.lower().find('principal liquidity sources')
    if index == -1:
        aText = liquidityText
    else:
        aText = liquidityText[:index]
    titleIdx1 = aText.lower().find('\nliquidity')
    if titleIdx1 != 0:
        return aText.replace('\n', ' ')
    else:
        titleIdx2 = aText.find('\n', titleIdx1 + 7)
        removedTitle = aText[titleIdx2 + 1:]
        return removedTitle.replace('\n', ' ')


def GetFirstSentence(aText):
    fullstopIdx = aText.find('.')
    if fullstopIdx == -1:
        return ''
    else:
        return aText[:fullstopIdx + 1]


def BreakToSentences(aText):
    first = GetFirstSentence(aText)
    if first == '':
        return []
    else:
        return [first] + BreakToSentences(aText.replace(first, ''))


def ExtractTable(liquidityText):
    index = liquidityText.lower().find('principal liquidity sources')
    index2 = liquidityText.lower().find('bt maturities\n')
    if index == -1:
        return ''
    else:
        if index2 == -1:
            reduced = liquidityText[index:]
        else:
            reduced = liquidityText[index:index2-2]
        return reduced

def tagCompanyName(aTxt, companyNames):
    for s in companyNames:
        if aTxt.find(s)!=-1:
            aTxt = aTxt.replace(s, "${company_name}")
    return aTxt
def GetSourcesUses(companyName,liquidityText):
    companyNames = GetCompanyNames(companyName)
    Table = ExtractTable(liquidityText)
    alist = re.split('\n\n', Table)
    str1 = ""
    str2 = ""
    for i in range(len(alist)):
        if i % 2 == 0:
            str1 = str1 + tagCompanyName(alist[i], companyNames)
        else:
            str2 = str2 + tagCompanyName(alist[i], companyNames)
    str1 = str1.replace('\n', ' ')
    str1 = str1.replace('•', '\n •')
    str2 = str2.replace('\n', ' ')
    str2 = str2.replace('•', '\n •')
    return (str1, str2)


# def GetAllBulletsInTables
def GetSourcesUsesBullets(companyName,liquidityText):
    str1, str2 = GetSourcesUses(companyName,liquidityText)
    sourcesBullets = GetAllBullet(str1)
    usesBullets = GetAllBullet(str2)
    return (sourcesBullets, usesBullets)


def GetAllParts(FolderPath):
    temp = ExtractAllValid(FolderPath)
    extractList = [y for (x, y) in temp]
    beforeTableList1 = [ExtractBeforeTable(x) for x in extractList]
    beforeTableList = [BreakToSentences(x) for x in beforeTableList1]
    bulletsList = [GetSourcesUsesBullets(x,y) for (x,y) in temp]
    sourcesList, usesList = zip(*bulletsList)
    return (beforeTableList, sourcesList, usesList)


def CombineSourceUseList(aList):  # aList is a list of array of strings.
    resultStr = ''
    for x in aList:
        for y in x:
            resultStr = resultStr + " " + y
    return resultStr


def TagUseSentences(sentenceSet):
    results = [tagUseSingleSentence(s) for s in sentenceSet if len(s)<200]
    return reduce(lambda a,b: a+b, results, [])
def tagUseSingleSentence(sentence):
    tags = []
    for (taggingWordSet, taggingNumber) in zip(useClusters, range(len(useClusters))):
        findRes = [1 for t in taggingWordSet if sentence.find(t) != -1]
        if len(findRes) > 0:
            tags.append(taggingNumber)

    if len(tags) == 0:
        return []
    else:
        if len(tags)>1:
            print(tags)
        return [(tags[0], sentence)]

def TagSourceSentences(sentenceSet):
    results = [tagSourceSingleSentence(s) for s in sentenceSet if len(s)<200 and s.find("Share repurchases")==-1 and s.find("government support")==-1]
    return reduce(lambda a,b: a+b, results, [])
def tagSourceSingleSentence(sentence):
    tags = []
    for (taggingWordSet, taggingNumber) in zip(sourceClusters, range(len(sourceClusters))):
        findRes = [1 for t in taggingWordSet if sentence.find(t) != -1]
        if len(findRes) > 0:
            tags.append(taggingNumber)
    if len(tags) == 0:
        return []
    else:
        return [(tags[0], sentence)]


def randomlyDrawAndTag(sentenceset, keywordset, tag):
    while True:
        senStr0 = sentenceset[np.random.randint(len(sentenceset))]
        # Search for placeholder
        phNum = len(re.findall("{monetary}", senStr0))
        if phNum == 1:
            break
    # Search for keyword or the group of similar keywords to keyword
    keyword = GetTheKeyWord(senStr0, keywordset, tag)
    senstr = senStr0.replace("{monetary}", keyword)
    if tag=="{cash}":
        senstr = senstr.replace("{year}", "{date}")
        senstr = senstr.replace("{month}", "{date}")
    elif tag=="{ffo}":
        senstr = senstr.replace("{duration}", "{ffoduration}")
        senstr = senstr.replace("through ${year}", "in the ${ffoduration}")
        senstr = senstr.replace("{year}", "{ffoduration}")
        senstr = senstr.replace("{month}", "{ffoduration}")
    elif tag =="{credit}":
        senstr = senstr.replace("due in ${year}", "due in ${creditMaturity}")
        senstr = senstr.replace("in ${year}", "due in ${creditMaturity}")
        senstr = senstr.replace("due ${year}", "due ${creditMaturity}")
        senstr = senstr.replace("due ${month}", "due ${creditMaturity}")
        senstr = senstr.replace("maturing in ${year}", "maturing ${creditMaturity}")
        senstr = senstr.replace("maturing in ${month}", "maturing ${creditMaturity}")
        senstr = senstr.replace("expiring in ${month}", "expiring on ${creditMaturity}")
        senstr = senstr.replace("matures in ${year}", "maturing ${creditMaturity}")
        senstr = senstr.replace("mature in end of ${year}", "maturing ${creditMaturity}")
        senstr = senstr.replace("matures in ${month}", "maturing ${creditMaturity}")
        senstr = senstr.replace("maturity of ${month}", "maturity of ${creditMaturity}")
        senstr = senstr.replace("maturity of ${year}", "maturity of ${creditMaturity}")
        if senstr.find("{date}")!=-1:
            senstr = senstr.replace("due ${date}","due ${creditMaturity}")
    elif tag in ["{workcapout}","{capex}", "{dividends}","{debt}"]:
        senstr = senstr.replace("${duration}", "next year.")
        senstr = senstr.replace("${year}", "next year.")
        senstr = senstr.replace("${month}", "next year.")
    senstr = senstr.rstrip(" ")
    senstr = senstr.rstrip("and")
    senstr = senstr.rstrip(" ")
    senstr = senstr.rstrip(";")
    senstr = senstr.rstrip(".")
    return senstr


def GetTheKeyWord(sent, keywordSet, tag):
    for keyword in keywordSet:
        if sent.find(keyword) != -1:
            return tag
    return "Not Found"


def GeneratePoints_source(sourceSentences):
    sentenceset1 = [y for (x, y) in sourceSentences if x == 0]
    sentenceset2 = [y for (x, y) in sourceSentences if x == 1]
    sentenceset3 = [y for (x, y) in sourceSentences if x == 2]
    # sentenceset4 = [y for (x,y) in sourceSentences if x == 3]
    return randomlyDrawAndTag(sentenceset3,sourceClusters[2],sourceTags[2]) + ';\r' + randomlyDrawAndTag(sentenceset1, sourceClusters[0], sourceTags[0]) + ';\r' + randomlyDrawAndTag(sentenceset2,  sourceClusters[1], sourceTags[1]) + "."   # +'\r'+randomlyDrawAndTag(sentenceset4, "{monetary}", sourceClusters[3],sourceTags[3])


def GeneratePoints_use(usesSentences):
    sentenceset1 = [y for (x, y) in usesSentences if x == 0]
    sentenceset2 = [y for (x, y) in usesSentences if x == 1]
    sentenceset3 = [y for (x, y) in usesSentences if x == 2]
    sentenceset4 = [y for (x, y) in usesSentences if x == 3]
    # sentenceset5 = [y for (x,y) in sourceSentences if x==4]
    return randomlyDrawAndTag(sentenceset1, useClusters[0], useTags[0]) + ';\r' + randomlyDrawAndTag(sentenceset2, useClusters[1], useTags[1]) + ';\r' + randomlyDrawAndTag(sentenceset3,useClusters[2], useTags[2]) + ';\r' + randomlyDrawAndTag(sentenceset4, useClusters[3], useTags[3])+'.'

# def SimpleBackOffNGram(s, n, disR):
#     allTheGrams = [GetNGram(s, l) for l in range(1, n + 2)]
#     result = [];
#     for i in range(n):
#         lowerGrams = allTheGrams[i]
#         higherGrams = allTheGrams[i + 1]
#         result = result + FilterLowerByHigherNGram(lowerGrams, higherGrams, i == 0, disR)
#     return result
#
#
# def GetCoordinates(aList, aItem):
#     # aList contains arrays of sentences. aItem is a phrase.
#     # GetCoordinates returns [(x,y)] such that aItem appears in the yth sentence in xth array.
#     coordinates = [];
#     for i in range(len(aList)):
#         currArray = aList[i]
#         for j in range(len(currArray)):
#             currSentence = currArray[j]
#             if currSentence.lower().find(aItem.lower()) != -1:
#                 coordinates.append((i, j))
#     return coordinates
#
#
# def GetPositiveCount(iCoordinates, jCoordinates):
#     count = 0
#     for (ix, iy) in iCoordinates:
#         for (jx, jy) in jCoordinates:
#             if ix == jx and iy == jy:
#                 count = count + 1
#     return count
#
#
# def GetPositiveMatrix(aList, Items):
#     allCoordinates = [GetCoordinates(aList, x) for x in Items]
#     nItem = len(Items)
#     positiveMatrix = np.zeros((nItem, nItem))
#     for i in range(nItem):
#         iCoordinates = allCoordinates[i]
#         for j in range(i, nItem):
#             jCoordinates = allCoordinates[j]
#             positiveMatrix[i, j] = GetPositiveCount(iCoordinates, jCoordinates)
#             positiveMatrix[j, i] = positiveMatrix[i, j]
#     return positiveMatrix
#
# def GetNegativeCount(iCoordinates, jCoordinates):
#     count = 0
#     for (ix, iy) in iCoordinates:
#         for (jx, jy) in jCoordinates:
#             if ix == jx and iy != jy:
#                 count = count + 1
#     return count

# def GetNegativeMatrix(aList, Items):
#     allCoordinates = [GetCoordinates(aList, x) for x in Items]
#     nItem = len(Items)
#     negativeMatrix = np.zeros((nItem, nItem))
#     for i in range(nItem):
#         iCoordinates = allCoordinates[i]
#         for j in range(i, nItem):
#             jCoordinates = allCoordinates[j]
#             negativeMatrix[i, j] = GetNegativeCount(iCoordinates, jCoordinates)
#             negativeMatrix[j, i] = negativeMatrix[i, j]
#     return negativeMatrix
#
# def keepNGram(currBackOffgram, commonNGram, disR):
#     term, freq = currBackOffgram
#     relevantNGram = [x for (x, y) in commonNGram if x.find(term) != -1 and y > disR * freq]
#     KeepFlag = True
#     if relevantNGram != []:
#         KeepFlag = False
#     return KeepFlag
#
#
# def FilterLowerByHigherNGram(LowerGram, HigherGram, unigramFlag, disR):
#     cleanedGrams = [word.lower() for word in HigherGram if filterFun(word.lower())]
#     countGrams = FreqDist(cleanedGrams)
#     commonNGram = [(x, y) for (x, y) in countGrams.most_common() if y > 10]
#     if unigramFlag:
#         cleanedGrams = [word.lower() for word in LowerGram if filterWordFun(word.lower())]
#     else:
#         cleanedGrams = [word.lower() for word in LowerGram if filterFun(word.lower())]
#     countGrams = FreqDist(cleanedGrams)
#     commonBackOffGram = [(x, y) for (x, y) in countGrams.most_common() if y > 10]
#     return [x for x in commonBackOffGram if keepNGram(x, commonNGram, disR)]
#
#
# def keepNMinusOneGram(NminusOneGram, currNGram, disR):
#     term, freq = currNGram
#     relevantNMinus1Gram = [x for (x, y) in NminusOneGram if term.find(x) != -1 and y * disR > freq]
#     KeepFlag = True
#     if relevantNGram != []:
#         KeepFlag = False
#     return KeepFlag
#
#
# def FilterHigherByLowerNGram(LowerGram, HigherGram, unigramFlag, disR):
#     cleanedGrams = [word.lower() for word in HigherGram if filterFun(word.lower())]
#     countGrams = FreqDist(cleanedGrams)
#     commonNGram = [(x, y) for (x, y) in countGrams.most_common() if y > 15]
#     if unigramFlag:
#         cleanedGrams = [word.lower() for word in LowerGram if filterWordFun(word.lower())]
#     else:
#         cleanedGrams = [word.lower() for word in LowerGram if filterFun(word.lower())]
#     countGrams = FreqDist(cleanedGrams)
#     commonBackOffGram = [(x, y) for (x, y) in countGrams.most_common() if y > 15]
#     return [x for x in commonNGram if keepNMinusOneGram(commonBackOffGram, x, disR)]
#
#
# def get3Gram(s):
#     return GetNGram(s, 3)
#
#
# def filterWordFun(lowerWord):
#     all_stopwords = stopwords.words('english') + ['million', 'millions', 'billion', 'billions', 'trillion', 'trillions',
#                                                   '•', 'mil',\
#                                                   'june', 'jun', 'march', 'mar', 'months', 'month']
#     if lowerWord.isnumeric() or lowerWord in string.punctuation or lowerWord in all_stopwords:
#         return False
#     else:
#         return True
#
# def filterFun(lowerPhrase):
#     stopWords = ['million', 'millions', 'billion', 'billions', 'trillion', 'trillions', '•', \
#                  'june', 'jun', 'march', 'mar', 'months', 'month']
#     # presence of punctuation:
#     wordList = re.split(" ", lowerPhrase)
#     unwanted = [x for x in wordList if x in string.punctuation or x.isnumeric() or x in stopWords]
#     return len(unwanted) == 0
#
# def Clustering(distanceMatrix, th, sourceSet):
#     Zd = linkage(ssd.squareform(distanceMatrix), method="complete")
#     cld = fcluster(Zd, th, criterion='distance')
#     nGroup = max(cld)
#     groups = list(zip(sourceSet, cld))
#     return [[x for (x, y) in groups if y == i] for i in range(1, nGroup + 1)]

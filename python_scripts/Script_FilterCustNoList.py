import json
import sys
import traceback
from java.nio.charset import StandardCharsets
from org.apache.commons.io import IOUtils
from org.apache.nifi.processor.io import InputStreamCallback, OutputStreamCallback, StreamCallback
from org.python.core.util import StringUtil
from java.util import HashMap
from org.apache.nifi.components.state import Scope


# function extract and return cust_no list
def extractCustNoList(inputText, columnName):
    resultList = []
    dictObject = json.loads(inputText)
    for value in dictObject:
        resultList.append(value.get(columnName))
    resultList = list(set(resultList))
    return resultList


def cleanText(inputText):
    inputText = inputText.replace('\\', '')
    inputText = inputText.replace('u', '')
    inputText = inputText.replace('[', '').replace(']', '')
    inputText = inputText.replace('"', '')
    inputText = inputText.replace('\'', '')
    inputText = inputText.replace(' ', '')
    return inputText


def convertTextToList(inputText):
    return inputText.split(',')


def getNewmartCustListFromState():
    currentState = context.getStateManager().getState(Scope.LOCAL)
    return currentState.get('newmartCustList')


def updateNewmartState(additionalNewmartList):
    newState = HashMap()
    oldNewmartCustListText = getNewmartCustListFromState()
    if oldNewmartCustListText == None:
        oldNewmartCustList = []
    else:
        oldNewmartCustList = convertTextToList(cleanText(oldNewmartCustListText))
    updateNewmartList = list(set(additionalNewmartList + oldNewmartCustList))
    updateNewmartList = cleanText(str(updateNewmartList))
    newState.put('newmartCustList', updateNewmartList)
    context.getStateManager().setState(newState, Scope.LOCAL)
    return


def getFilteredCustNoList(listCustNoOlist, listCustNoNewmart):
    return list(set(listCustNoOlist).intersection(listCustNoNewmart))


# OutputStream: extract cust_no oc and write stream
class NewmartModifyStreamCallBack(InputStreamCallback):
    def __init__(self):
        pass

    def process(self, inputStream):
        global flowFile
        text = IOUtils.toString(inputStream, StandardCharsets.UTF_8)
        additionalNewmartList = convertTextToList(text)
        updateNewmartState(additionalNewmartList)


# end class


# OutputStream: extract cust_no sunline and write stream
class OlistModifyStreamCallBack(InputStreamCallback):
    def __init__(self):
        self.parentFlowFile = None

    def process(self, inputStream):
        listCustNoOlist = IOUtils.toString(inputStream, StandardCharsets.UTF_8)
        result = getFilteredCustNoList(convertTextToList(listCustNoOlist),
                                       convertTextToList(getNewmartCustListFromState()))
        if result:
            result = cleanText(str(result))
            newFlowFile = session.create(self.parentFlowFile)
            newFlowFile = session.putAttribute(newFlowFile, 'cust_no', result)
            session.transfer(newFlowFile, REL_SUCCESS)


# end class


flowFile = session.get()
if flowFile != None:
    if flowFile.getAttribute('database') == 'newmart':
        # save to State
        newmartModifyStreamCallBack = NewmartModifyStreamCallBack()
        session.read(flowFile, newmartModifyStreamCallBack)
        session.remove(flowFile)
    else:
        # filter list
        olistModifyStreamCallBack = OlistModifyStreamCallBack()
        olistModifyStreamCallBack.parentFlowFile = flowFile
        session.read(flowFile, olistModifyStreamCallBack)
        session.remove(flowFile)

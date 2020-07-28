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


# function clean text to split into list
def cleanText(inputText):
    inputText = inputText.replace('\\', '')
    inputText = inputText.replace('u', '')
    inputText = inputText.replace('[', '').replace(']', '')
    inputText = inputText.replace('"', '')
    inputText = inputText.replace('\'', '')
    inputText = inputText.replace(' ', '')
    return inputText


# OutputStream: extract cust_no sunline and write stream
class NewmartModifyStreamCallBack(StreamCallback):
    def __init__(self):
        pass

    def process(self, inputStream, outputStream):
        text = IOUtils.toString(inputStream, StandardCharsets.UTF_8)
        listCustNoNewmart = extractCustNoList(text, 'client_id')
        result = cleanText(str(listCustNoNewmart))
        outputStream.write(StringUtil.toBytes(result))


# end class


# process flowFile from session
flowFile = session.get()
if (flowFile != None):
    # flowFile = session.putAttribute(flowFile, "database", "newmart")
    flowFile = session.write(flowFile, NewmartModifyStreamCallBack())
    session.transfer(flowFile, REL_SUCCESS)

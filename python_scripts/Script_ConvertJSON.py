import json
import sys
import traceback
from java.nio.charset import StandardCharsets
from org.apache.commons.io import IOUtils
from org.apache.nifi.processor.io import InputStreamCallback, OutputStreamCallback, StreamCallback
from org.python.core.util import StringUtil
from java.util import HashMap
from org.apache.nifi.components.state import Scope


def removeDuplicateInList(inputList=[]):
    uniqueList = []
    seen = set()
    for member in inputList:
        temp = tuple(member.items())
        if temp not in seen:
            seen.add(temp)
            uniqueList.append(member)
    return uniqueList


def convertJsonMapping(inputText):
    infoList = json.loads(inputText)
    order_info = []
    outputJson = {}
    outputJsonArray = []

    for info in infoList:
        # order_info list
        order_info_member = {}
        order_info_member["order_id"] = info["order_id"]
        order_info_member["product_id"] = info["product_id"]
        order_info_member["price"] = info["price"]
        order_info_member["review_id"] = info["review_id"]
        order_info_member["review_score"] = info["review_score"]
        order_info_member["review_content"] = info["review_comment_title"] + " " + info["review_comment_message"]
        order_info.append(order_info_member)

    outputJson["customer_number"] = info["customer_unique_id"]
    outputJson["order_info"] = removeDuplicateInList(order_info)

    outputJsonArray.append(outputJson)
    return outputJsonArray


# OutputStream: extract cust_no sunline and write stream
class ExtractJsonFinal(StreamCallback):
    def __init__(self):
        pass

    def process(self, inputStream, outputStream):
        text = IOUtils.toString(inputStream, StandardCharsets.UTF_8)
        outputList = convertJsonMapping(text)
        outputText = json.dumps(outputList, indent=1)
        outputStream.write(StringUtil.toBytes(outputText))


# end class


# process flowFile from session
flowFile = session.get()
if (flowFile != None):
    flowFile = session.write(flowFile, ExtractJsonFinal())
    session.transfer(flowFile, REL_SUCCESS)

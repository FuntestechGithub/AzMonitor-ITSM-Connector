import logging
import os
import json
import aiohttp
import azure.functions as func # Service Bus interaction
from shared import settings # Global settings
from azure.servicebus import ServiceBusClient
from azure.storage.blob import  BlobServiceClient

# manifest type can be any
async def mainProcessFlow(Manifest):
    # logging.warn(f"Processing code block: {Manifest}")
    jsonops = jsonOps()
    if isinstance(Manifest, dict):
        # if this is no "payload" key, it is the root then feed "action" data back to mainProcessFlow
        if "payload" not in Manifest and "action" in Manifest:
            return await mainProcessFlow(Manifest["action"])

        # check if there are dependencies. If there are dependencies, payload needs to be updated.  
        if "dependencies" in Manifest:
            # logging.warn(settings.responseCache)
            for each in Manifest["dependencies"]:
                newValue = settings.responseCache[each]
                jsonops.replaceJSONyValue(Manifest["payload"], each, newValue)
        
        if "type" in Manifest:
            # setup request properties
            api_url = os.environ['SKILL_ENDPOINT'] + '/api/' + Manifest["skillname"]
            params = {
                "code": os.environ['SKILL_ENDPOINT_CODE']
            }

            # logical workflow
            if Manifest["type"] == "callback":
                async with aiohttp.ClientSession() as session:
                    try:
                        payloaddata = Manifest["payload"]
                        async with session.post(api_url, params=params, json=payloaddata) as response:  
                            # logging.warn(f"Response is {response}")
                            responseResult = await response.json()
                            # logging.warn(f"Response received {responseResult}")
                    except aiohttp.ClientError as e:
                        logging.error(f"Error: {str(e)}")
                        # put message back to service bus queue
                        return None
                    
                    # put response to cache
                    cacheName = "response." + Manifest["skillname"]
                    if "result" in responseResult:
                        logging.info(f"Response {cacheName} has been added into cache.")
                        # logging.info(responseResult["result"])
                        settings.responseCache[cacheName] = responseResult["result"]
                    
                    # if not the last action, call action
                    if "action" in Manifest:
                        # logging.warn(f"Continue procesing following actions:")
                        # logging.warn(Manifest["action"])
                        await mainProcessFlow(Manifest["action"])

            if Manifest["type"] == "bool":
                # logging.warn(Manifest["payload"])
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.post(api_url, params=params, json=Manifest["payload"]) as response:
                            responseResult = await response.json()
                            # logging.warn(f"Response received {responseResult}")
                    except aiohttp.ClientError as e:
                        logging.error(f"Error: {str(e)}")
                        # put message back to service bus queue
                        return None  
                    
                    # put response to cache
                    cacheName = "response." + Manifest["skillname"]
                    if "result" in responseResult:
                        # logging.warn(f"Response {cacheName} has been added into cache. Value is:")
                        # logging.warn(responseResult["result"])
                        settings.responseCache[cacheName] = responseResult["result"]
                    
                    # if not the last action, call action
                    if "action" in Manifest:
                        # logging.warn(Manifest["action"][responseResult["result"]])
                        await mainProcessFlow(Manifest["action"][responseResult["result"]])
                                              
    elif isinstance(Manifest, list):
        for element in Manifest:
            # logging.warn(f"List element is {element}")
            if isinstance(element, dict) or isinstance(element, list):
                await mainProcessFlow(element)       
    else:
        typevalue = type(Manifest)
        logging.warn(f"Unknown type, can't process manifest. Type is {typevalue}")




# using string expression to do the key value lookup
class jsonOps:
    def getJSONvalue(self, jsondata, lookupkey):
        lookupkeys = lookupkey.split(".")
        curr_jsondata = jsondata
        for key in lookupkeys:
            curr_jsondata = curr_jsondata[key]
        
        return curr_jsondata
    
    # replace json data key with old data with new data.
    def replaceJSONyValue(self, jsondata, oldvalue, newvalue):
        if isinstance(jsondata,dict) and jsondata:
            for key,value in jsondata.items():
                if isinstance(value, str) and value == oldvalue:
                    jsondata[key] = newvalue
                elif isinstance(value, dict) or isinstance(value, list):
                    self.replaceJSONyValue(value, oldvalue, newvalue)                                       
        elif isinstance(jsondata,list) and jsondata:
            for element in jsondata:
                if isinstance(element, dict) or isinstance(element, list):
                    self.replaceJSONyValue(element, oldvalue, newvalue)
        elif isinstance(jsondata, str) or isinstance(jsondata, int) or isinstance(jsondata, float):
            pass
        else:
            logging.error("Type is not recognized.")
        return jsondata
    


# ServiceBus opertaion class
class servicebusOps:
    def __init__(self, sbConnStr: str, sbqueueName: str) -> None:
        connstr = os.environ[sbConnStr]
        queue_name = os.environ[sbqueueName]
        with ServiceBusClient.from_connection_string(connstr) as client:
            with client.get_queue_receiver(queue_name) as receiver:
                self.receiver = receiver

    def putMsg2DeadLetter(self, msg: func.ServiceBusMessage):
        logging.info(f"Info: putting event to dead-letter queue. Event details: {str(msg.get_body().decode('utf-8'))}")
        self.receiver.dead_letter_message(msg)


# Storage Blob operation class
class storageBlobOps:
    def __init__(self) -> None:
        connect_str = os.environ['AZURE_STORAGE_CONNECTION_STRING']
        self.containerName = os.environ['AZURE_STORAGE_CONTAINER_NAME']
        # Create the BlobServiceClient object
        self.blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        
    '''
    BlobServiceClient doesn't have async function.
    '''
    def getAlertManifest(self, alertName:str) -> dict:
        fileName = alertName + ".json"
        blob_client = self.blob_service_client.get_container_client(container=self.containerName) 
        # encoding param is necessary for readall() to return str, otherwise it returns bytes
        downloader = blob_client.download_blob(blob=fileName,max_concurrency=1, encoding='UTF-8')
        blob_text = downloader.readall()
        return json.loads(blob_text)
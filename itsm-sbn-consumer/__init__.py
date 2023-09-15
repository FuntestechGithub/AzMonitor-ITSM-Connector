import logging
import json
import azure.functions as func
from shared.functionClasses import servicebusOps, storageBlobOps, mainProcessFlow
from shared import settings


async def main(msg: func.ServiceBusMessage):
    # intialize
    settings.init()
    '''
    Identify the alert type based on common alert schema.This is an universal step
    Current solution =  if "ServiceHealth" -> don't capture affected service

    ***Next gen solution will be put this into manifest as well so no need to touch the code.***
    '''
    # need to convert bytes to json. 
    # types need to be specified in their own "cases"
    msg_jsondata = json.loads(msg.get_body().decode('utf-8')) 
    settings.responseCache["EventData"] = msg_jsondata
    match msg_jsondata["data"]["essentials"]["monitoringService"]:
        case "ServiceHealth":
            msg_type = msg_jsondata["data"]["essentials"]["monitoringService"] + "-" + msg_jsondata["data"]["alertContext"]["properties"]["incidentType"]
            settings.responseCache["alerType"] = msg_type

    '''
    1. Get JSON manifest from storage.
    2. Go through the manifest and call the skills. Each calling will ask for payload:
        2.0 need to identify if it is list or dict
        2.1 check "dependencies", if presented, get the key value from cache previous step .
        2.2 check "type", define if it goes after true or false.
    '''

    # connect to the blob and get 
    blolclient = storageBlobOps()
    try:
        manifestJSON = json.dumps(blolclient.getAlertManifest(msg_type))
        manifestJSON = json.loads(manifestJSON)
        logging.info(f'Successfully retrieved manifest for alert type: {msg_type}.')
    except KeyError as e:
        logging.error(f'Failed retrieved manifest for alert type: {msg_type}.')
        logging.error(e)
    
    # core function to process the manifests
    return await mainProcessFlow(manifestJSON)

    
    



    
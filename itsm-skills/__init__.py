import logging
import azure.functions as func
import aiohttp
import html2text
from fastapi import FastAPI,status,Response, Request
from fastapi.responses import JSONResponse
from shared.payloadClasses import SnowIncident, Environment, SnowIncidentLookup, SnowShortDescriptoin, ManifestDetail, SNOWIncidentChange
from shared.referenceClasses import EnvReference
from shared.functionClasses import servicebusOps, jsonOps

app = FastAPI()

# Create a snow ticket
@app.post("/api/createSNOWIncident")
async def create_snow_incident(environment: Environment, snow_incident: SnowIncident, statusresponse: Response):
    logging.info(f"Received request to create incident with short description as {snow_incident.short_description}")   
    target = EnvReference(environment.env)
    try:
        api_url = target.snow_endpoint + 'api/now/table/incident'
    except:   
        statusresponse.status_code = status.HTTP_400_BAD_REQUEST
        return {"Error": "Enivronment name is invalid."}


    async with aiohttp.ClientSession() as session: 
        try:
            # Use exclude_none=True parameter in dict() to get rid of none presented 
            async with session.post(api_url, auth=aiohttp.BasicAuth(target.snow_sa_username, target.snow_sa_password), json=snow_incident.dict(exclude_none=True)) as response:
                    try:
                        rescontext = await response.json()
                        logging.info(rescontext)
                        if response.status < 300:
                            ticketNum = rescontext["result"]["number"]
                            return JSONResponse(content={ "result": {ticketNum}  })
                    except:
                        statusresponse.status_code = status.HTTP_400_BAD_REQUEST
                        return {"Error": "Either request to endpoint or response from endpoint is invalid."}
        except aiohttp.ClientError as e:
            return {"Error": str(e)}


# Get a snow ticket by short description value
@app.post("/api/getSNOWIncident")
async def get_snow_incident(environment: Environment, lookup_value: SnowIncidentLookup, statusresponse: Response):
    logging.info(f"Received request to get incident with short_description: {lookup_value.short_description}")
    target = EnvReference(environment.env)
    
    try:
        api_url = target.snow_endpoint + 'api/now/table/incident'
    except:   
        statusresponse.status_code = status.HTTP_400_BAD_REQUEST
        return {"Error": "Enivronment name is invalid."}
    
    QueryParams = {
        "short_description": lookup_value.short_description
    }

    # async with aiohttp client to allow multiple requests to be made at the same time
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, params=QueryParams, auth=aiohttp.BasicAuth(target.snow_sa_username, target.snow_sa_password)) as response:
                try:
                    rescontext = await response.json(content_type='application/json')
                    if response.status < 300:
                            if rescontext["result"]:
                                return JSONResponse(content={ "result": "true" })
                            else:
                                return JSONResponse(content={ "result": "false" })
                    else:
                        return JSONResponse(content={
                            "Status": response.status,
                            "Message": rescontext
                        })
                except:
                    statusresponse.status_code = status.HTTP_400_BAD_REQUEST
                    return {"Error": "Either request to endpoint or response from endpoint is invalid."}
        except aiohttp.ClientError as e:
            return {"Error": str(e)}


# Get a snow ticket system ID by short description value
@app.post("/api/getSNOWIncidentSysID")
async def get_snow_incident_sys_id(environment: Environment, lookup_value: SnowIncidentLookup, statusresponse: Response):
    logging.info(f"Received request to get incident system ID with short_description: {lookup_value.short_description}")
    target = EnvReference(environment.env)
    
    try:
        api_url = target.snow_endpoint + 'api/now/table/incident'
    except:   
        statusresponse.status_code = status.HTTP_400_BAD_REQUEST
        return {"Error": "Enivronment name is invalid."}
    
    QueryParams = {
        "short_description": lookup_value.short_description
    }

    # async with aiohttp client to allow multiple requests to be made at the same time
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, params=QueryParams, auth=aiohttp.BasicAuth(target.snow_sa_username, target.snow_sa_password)) as response:
                try:
                    rescontext = await response.json(content_type='application/json')
                except:
                    statusresponse.status_code = status.HTTP_400_BAD_REQUEST
                    return {"Error": "Failed to send request to endpoint."}
                
                if response.status < 300:
                    if rescontext["result"]:
                        # need to get first element from the list, have to make sure that short description to be unique
                        return JSONResponse(content={ "result": rescontext["result"][0]["sys_id"] })
                else:
                    statusresponse.status_code = status.HTTP_501_NOT_IMPLEMENTED
                    return JSONResponse(content={
                        "Status": response.status,
                        "Message": rescontext
                    })
                    
        except aiohttp.ClientError as e:
            return {"Error": str(e)}

# Compose the SNOW short description based on the list being passed in.
@app.post("/api/composeSNOWShortDescriptionName")
async def compose_short_description(snowShortDescription:SnowShortDescriptoin): 
    logging.info(f"Received request to compose short_description based on following elements: {snowShortDescription.shortDescription}")
    jsonClient = jsonOps()
    shortDescriptionString = ""
    lstsize = len(snowShortDescription.shortDescription) - 1
    for index, element in enumerate(snowShortDescription.shortDescription):
        if index < lstsize:
            shortDescriptionString += jsonClient.getJSONvalue(snowShortDescription.manifestData, element) + "-"
            
        else:
            shortDescriptionString += jsonClient.getJSONvalue(snowShortDescription.manifestData, element)
    return JSONResponse(content={ "result": shortDescriptionString })


# Check if alert status is closed.
@app.post("/api/checkIfResolved")
async def check_if_resolved(snowShortDescription:ManifestDetail): 
    jsonClient = jsonOps()
    status = jsonClient.getJSONvalue(snowShortDescription.manifestData, snowShortDescription.statusPath)
    if status == "Resolved":
        return JSONResponse(content={ "result": "true" })
    else:
        return JSONResponse(content={ "result": "false" })


# Update SNOW incident.
@app.post("/api/updateSNOWIncident")
async def update_SNOW_Incident(environment: Environment, snowIncidentChange:SNOWIncidentChange, statusresponse: Response): 
    logging.info(f"Received request to update SNOW incicent with system ID: {snowIncidentChange.sysId}.")
    jsonClient = jsonOps()
    payload = {}
    target = EnvReference(environment.env)
    newvalue = ""
    try:
        api_url = target.snow_endpoint + 'api/now/table/incident/' + snowIncidentChange.sysId
    except:   
        statusresponse.status_code = status.HTTP_400_BAD_REQUEST
        return {"Error": "Enivronment name is invalid."}

    # for key value in html format
    if snowIncidentChange.htmlpayload:
        for key,value in snowIncidentChange.htmlpayload.items():          
            if isinstance(value, list):
                for each in value:
                    try:
                        newvalue += html2text.html2text(jsonClient.getJSONvalue(snowIncidentChange.manifestData, each)) + '\n'
                    except:
                        statusresponse.status_code = status.HTTP_400_BAD_REQUEST
                        return  {"Error": "Failed to convert html content to text"}
            else:
                try:
                    newvalue = html2text.html2text(jsonClient.getJSONvalue(snowIncidentChange.manifestData, value))
                except:
                    statusresponse.status_code = status.HTTP_501_NOT_IMPLEMENTED
                    return  {"Error": "Failed to convert html content to text"}
            # put value to payload
            payload[key] =  newvalue
    # for key value in other formats
    if snowIncidentChange.nonehtmlpayload:
        for key,value in snowIncidentChange.nonehtmlpayload.items():
            if isinstance(value, list):
                for each in value:
                    newvalue += jsonClient.getJSONvalue(snowIncidentChange.manifestData, value) + '\n'
            else:        
                newvalue = jsonClient.getJSONvalue(snowIncidentChange.manifestData, value)
            payload[key] =  newvalue
    
    # async with aiohttp client to allow multiple requests to be made at the same time
    async with aiohttp.ClientSession() as session:
        try:
            async with session.put(api_url, auth=aiohttp.BasicAuth(target.snow_sa_username, target.snow_sa_password), json=payload) as response:
                rescontext = await response.json(content_type='application/json')
                if response.status < 300:
                    logging.info(f"Incident with sys_id {snowIncidentChange.sysId} is updated successfully.")
                    return JSONResponse(content=rescontext)
                else:
                    statusresponse.status_code = status.HTTP_501_NOT_IMPLEMENTED
                    return JSONResponse(content={
                        "Status": response.status,
                        "Message": rescontext
                    })
        except aiohttp.ClientError as e:
            return {"Error": str(e)}



async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(app).handle_async(req, context)

from pydantic import BaseModel, typing
import azure.functions as func


class SnowIncident(BaseModel):
    # for create_incident
    assignment_group: str = None
    caller_id: str = None
    cmdb_ci: str =  None
    contact_type: str = None
    description: str = None
    short_description: str = None
    u_category: str = None
    u_contact_details: str = None 
    u_sub_category_main: str = None
    # for update_incident
    work_notes: str = None
    # for close_incident
    close_code: int = None
    state: str = None
    u_issue_description: str = None 
    u_issue_type_new: str  = None
    u_resolution_steps: str = None
    u_rsolution_code: str = None
    u_service_outage_time: str = None
    u_service_restoration_time: str = None
    sys_id: str = None

class Environment(BaseModel):
    env: str

class SnowIncidentLookup(BaseModel):
    short_description: str = None
    sys_id: str = None

class ServiceBusProperties(BaseModel):
    sbConnStr: str 
    sbqueueName: str

class SnowShortDescriptoin(BaseModel):
    manifestData: typing.Any
    shortDescription: list

class ManifestDetail(BaseModel):
    manifestData: typing.Any
    statusPath: str = "data.alertContext.status"

class SNOWIncidentChange(BaseModel):
    manifestData: typing.Any
    sysId: str
    htmlpayload: dict = None
    nonehtmlpayload: dict = None


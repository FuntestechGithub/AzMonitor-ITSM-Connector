import os

class EnvReference:
    def __init__(self, Env:str):   
        match Env:
            case "sbx":
                self.snow_endpoint = "https://suncorsbx.service-now.com/"
                self.snow_sa_password = os.environ['SNOW_SBX_SA_PASSWORD']
                self.snow_sa_username = os.environ['SNOW_SBX_SA_USERNAME']
            case "sbx1":
                self.snow_endpoint = "https://dev156616.service-now.com/"
                self.snow_sa_password = os.environ['SNOW_SBX_SA_PASSWORD2']
                self.snow_sa_username = os.environ['SNOW_SBX_SA_USERNAME2']
            case "dit":
                self.snow_endpoint = "https://suncordit.service-now.com/"
                self.snow_sa_password = os.environ['SNOW_DIT_SA_PASSWORD']
                self.snow_sa_username = os.environ['SNOW_DIT_SA_USERNAME']
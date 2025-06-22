from DATA9003 import assets

# DATA HANDLING
import pandas as pd
from sodapy import Socrata
import json
from shapely.geometry import shape
from importlib import resources

# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  getasset
# DESCRIPTION:  SODA query to get the locations of universities/colleges in NYC and save results as asset

def getasset():

    # get SODA credentials
    with resources.open_text(assets, "sodacreds.json") as jsonfile:
        sodadict = json.load(jsonfile)
        apptoken = sodadict["APIkey"]
        dataurl = sodadict["url"]
        dataid = sodadict["datasets"]["uni"]

    # connect to socrata
    client = Socrata(dataurl,
                     app_token=apptoken)
    client.timeout = 90

    # query dataset
    select = "NAME AS name, the_geom AS geometry"

    res = client.get_all(dataid,
                         select=select)

    client.close()

    # convert to dataframe
    mylist = [item for item in res]
    unis = pd.DataFrame(mylist)
    unis.geometry = unis.geometry.apply(shape)

    unis.dropna(inplace=True)

    # get lat and long
    unis["longitude"] = unis.geometry.x
    unis["latitude"] = unis.geometry.y
    unis = unis[["name", "latitude", "longitude"]]

    with resources.path(assets, "thirdlevel.csv") as outfile:
        unis.to_csv(outfile)

    return unis


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  loadschools
# DESCRIPTION:  Load the locations of universities/colleges in NYC from asset
#               If an error occurs, load data using SODA and rewrite asset

def loadthirdlvl():

    try:
        with resources.path(assets, "thirdlevel.csv") as filepath:
            unis = pd.read_csv(filepath)
    except:
        unis = getasset()

    return unis
from DATA9003 import assets
import pandas as pd
import geopandas as gpd
from sodapy import Socrata
import wikipedia as wp
from importlib import resources
from shapely.geometry import shape
from shapely.geometry import Point
import re
import json
import folium as fl


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  getasset_nyc
# DESCRIPTION:  SODA query to get the locations of NYC subway stations

def getasset_nyc():

    # get SODA credentials
    with resources.open_text(assets, "sodacreds.json") as jsonfile:
        sodadict = json.load(jsonfile)
        apptoken = sodadict["APIkey"]
        dataurl = sodadict["url"]
        dataid = sodadict["datasets"]["sbwy_stations"]

    # connect to Socrata
    client = Socrata(dataurl,
                     app_token=apptoken)
    client.timeout = 90

    # query the dataset
    select = "the_geom AS geometry, name"

    res = client.get_all(dataid,
                         select=select)

    client.close()

    # convert results to dataframe
    mylist = [item for item in res]
    sbwystat = pd.DataFrame(mylist)

    sbwystat.geometry = sbwystat.geometry.apply(shape)

    return sbwystat


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  getasset_sir
# DESCRIPTION:  SODA query to get the locations of Staten Island Railway stations

def getasset_sir():

    # list of wikipedia pages to scrape
    wikipages = ["St. George Terminal",
                 "Tompkinsville station",
                 "Stapleton station",
                 "Clifton station (Staten Island Railway)",
                 "Grasmere station",
                 "Old Town station (Staten Island Railway)",
                 "Dongan Hills station",
                 "Jefferson Avenue station",
                 "Grant City station",
                 "New Dorp station",
                 "Oakwood Heights station",
                 "Bay Terrace station",
                 "Great Kills station",
                 "Eltingville station",
                 "Annadale station",
                 "Huguenot station",
                 "Prince's Bay station",
                 "Pleasant Plains station",
                 "Richmond Valley station",
                 "Arthur Kill station",
                 "Tottenville station"]
    SIRstations=pd.DataFrame(wikipages)
    SIRstations.columns=["name"]

    # scrape coords from wikipedia
    def getcoords(page):
        html=wp.page(page).html().encode("UTF-8")
        wikitable=pd.read_html(html)[0]

        # some stations need to have coords entered manually
        if page == "Annadale station":
            coords = ["40.54043°N", "74.1784°W"]
        elif page == "Prince's Bay station":
            coords = ["40.5254°N", "74.2003°W"]
        else:
            coords = wikitable.iloc[4, 1].split()[-2:]
        j=0
        for i in coords:
            coords[j] = float(re.sub('[^0-9.]','', i))
            j=1

        return Point(-coords[1], coords[0])
    SIRstations["geometry"] = SIRstations["name"].apply(getcoords)

    return SIRstations


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  getasset
# DESCRIPTION: Get and combine coords for subway and SIR stations

def getasset():

    subway = getasset_nyc()
    sir = getasset_sir()

    allhubs = gpd.GeoDataFrame(pd.concat([subway, sir]),
                               crs=4326)

    allhubs["longitude"] = allhubs.geometry.x
    allhubs["latitude"] = allhubs.geometry.y

    with resources.path(assets, "transport_hubs.geojson") as outfile:
        allhubs.to_file(outfile, driver="GeoJSON")

    return allhubs


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  loadstations
# DESCRIPTION:  read station coords from file or generate new file

def loadstations():

    try:
        with resources.path(assets, "transport_hubs.geojson") as filepath:
            geofile = open(filepath, "r")
            hubs = gpd.read_file(geofile)
            geofile.close()
    except:
        hubs = getasset()

    return hubs


# OBJECT TYPE: Function
# RETURN TYPE: folium map
# NAME:  mapstations
# DESCRIPTION:  map subway and SIR stataions

def mapstations(stations_df):

    # base map
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="CartoDB positron",
                   zoom_start=10)

    # subway lines data
    with resources.path("DATA9003.assets", "SubwayLines.geojson") as linefile:
        sbwy_lines = gpd.read_file(linefile)

    # add subway lines to map
    lines = fl.features.GeoJson(sbwy_lines.geometry,
                                style_function=lambda x: {'color': '#a1a1a1',
                                                          'weight': 1.5})

    mymap.add_child(lines)

    # add subway stations to map
    for point in range(0, len(stations_df)):
        fl.CircleMarker(location=(stations_df.iloc[point]["geometry"].y,
                                  stations_df.iloc[point]["geometry"].x),
                        popup=stations_df.iloc[point]["name"],
                        radius=2,
                        color="red").add_to(mymap)

    return mymap

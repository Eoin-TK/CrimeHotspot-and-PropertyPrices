from DATA9003 import assets

# DATA HANDLING
import json
import pandas as pd
from shapely.geometry import shape
import geopandas as gpd
from sodapy import Socrata
from importlib import resources

# PLOTTING
import folium as fl
from folium import plugins


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  getasset
# DESCRIPTION:  SODA query to get the locations of parks in NYC and save results as asset

def getasset():

    # load soda credentials
    with resources.open_text(assets, "sodacreds.json") as jsonfile:
        sodadict = json.load(jsonfile)
        apptoken = sodadict["APIkey"]
        dataurl = sodadict["url"]
        dataid = sodadict["datasets"]["parks"]

    # connect to socrata
    client = Socrata(dataurl,
                     app_token=apptoken)
    client.timeout = 90

    # query the dataset
    select = "BOROUGH, SIGNNAME AS NAME, TYPECATEGORY AS TYPE, ZIPCODE, multipolygon AS GEOMETRY"
    where = "TYPE LIKE '%Park' AND NOT(TYPE = 'Historic House Park')"

    res = client.get_all(dataid,
                         where=where,
                         select=select)

    client.close()

    # transform results to dataframe
    mylist = [item for item in res]
    parks = pd.DataFrame(mylist)
    parks.columns = [name.lower() for name in parks.columns]

    boro = {"X": "Bronx",
            "Q": "Queens",
            "B": "Brooklyn",
            "M": "Manhattan",
            "R": "Staten Island"}

    parks.borough.replace(boro,
                          inplace=True)

    # convert to geodataframe and get centres
    parks["geometry"] = parks.geometry.apply(shape)

    parks_geo = gpd.GeoDataFrame(parks,
                                 geometry="geometry")

    parks_geo["geometry"] = parks_geo.geometry.centroid

    parks.dropna(inplace=True)
    parks.drop_duplicates(inplace=True)

    # get lat long from GIS object
    parks_geo["longitude"] = parks_geo.geometry.x
    parks_geo["latitude"] = parks_geo.geometry.y

    # write results to file
    with resources.path(assets, "parks.geojson") as outfile:
        parks_geo.to_file(outfile, driver="GeoJSON")

    return parks_geo

# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  loadparks
# DESCRIPTION:  Load the locations of parks in NYC from asset
#               If an error occurs, load data using SODA and rewrite asset

def loadparks():

    try:
        with resources.path(assets, "parks.geojson") as filepath:
            geofile = open(filepath, "r")
            parks = gpd.read_file(geofile)
            geofile.close()
    except:
        parks = getasset()

    return parks


# OBJECT TYPE: Function
# RETURN TYPE: Folium Map
# NAME:  MapParks
# DESCRIPTION:  Load the locations of parks in nyc

def mapparks(parks_df):

    # base map
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="CartoDB positron",
                   zoom_start=10)

    # add markers for parks
    mycluster = fl.plugins.MarkerCluster()

    for point in range(0, len(parks_df)):
        fl.Marker(location=[parks_df.iloc[point]["geometry"].y,
                            parks_df.iloc[point]["geometry"].x],
                  popup=parks_df.iloc[point]["name"],
                  icon=fl.Icon(color='green', icon='leaf')).add_to(mycluster)

    # add markers to map
    mycluster.add_to(mymap)

    return mymap


# OBJECT TYPE: Function
# RETURN TYPE: Folium Map
# NAME: ParksChloro
# DESCRIPTION:  Count and map the number of parks in each zipcode

def parkschoro(parks_df):

    # count number of arrests in each zipcode
    mydf = parks_df.groupby(["zipcode"]).agg("count")
    mydf.reset_index(inplace=True)

    # read in GIS data for zipcodes
    with resources.path(assets, "zipcodes.zip") as zipfile:
        zipcodes = gpd.read_file(zipfile)
        zipcodes.columns = [name.lower() for name in zipcodes.columns]
        zipcodes = zipcodes[["zipcode", "geometry"]]
        zipcodes.to_crs(epsg=4326, inplace=True)

    # match zipcodes to counts
    finaldf = gpd.GeoDataFrame(mydf.merge(zipcodes,
                                          on="zipcode",
                                          how="right"))

    finaldf["name"] = finaldf["name"].fillna(0)

    # leaflet map of NYC
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="Cartodb positron",
                   zoom_start=10)

    # add choropleth to map
    fl.Choropleth(geo_data=zipcodes.to_json(),
                  data=finaldf,
                  key_on="feature.properties.zipcode",
                  columns=["zipcode", "name"],
                  fill_color='YlGn').add_to(mymap)

    return mymap

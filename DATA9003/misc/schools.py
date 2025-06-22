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
# DESCRIPTION:  SODA query to get the locations of schools in NYC and save results as asset

def getasset():

    # get SODA credentials
    with resources.open_text(assets, "sodacreds.json") as jsonfile:
        sodadict = json.load(jsonfile)
        apptoken = sodadict["APIkey"]
        dataurl = sodadict["url"]
        dataid = sodadict["datasets"]["schools"]

    # connect to Socrata
    client = Socrata(dataurl,
                     app_token=apptoken)
    client.timeout = 90

    # query the dataset
    select = "location_name AS name, Location_Category_Description AS category, LONGITUDE AS longitude, LATITUDE AS latitude, open_date AS year_opened"
    where = "Status_descriptions='Open' AND location_type_description='General Academic'"

    res = client.get_all(dataid,
                         where=where,
                         select=select)

    client.close()

    # convert results to dataframe
    mylist = [item for item in res]
    schools = pd.DataFrame(mylist)

    schools.dropna(inplace=True)
    schools.drop_duplicates(inplace=True,
                            subset=["category",
                                    "longitude",
                                    "latitude",
                                    "year_opened"])

    schools["year_opened"] = schools.year_opened.str.slice(0,4).astype(int)
    schools.sort_values("year_opened",
                        inplace=True)

    with resources.path(assets, "schools.json") as outfile:
        schools.to_json(outfile)

    return schools


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  loadschools
# DESCRIPTION:  Load the locations of schools in NYC from asset
#               If an error occurs, load data using SODA and rewrite asset

def loadschools():

    try:
        with resources.path(assets, "schools.json") as filepath:
            schools = pd.read_json(filepath)
    except:
        schools = getasset()

    return schools


# OBJECT TYPE: Function
# RETURN TYPE: Folium Map
# NAME:  mapschools
# DESCRIPTION:  Map the locations of schools in NYC

def mapschools(school_df):

    # base map
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="Cartodb positron",
                   zoom_start=10)

    #  make markers schools
    mymarkers=plugins.MarkerCluster().add_to(mymap)

    for point in range(0, len(school_df)):
        fl.Marker(location=[school_df.iloc[point]["latitude"],
                            school_df.iloc[point]["longitude"]],
                  popup=" Type: {}\n Year Opened: {}".format(school_df.iloc[point]["category"],
                                                             school_df.iloc[point]["year_opened"]),
                  icon=fl.Icon(color='blue', icon='book')).add_to(mymarkers)

    # add markers to map
    mymarkers.add_to(mymap)

    return mymap

# OBJECT TYPE: Function
# RETURN TYPE: Folium Map
# NAME:  schoolchoro
# DESCRIPTION:  Choropleth showing the number of schools in each zipcode

def schoolchoro(school_df):

    # make geodataframe
    geoschools = gpd.GeoDataFrame(school_df,
                                  geometry=gpd.points_from_xy(school_df.longitude, school_df.latitude))
    geoschools.set_crs(epsg=4326,
                      inplace=True)

    # base map
    mymap = fl.Map(location=[40.730610, -73.935242],
                   tiles="Cartodb positron",
                   zoom_start=10)

    # read in GIS data for zipcodes
    with resources.path(assets, "zipcodes.zip") as zipfile:
        zipcodes = gpd.read_file(zipfile)
        zipcodes.columns = [name.lower() for name in zipcodes.columns]
        zipcodes = zipcodes[["zipcode", "geometry"]]
        zipcodes.to_crs(epsg=4326,
                        inplace=True)

    # match schools to zipcodes
    finaldf = gpd.sjoin(geoschools,
                        zipcodes,
                        how="left",
                        op="within")

    # count schools in each zipcode
    finaldf = finaldf.groupby(["zipcode"]).agg("count")
    finaldf.reset_index(inplace=True)

    # add choropleth to map
    fl.Choropleth(geo_data=zipcodes.to_json(),
                  data=finaldf,
                  key_on="feature.properties.zipcode",
                  columns=["zipcode", "name"],
                  fill_color='YlGnBu').add_to(mymap)

    return mymap

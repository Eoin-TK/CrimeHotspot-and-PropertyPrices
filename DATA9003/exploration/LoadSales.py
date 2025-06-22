import os
import pandas as pd
import geopandas as gpd
import numpy as np
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import ArcGIS
from importlib import resources

from DATA9003.misc.schools import loadschools
from DATA9003.misc.parks import loadparks
from DATA9003.misc.subway import loadstations
from DATA9003.misc.uni import loadthirdlvl
from DATA9003 import assets
from sklearn.neighbors import BallTree


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  NearestDistance
# DESCRIPTION:  Get distance for each (lat, long) pair in FROM to their nearest neighbour in TO

def NearestDistance(FROM, TO):

    F = pd.DataFrame()
    T = pd.DataFrame()

    # get coordinates in radians
    for col in FROM[["latitude", "longitude"]]:
        F[col] = np.deg2rad(FROM[col].values)
    for col in TO[["latitude", "longitude"]]:
        T[col] = np.deg2rad(TO[col].values)

    # initialise BallTree object
    Btree = BallTree(T.values,
                     metric='haversine')

    # query the Btree object for the nearest neighbour of each property
    distance, index = Btree.query(F.values, k=1)

    # distances returned are for unit sphere
    # convert to kilometres by multiplying by earth's radius: 6371km
    distance = distance*6371

    return distance.flatten()


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  DistanceToShore
# DESCRIPTION:  Calculate the distance to shore for each property in houses

def DistanceToShore(houses):

    # create GeoDataFrame to use coords as GIS data
    geodf = gpd.GeoDataFrame(houses,
                             geometry=gpd.points_from_xy(houses.longitude,
                                                         houses.latitude))
    geodf.set_crs(epsg=4326,
                  inplace=True)
    # transform to coord ref system EPSG:2263, this means resulting distances will be in ft
    geodf.to_crs(epsg=2263,
                 inplace=True)

    # read in GIS data for NYC shoreline
    with resources.path(assets, "shoreline.geojson") as filepath:
        geofile = open(filepath, "r")
        shoreline = gpd.read_file(geofile)
        # ensure crs matches
        shoreline.to_crs(epsg=2263, inplace=True)
        geofile.close()

    # geopandas has some functionality for calculating distances between different geometries
    def getdist(point):
        distances = shoreline.distance(point)
        return min(distances)

    # get the distance to shore for each property
    dist2shore = geodf.geometry.apply(getdist)

    return dist2shore


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  LoadOneYear
# DESCRIPTION:  Load the property sales data for a given year

def LoadOneYear(SalesDir, yr):
    mydir = os.path.join(SalesDir, str(yr))
    myfiles = os.listdir(mydir)

    cols = ["borough",
            "neighbourhood",
            "address",
            "zipcode",
            "resi_units",
            "comm_units",
            "total_units",
            "land_sqft",
            "gross_sqft",
            "year_built",
            "tax_cls",
            "building_cls",
            "sale_price",
            "sale_date"]

    # read and concatenate sales data for each borough
    for file in myfiles:
        df_temp = pd.read_excel(os.path.join(mydir, file),
                                usecols="A:B,I,K:U",
                                skiprows=1,
                                header=None,
                                names=cols)

        if "sales_df" not in locals():
            sales_df = df_temp
        else:
            sales_df = pd.concat([sales_df, df_temp])
    del df_temp

    # change borough values from numerical encoding to names
    boroughs = {1: "M",
                2: "X",
                3: "B",
                4: "Q",
                5: "SI"}

    sales_df["borough"].replace(boroughs,
                                inplace=True)

    # filter for purchases of a single residential unit
    cond0a = sales_df["resi_units"] == 1
    cond0b = sales_df["comm_units"] == 0
    cond0c = sales_df["total_units"] == 1

    # filter out properties on extreme ends of price scale
    cond1a = 150000 < sales_df["sale_price"]
    cond1b = sales_df["sale_price"] < 1 * (10 ** 6)

    # filter for one-family homes that are detached (A1) and terraced/semi-d (A5)
    cond2 = sales_df.building_cls.str.contains("A1|A5")

    # remove sales of properties with invalid construction years
    cond3 = sales_df.year_built > 0

    # manhattan is excluded from our analysis
    cond4 = sales_df.borough != "M"

    sales_df = sales_df.loc[(cond0a & cond0b & cond0c) &
                            (cond1a & cond1b) &
                            (cond2) &
                            (cond3) &
                            (cond4)]

    # some addresses include apartment numbers (in the format [ST ADDRESS, APT NO.])
    # the apartment no. can be removed
    sales_df["address"] = sales_df.address.str.split(",").str[0]

    # removing missing values and duplicates
    sales_df.dropna(inplace=True)
    sales_df.drop_duplicates(inplace=True,
                             ignore_index=True)

    with resources.path("DATA9003.assets", "PropertyCoords.csv") as coordfile:
        coords = pd.read_csv(coordfile,
                             usecols=["StreetAddress",
                                      "latitude",
                                      "longitude"])

    sales_df = pd.merge(sales_df, coords,
                        how="left",
                        left_on=["address"],
                        right_on=["StreetAddress"])

    sales_df.drop(["resi_units",
                   "comm_units",
                   "total_units",
                   "StreetAddress"],
                  axis=1,
                  inplace=True)

    # extract year from date
    sales_df["year"] = sales_df["sale_date"].dt.year
    sales_df = sales_df.loc[sales_df.year < 2021]

    sales_df["age"] = sales_df["year"] - sales_df["year_built"]
    sales_df.drop("year_built",
                  axis=1,
                  inplace=True)

    # extract quarter from date
    sales_df["quarter"] = sales_df["sale_date"].dt.quarter + 4*(sales_df["year"] - min(sales_df["year"]))

    # extract month from date
    sales_df["month"] = sales_df["sale_date"].dt.month + 12*(sales_df["year"] - min(sales_df["year"]))

    # Distance to nearest school
    schools = loadschools()
    sales_df["dist2school"] = NearestDistance(sales_df, schools.loc[schools.year_opened <= yr])

    # Distance to nearest park
    parks = loadparks()
    sales_df["dist2park"] = NearestDistance(sales_df, parks)

    # Distance to transport hub
    sbwy = loadstations()
    sales_df["dist2sbwy"] = NearestDistance(sales_df, sbwy)

    # Distance to college/university
    uni = loadthirdlvl()
    sales_df["dist2uni"] = NearestDistance(sales_df, uni)

    # Distance to shore
    sales_df["dist2shore"] = DistanceToShore(sales_df[["latitude", "longitude"]])

    # Distance to crime hotspot
    with resources.path(assets, "hotspots_meso.json") as filepath:
        hotspots = pd.read_json(filepath)
    sales_df["dist2crime"] = NearestDistance(sales_df, hotspots)

    return sales_df


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  LoadSalesData
# DESCRIPTION:  Load the property sales data for all years

def LoadSalesData(SalesDir):
    filepath = os.path.join(SalesDir, "NYC_propertysales.csv")

    if os.path.exists(filepath):
        allsales = pd.read_csv(filepath,
                               parse_dates=[7])
    else:
        # collate sales data for all years
        for yr in range(2006, 2021):
            sales_yr = LoadOneYear(SalesDir, yr)

            if "allsales" not in locals():
                allsales = sales_yr
            else:
                allsales = pd.concat([allsales, sales_yr])

        allsales.sort_values("sale_date",
                             inplace=True,
                             ignore_index=True)

        allsales.drop(["neighbourhood",
                       "address"],
                      axis=1,
                      inplace=True)

        allsales.to_csv(filepath,
                        index=False)

    print(allsales.info())
    return allsales


# OBJECT TYPE: Function
# RETURN TYPE: Pandas DataFrame
# NAME:  GeoCodeAddresses
# DESCRIPTION:  Get coordinates for all unique street addresses in sales_df

def GeocodeAddresses(sales_df, SalesDir=None):

    # only street addresses and zipcodes required for geocoding
    mydf = sales_df.loc[:, ["address", "zipcode"]]

    # properties may have been sold multiple times
    mydf.drop_duplicates(inplace=True)

    # combine street address and zipcode into full address
    mydf["FullAddress"] = mydf["address"] + ", NEW YORK, NEW YORK, " + mydf["zipcode"].astype(str)
    mydf.rename(columns={"address":"StreetAddress"},
                inplace=True)

    # connect to ArcGIS
    locator = ArcGIS(user_agent="NYCsales")

    # 1 - include delay between geocoding calls (avoid usage limits)
    geocode = RateLimiter(locator.geocode, min_delay_seconds=0.1)

    # 2- - create location column
    mydf['location'] = mydf['FullAddress'].apply(geocode)

    # 3 - get long, lat and alt from location column (break tuple into multiple columns)
    mydf['point'] = mydf['location'].apply(lambda loc: tuple(loc.point) if loc else None)
    mydf[['latitude', 'longitude', 'altitude']] = pd.DataFrame(mydf['point'].tolist(),
                                                               index=mydf.index)
    # remove unneeded columns
    mydf.drop(["FullAddress", "altitude"],
              axis=1,
              inplace=True)

    # if provided with a directory path then save to a file there
    if SalesDir is not None:
        filepath = os.path.join(SalesDir, "PropertyCoords.csv")
        mydf.to_csv(filepath,
                    index=False)

    return mydf

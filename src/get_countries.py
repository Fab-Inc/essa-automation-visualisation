import re
import requests
import pandas as pd
import yaml
from bs4 import BeautifulSoup as BSoup

def country_dict(row):
    iso = row["iso_3"]
    country = row["Official name"]
    alternatives = row["Alternatives"]

    if pd.notna(iso):
        c_dict = {iso:country}
    else:
        c_dict = {}
    for cc in alternatives:
        c_dict.update({cc:country})
    
    return c_dict

def retrieve_countries(URL: str, headers: dict) -> pd.DataFrame:
    """Fetch and parse the Wikipedia page of country names and aliases."""
    response = requests.get(URL, headers=headers)
    
    soup = BSoup(response.text, "lxml")

    tables = soup.select("table.wikitable")

    country_list = []
    for table in tables:
        table_rows = table.find_all("tr")
        for row in table_rows[1:]:
            row_contents = row.find_all("td")
            alpha_code = row_contents[0].text.strip()
            country = row_contents[1].find("a").text.strip()
            alternatives = [c.text.strip() for c in row_contents[2].find_all("b")]
            country_list.append([alpha_code,country,alternatives])

    country_list_df = pd.DataFrame(country_list)
    country_list_df.columns = ["iso_3","Official name","Alternatives"]

    full_dict = {}
    for r, row in country_list_df.iterrows():
        full_dict.update(country_dict(row))

    return country_list_df, full_dict

def country_iso_standards(url: str, headers: dict) -> pd.DataFrame:
    # Fetch the page content
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise error if request failed

    # Parse all tables into a list of DataFrames
    tables = pd.read_html(response.text)
    df = tables[0]
    cols = ["ISO name","Official name", "Sovereignty","ISO-2","ISO-3","Num","Subdivision codes","TLD"]
    df.columns = cols
    new_rows = []
    def clean_rows(row):
        iso_name = row[cols[0]]
        off_name = row[cols[1]]
        iso_2 = row[cols[3]]
        iso_3 = row[cols[4]]

        if pd.notna(iso_name):
            for x,nn in enumerate(iso_name):
                if nn == "[":
                    iso_name = iso_name[:x]
        if pd.notna(off_name):
            for x,nn in enumerate(off_name):
                if nn == "[":
                    off_name = off_name[:x]
        if pd.notna(iso_2):
            for x,nn in enumerate(iso_2):
                if nn == "[":
                    iso_2 = iso_2[:x]
        if pd.notna(iso_3):
            for x,nn in enumerate(iso_3):
                if nn == "[":
                    iso_3 = iso_3[:x]
        
        new_rows.append([iso_name, off_name, iso_2, iso_3])

    for k,row in df.iterrows():
        clean_rows(row)
    countries_df = pd.DataFrame(new_rows)
    countries_df.columns = ["iso_name","official_name","iso_2","iso_3"]
    return countries_df

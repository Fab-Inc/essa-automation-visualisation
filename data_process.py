#%%
# import all necessary libs
import re
import ast
from pathlib import Path
import pandas as pd
import numpy as np
import yaml
import json
from fuzzywuzzy import fuzz

from src.get_countries import retrieve_countries, country_iso_standards
from src.process import ( 
    country_cleaning, 
    clean_agents_data, 
    clean_users, 
    capitalize_values, 
    to_wide_format,
    rename_vals,
    replace_manual_values,
    country_to_region
)
from ecar_full_analysis import combine_tables

#%%
home = Path.home()
if home.name == "evans":
    home = Path("D:/Dropbox")

#%%
# load yaml file with parameters
with open("config.yaml", 'r') as file:
    params = yaml.safe_load(file)

wiki_countries_URL = params["wiki_countries_url"]
country_iso_url = params["country_codes_url"]
headers = params["headers"]
country_cols = params["country_cols"]

## defining paths >> if the path changes, so should this section only, everything else should remain the same
root_dir = home / "Fab Inc Dropbox/Fab Inc BMGF AI/10. Sector mappings"
data_dir = root_dir / "Data"
powerbi_dir = root_dir / "PowerBi/V2/Data/Dashboard data"

# defining file paths
product_impact_path = data_dir / params["product_impact_path"] # path to the product impact file
product_types_path = data_dir / params["product_types_path"] # path to the product types file
taxonomy_path = data_dir / params["guide_path"] # path to the taxonomy file
json_countries = root_dir / params["json_countries_path"] # path to the json countries file
initial_dataset_path = root_dir / params["initial_dataset"] # path to the initial dataset
evidence_path = home / params["evidence_path"]
region_path = params["regions"]

#%%
# load the initial dataset
initial_dataset = pd.read_excel(initial_dataset_path)
initial_dataset.rename(columns={"Product_ID":"product_id"}, inplace=True)
use_cols = list(initial_dataset.columns)[:11]
initial_dataset_df = initial_dataset[use_cols].copy()
#initial_dataset_df.drop(columns=["Level of Education System"], inplace=True)
values_replacer = pd.read_excel(params["value_replace_file"], sheet_name="replace_values").iloc[:,:3]
values_replacer_ = pd.read_excel(params["value_replace_file"], sheet_name="replace_old")
evidence_data = pd.read_csv(evidence_path)
quality_cols = list(evidence_data.columns)[:10]
quality_cols.append("validation_label")
quality_cols = list(set(quality_cols) - {"product_name","company_name"})
 
region_data = pd.read_csv(region_path, encoding="cp1252")
region_data["country"] = region_data["country"].str.replace("'","").str.replace(",","").str.replace('"','').str.strip()
region_data.dropna(subset=["class_region"], inplace=True, ignore_index=True)
region_data_dict = region_data.set_index("country")["class_region"].to_dict()

# obtain a unique output of the df
initial_dataset_df = initial_dataset_df.drop_duplicates(subset=["product_id","User"], ignore_index=True)
orgs_cols = list(initial_dataset.columns[1:4])
products_col = list(initial_dataset.columns[4:10])
products_col.append(products_col.pop(0)) # interchange order

# %%
# impact, product types and taxonomy dataset
product_impacts = pd.read_excel(product_impact_path) # dataframe containing the product impacts
product_types = pd.read_excel(product_types_path) # dataframe containing the product types
taxonomy = pd.read_excel(taxonomy_path, sheet_name="Taxonomy") # dataframe containing the taxonomy

# %%
### focus on the variable_ids that we have, i.e. if the id is blank, then we drop it
#product_impacts = product_impacts[product_impacts["variable_group"].notna()].reset_index(drop=True)
#product_impacts["variable_group"] = product_impacts["variable_group"].astype(int)

# variable groups we have
variables = list(product_impacts["variable_name"].unique())

product_impacts_copy = product_impacts.copy() # a copy of the original df

# apply a clean function to the variable value column to remove instances of special characters
col = "variable_value"
product_impacts[col] = product_impacts[col].apply(clean_agents_data) 

# %%
## converting to wide format from a long format
# >> product_impacts data
wide_df = to_wide_format(product_impacts, variables)
product_cols = list(wide_df.columns)[4:-7]
product_cols.insert(0, "product_id")
product_cols.extend(list(wide_df.columns)[-2:])
products_col.extend(product_cols)
# >> product_types data
products_cat_df = pd.DataFrame()
for i,row in product_types.iterrows():
    pro_id = row["product_id"]
    categories_df = pd.DataFrame(ast.literal_eval(row["variable_value"])) if pd.notna(row["variable_value"]) else pd.DataFrame()
    categories_df["product_id"] = pro_id
    products_cat_df = pd.concat([products_cat_df, categories_df], ignore_index=True)

use_cases_cols = list(products_cat_df.columns)
use_cases_cols.append("User")
# %%
# merge wide df with products_cat_df
full_df = wide_df.merge(products_cat_df, on="product_id", how="outer")
full_df.drop(columns=['Product Sub-type', 'Product Type', 'Product Use Cases'], inplace=True)

## merge resulting df with the initial dataset
full_merge_df = full_df.merge(initial_dataset_df, on="product_id", how="outer")
full_merge_df = full_merge_df.merge(evidence_data, on="product_id", how="outer")
ecar_df = combine_tables()
ecar_df.dropna(subset=["product_id","organisation_id"], inplace=True)

full_merge_df = pd.concat([full_merge_df, ecar_df])
## get alternative country naming || country cleaning

alternative_countries = retrieve_countries(wiki_countries_URL, headers)
standard_countries = country_iso_standards(country_iso_url, headers)
# standard_countries.loc[
#     standard_countries["iso_name"] == "Namibia", "iso_2"
# ] = "NA"
alternative_countries = retrieve_countries(wiki_countries_URL, headers)
alternative_countries[0].loc[
    alternative_countries[0]["Official name"] == "Kosovo", "iso_3"
] = "XKX"
clean_countries = alternative_countries[0][alternative_countries[0]["iso_3"] != '']
merged_countries = clean_countries.merge(standard_countries[["iso_2", "iso_3"]], on="iso_3")
alt_country_dict = merged_countries.set_index("iso_3")["Official name"].to_dict()
alt_country_dict.update(merged_countries.set_index("iso_2")["Official name"].to_dict())
if np.nan in alt_country_dict:
    alt_country_dict["NA"] = alt_country_dict.pop(np.nan)

alt_country_dict.update(alternative_countries[1])
alt_country_dict["XK"] = "Kosovo"
alt_country_dict["HK"] = "Hong Kong"

regions_dict = {
    "Asia": [
        "Afghanistan","Armenia","Azerbaijan","Bahrain","Bangladesh","Bhutan","Brunei",
        "Cambodia","China","Cyprus","Georgia","India","Indonesia","Iran","Iraq","Israel",
        "Japan","Jordan","Kazakhstan","Kuwait","Kyrgyzstan","Laos","Lebanon","Malaysia",
        "Maldives","Mongolia","Myanmar","Nepal","North Korea","Oman","Pakistan","Palestine",
        "Philippines","Qatar","Saudi Arabia","Singapore","South Korea","Sri Lanka","Syria",
        "Tajikistan","Thailand","Timor-Leste","Turkey","Turkmenistan","United Arab Emirates",
        "Uzbekistan","Vietnam","Yemen"
    ],
    "Western Europe": [
        "Austria","Belgium","France","Germany","Liechtenstein","Luxembourg",
        "Monaco","Netherlands","Switzerland"
    ],
    "South America": [
        "Argentina","Bolivia","Brazil","Chile","Colombia","Ecuador","Guyana",
        "Paraguay","Peru","Suriname","Uruguay","Venezuela"
    ],
    "Middle-East": [
        "Bahrain","Cyprus","Egypt","Iran","Iraq","Israel","Jordan","Kuwait","Lebanon",
        "Oman","Palestine","Qatar","Saudi Arabia","Syria","Turkey","United Arab Emirates","Yemen"
    ]
}

[country_cleaning(full_merge_df, col, alt_country_dict, regions_dict) for col in country_cols]

# get regions for the countries
full_merge_df["region"] = full_merge_df['Countries Implementing in'].apply(
    lambda x: country_to_region(x, region_data_dict)
)
products_col.append("region")
#%%
## replace values as per the excel file
values_replacer = rename_vals(values_replacer)
values_replacer_ = rename_vals(values_replacer_)

world = alternative_countries[0]["Official name"].to_list()
#%%
replace_manual_values(full_merge_df, values_replacer, world)
for col in values_replacer_["column"]:
    full_merge_df[col] = full_merge_df[col].apply(lambda x: "Unknown" if pd.isna(x) else x)

full_merge_df.loc[full_merge_df["Impact"].isna(), "Outcomes Measured"] = "Unknown"

# %%
## General cleaning of the dataframe
#### column-by-column cleaning >>> function to clean these columns

full_merge_df["Type of Organisation"] = full_merge_df["Type of Organisation"].replace('For-profit','For-Profit')

for col in ["Product types", "Product Subtype", "Use Cases", "User"]:
    full_merge_df[col] = full_merge_df[col].apply(lambda x: x.strip().strip("\n") if isinstance(x, str) else x)

for col in ["Product types", "Product Subtype", "Use Cases"]:
    taxonomy[col] = taxonomy[col].apply(lambda x: x.strip().strip("\n") if isinstance(x, str) else x)

# %%
#### product sub-type cleaning
prod_types = [ll for ll in list(full_merge_df["Product types"].unique()) if pd.notna(ll)]
taxonomy_ptypes,taxonomy_subptypes,taxonomy_usecases = list(taxonomy["Product types"].unique()), list(taxonomy["Product Subtype"].unique()), list(taxonomy["Use Cases"].unique())
combined_list = sorted(taxonomy_subptypes + taxonomy_usecases)
taxonomy_dict = taxonomy.set_index("Product Subtype")["Product types"].to_dict()
taxonomy_dict.update(taxonomy.set_index("Use Cases")["Product types"].to_dict())
for ptype in prod_types:
    if ptype in combined_list:
        print(f"{ptype} is valid")

#concept
product_cats = ["Learning","Teaching","Administration & Governance","Other"]
product_cats_low = [cat.lower().strip() for cat in product_cats]
prod_Dict = {}
prod_types = [pod for pod in prod_types if pd.notna(pod)]
for pdtype in prod_types:
    prod_Dict[pdtype] = {}
    for inner_str in prod_types:
        ratio = fuzz.token_sort_ratio(pdtype, inner_str)
        if ratio >= 80 and pdtype != inner_str:
            if pdtype not in combined_list:
                print(pdtype)
                full_merge_df["Product types"] = full_merge_df["Product types"].replace(pdtype, inner_str)
                
            prod_Dict[pdtype][inner_str] = ratio
    
    if pdtype.lower().strip() not in product_cats_low:
        if pdtype in combined_list:
            full_merge_df.loc[
                full_merge_df["Product types"] == pdtype, "Product types"
            ] = taxonomy_dict[pdtype]

####### Product types
#%%
prod_types = [ll for ll in list(full_merge_df["Product types"].unique()) if pd.notna(ll)]
taxonomy_ptypes,taxonomy_subptypes,taxonomy_usecases = list(taxonomy["Product types"].unique()), list(taxonomy["Product Subtype"].unique()), list(taxonomy["Use Cases"].unique())
combined_list = sorted(taxonomy_subptypes + taxonomy_usecases)
taxonomy_dict = taxonomy.set_index("Product Subtype")["Product types"].to_dict()
taxonomy_dict.update(taxonomy.set_index("Use Cases")["Product types"].to_dict())

product_cats = ["Learning","Teaching","Administration & Governance","Other"]
product_cats_low = [cat.lower().strip() for cat in product_cats]

ver_df = full_merge_df[full_merge_df["Product types"].isin(product_cats)]

## df to work on
invalid_prodtypes = full_merge_df[~full_merge_df["Product types"].isin(product_cats)].copy()

prod_types = [ll for ll in list(invalid_prodtypes["Product types"].unique()) if pd.notna(ll)]

prod_Dict = {}

## starting with product types
for pdtype in prod_types:
    if pdtype in combined_list:
        continue
    prod_Dict[pdtype] = {}
    for inner_str in prod_types:
        ratio = fuzz.token_sort_ratio(pdtype, inner_str)
        if ratio >= 80 and pdtype != inner_str:
            if pdtype not in combined_list and inner_str in combined_list: ## taxonomy list reference - only replace if not in the taxonomy list
                full_merge_df["Product types"] = full_merge_df["Product types"].replace(pdtype, inner_str)
            else:
                cm_ratio, cm_max = 0,""
                for cm in combined_list:
                    if fuzz.token_sort_ratio(pdtype, cm) > cm_ratio:
                        cm_ratio = fuzz.token_sort_ratio(pdtype, cm)
                        cm_max = cm
                if cm_ratio >= 80:
                    full_merge_df["Product types"] = full_merge_df["Product types"].replace(pdtype, cm_max)
                
            prod_Dict[pdtype][inner_str] = ratio
for pdtype in prod_types:
    if pdtype.lower().strip() not in product_cats_low:
        if pdtype in combined_list:
            full_merge_df.loc[
                full_merge_df["Product types"] == pdtype, "Product types"
            ] = taxonomy_dict[pdtype]

## product subtypes
subprod_types = [ll for ll in list(full_merge_df["Product Subtype"].unique()) if pd.notna(ll)]
subproduct_cats = list(taxonomy["Product Subtype"].unique())
subproduct_cats_low = [cat.lower().strip() for cat in subproduct_cats]

subprod_Dict = {}
for spdtype in subprod_types:
    if not spdtype or spdtype.isspace(): 
        print(spdtype)
        continue
    if spdtype in combined_list:
        continue
    subprod_Dict[spdtype] = {}
    for inner_str in subprod_types:
        ratio = fuzz.token_sort_ratio(spdtype, inner_str)
        if ratio >= 80 and spdtype != inner_str:
            if spdtype not in combined_list and inner_str in combined_list: ## taxonomy list reference - only replace if not in the taxonomy list
                full_merge_df["Product Subtype"] = full_merge_df["Product Subtype"].replace(spdtype, inner_str)
            else:
                cm_ratio, cm_max = 0,""
                for cm in combined_list:
                    if fuzz.token_sort_ratio(spdtype, cm) > cm_ratio:
                        cm_ratio = fuzz.token_sort_ratio(spdtype, cm)
                        cm_max = cm
                if cm_ratio >= 80:
                    full_merge_df["Product Subtype"] = full_merge_df["Product Subtype"].replace(spdtype, cm_max)
                
            subprod_Dict[spdtype][inner_str] = ratio
for spdtype in subprod_types:
    if spdtype.lower().strip() not in subproduct_cats_low:
        if spdtype in combined_list:
            full_merge_df.loc[
                full_merge_df["Product Subtype"] == spdtype, "Product types"
            ] = taxonomy_dict[spdtype]

#full_merge_df = pd.concat([ver_df, invalid_prodtypes], ignore_index=True)

# use case cleaning
types_dict = taxonomy.set_index("Use Cases")["Product types"].to_dict()
subtypes_dict = taxonomy.set_index("Use Cases")["Product Subtype"].to_dict()

## change some use cases that are similar to those in the taxonomy but written differently
full_merge_df.loc[full_merge_df["Use Cases"] == "Track student attendance throughout the school term from the comfort of your phone.", "Use Cases"] = "Automated attendance Tracking"
full_merge_df.loc[full_merge_df["Use Cases"] == "Generate detailed spreadsheets and PDF report forms (report cards, transcripts, etc.).", "Use Cases"] = "Report Card Generation"
full_merge_df.loc[full_merge_df["Use Cases"] == "Inclusive  education", "Use Cases"] = "Special education"
full_merge_df.loc[full_merge_df["Use Cases"] == "AI Grading Tool", "Use Cases"] = "Automated Grading"

usecase_types = [ll for ll in list(full_merge_df["Use Cases"].unique()) if pd.notna(ll)]
usecase_cats = list(taxonomy["Use Cases"].unique())
usecase_cats_low = [cat.lower().strip() for cat in usecase_cats]
usecase_Dict = {}
for uctype in usecase_types:
    if uctype in combined_list:
        continue
    usecase_Dict[uctype] = {}
    for inner_str in usecase_types:
        ratio = fuzz.token_sort_ratio(uctype, inner_str)
        if ratio >= 80 and uctype != inner_str:
            if uctype not in combined_list and inner_str in combined_list: ## taxonomy list reference - only replace if not in the taxonomy list
                full_merge_df["Use Cases"] = full_merge_df["Use Cases"].replace(uctype, inner_str)
            else:
                cm_ratio, cm_max = 0,""
                for cm in combined_list:
                    if fuzz.token_sort_ratio(uctype, cm) > cm_ratio:
                        cm_ratio = fuzz.token_sort_ratio(uctype, cm)
                        cm_max = cm
                if cm_ratio >= 80:
                    full_merge_df["Use Cases"] = full_merge_df["Use Cases"].replace(uctype, cm_max)
                
            usecase_Dict[uctype][inner_str] = ratio
for uctype in usecase_types:
    if uctype.lower().strip() not in product_cats_low:
        if uctype in combined_list:
            full_merge_df.loc[
                full_merge_df["Use Cases"] == uctype, "Product types"
            ] = types_dict[uctype]
            full_merge_df.loc[
                full_merge_df["Use Cases"] == uctype, "Product Subtype"
            ] = subtypes_dict[uctype]

#%%
def get_closest_match(name, name_list):
    max_ratio = 0
    closest_name = ""
    for n in name_list:
        ratio = fuzz.token_set_ratio(name, n)
        if ratio > max_ratio:
            max_ratio = ratio
            closest_name = n
    return closest_name, max_ratio

### Verify use cases

#verified_df = full_merge_df[full_merge_df["Product types"].isin(product_cats)].copy() # lost 30 products
verified_df = full_merge_df.copy()
#verified_df.loc[~verified_df["Product types"].isin(product_cats), "Product types"] = "Incorrect class"

verified_df["label"] = verified_df["Product types"]+"."+verified_df["Product Subtype"]+"."+verified_df["Use Cases"]

taxonomy["label"] = taxonomy["Product types"]+"."+taxonomy["Product Subtype"]+"."+taxonomy["Use Cases"]
#verified_df.dropna(subset=["Use Cases"])
#verified_df.loc[verified_df["label"].isna(), "label"] = "Incorrect class"
success = []
for lab in verified_df["label"].unique():
    if lab not in taxonomy["label"].values and pd.notna(lab):
        print(lab)
        if pd.isna(lab):
            continue
        filter_df = verified_df[verified_df["label"] == lab]
        pdtype = filter_df["Product types"].unique()
        subpdtype = filter_df["Product Subtype"].unique()
        uctype = filter_df["Use Cases"].unique()
        if uctype[0] not in combined_list:
            #print(set(uctype))
            closest_match, ratio = get_closest_match(uctype[0], combined_list)
            if ratio >= 85:
                print(f"Replacing {uctype[0]} with {closest_match} | ratio: {ratio}", "\n")
                verified_df["Use Cases"] = verified_df["Use Cases"].replace(uctype[0], closest_match)
                verified_df.loc[verified_df["label"] == lab, "Present in taxonomy"] = "Yes"
                success.append([ratio,{uctype[0]:closest_match}])
            else:
                #verified_df.loc[verified_df["label"] == lab, "Product types"] = "Unknown class"
                verified_df.loc[verified_df["label"] == lab, "Present in taxonomy"] = "No"
                verified_df.loc[verified_df["label"] == lab, "Reason"] = "use case not found"
        if subpdtype[0] not in combined_list:
            closest_match, ratio = get_closest_match(subpdtype[0], combined_list)
            if ratio >= 85:
                print(f"Replacing {subpdtype[0]} with {closest_match} | ratio: {ratio}", "\n")
                verified_df["Product Subtype"] = verified_df["Product Subtype"].replace(subpdtype[0], closest_match)
                verified_df.loc[verified_df["label"] == lab, "Present in taxonomy"] = "Yes"
                success.append([ratio,{uctype[0]:closest_match}])
            else:
                #verified_df.loc[verified_df["label"] == lab, "Product Subtype"] = "Unknown class"
                verified_df.loc[verified_df["label"] == lab, "Present in taxonomy"] = "No"
                verified_df.loc[verified_df["label"] == lab, "Reason"] = "Product subtype not found"
    else:
        verified_df.loc[verified_df["label"] == lab, "Present in taxonomy"] = "Yes"

## df to work on
#verified_df = full_merge_df[full_merge_df["Product types"].isin(product_cats)].copy()
#verified_df["label"] = verified_df["Product types"]+"."+verified_df["Product Subtype"]+"."+verified_df["Use Cases"]
# for lab in verified_df["label"].unique():
#     if lab not in taxonomy["label"].values:
#         # drop rows meeting this condition
#         verified_df = verified_df[verified_df["label"] != lab]
#### use case validation
#%%
### checking the users: verified_df
users = list(verified_df["User"].unique())
def verify_users(df, users):
    student_df = df[df["User"]==users[0]]
    teacher_df = df[df["User"]==users[1]]
    parent_df = df[df["User"]==users[2]]
    school_df = df[df["User"]==users[3]]

    ver_student_df = student_df[student_df["Product types"] == "Learning"]
    ver_teacher_df = teacher_df[teacher_df["Product types"] == "Teaching"]
    ver_parent_df = parent_df[((parent_df["Product Subtype"] == "Collaborative tools") & (parent_df["Use Cases"] == "Parental Guidance"))
                              | ((parent_df["Product Subtype"] == "Self-Directed Learning") & (parent_df["Use Cases"] == "Homework & Assignment Support"))]
    ver_school_df = school_df[school_df["Product types"] == "Administration & Governance"] 

    return pd.concat([ver_student_df, ver_teacher_df, ver_parent_df, ver_school_df], ignore_index=True)

#clean_df = verify_users(verified_df, users)
clean_df = verified_df[~((verified_df["User"] == "Student") & (verified_df["Product types"] == "Teaching"))].copy() # only lost 3 products that have wrong user product type
# %%
fix_cols = ["Diverse Population"]

def clean_cols(df, cols):
    for col in cols:
        df[col] = df[col].apply(
            lambda x: ",".join(part.strip().strip(".") for part in str(x).split(",")) if pd.notna(x) else x
        )
    return df

clean_df = clean_cols(clean_df, fix_cols)

clean_df["Student User Numbers"] = clean_df["Student User Numbers"].apply(clean_users, args=("student", "pupil"))
clean_df["Teacher User Numbers"] = clean_df["Teacher User Numbers"].apply(clean_users, args=("teacher","tutor"))
clean_df["School User Numbers"] = clean_df["School User Numbers"].apply(clean_users, args=("school","building"))
clean_df["Parent User Numbers"] = clean_df["Parent User Numbers"].apply(clean_users, args=("parent","parents"))

## In school, at home
clean_df["Education Settings"] = clean_df["Education Settings"].apply(lambda x: "Both" if "in-school" in str(x).lower() and "at-home" in str(x).lower() else x)
clean_df["Approach (Learning/Teaching)"] = clean_df["Approach (Learning/Teaching)"].apply(lambda x: x.capitalize() if pd.notna(x) else x)
clean_df["Approach (Learning/Teaching)"] = clean_df["Approach (Learning/Teaching)"].apply(capitalize_values)

# %%
### if product is not used offline, then feature/basic phones will not be supported
def offline_access(row):
    offline = row["Availability of offline access"]
    devices = row["ICT Infrastructure"]

    if pd.isna(offline) or pd.isna(devices):
        return devices
    if offline == "No":
        if "feature" in devices.lower() or ("basic" in devices.lower() and "phone" in devices.lower()):
            devices_list = [d for d in devices.split(",") if d.strip() not in ["Feature phones", "Basic phones", "Feature/Basic Phone"]]
            return ", ".join(devices_list) #if devices_list else pd.NA
        else:
            return devices

clean_df["ICT Infrastructure"] = [offline_access(row) for i,row in clean_df.iterrows()]

clean_df["Language"] = clean_df["Language"].apply(lambda x: ",".join(sorted(list(set([lang.strip().lower() for lang in str(x).split(",")])))) if pd.notna(x) and len(x) <= 3 else x)
clean_df["study_date"] = clean_df["study_date"].apply(lambda x: x.split("-")[0] if pd.notna(x) and len(str(x).split("-")) > 1 else x)
# %%
# Regex for illegal Excel characters
illegal_chars = re.compile(r'[\x00-\x08\x0B-\x1F]')

def clean_excel_string(s):
    if isinstance(s, str):
        return illegal_chars.sub("", s)
    return s

# Apply to all columns
for col in clean_df.select_dtypes(include="object"):
    clean_df[col] = clean_df[col].map(clean_excel_string)

# %%
# create organisations id
i = 1
for org in clean_df["Organisation Name"].unique():
    if pd.isna(org):
        continue
    clean_df.loc[clean_df["Organisation Name"] == org, "Organisation ID"] = i
    i += 1

#%%

clean_df.to_excel(powerbi_dir/"full_products_to_dashboard.xlsx", index=False)
## separate tables
orgs_cols.insert(0, "Organisation ID")
products_col.insert(-1, "Organisation ID")
organisation_df = clean_df[orgs_cols].drop_duplicates(subset="Organisation ID").reset_index(drop=True)
organisation_df.to_excel(powerbi_dir/"organisations_full.xlsx", index=False)

products_df = clean_df[products_col].drop_duplicates(subset="product_id").reset_index(drop=True)
products_df.to_excel(powerbi_dir/"products_full.xlsx", index=False)

use_cases_cols.extend(["Present in taxonomy", "Reason"])
clean_df[use_cases_cols].to_excel(powerbi_dir/"use_cases_full.xlsx", index=False)
clean_df[quality_cols].to_excel(powerbi_dir/"evidence_full.xlsx", index=False)
# %%

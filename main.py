#%%
import ast
from pathlib import Path
import pandas as pd
import yaml
import json
from fuzzywuzzy import fuzz

from src.get_countries import retrieve_countries, country_iso_standards
from src.process import country_cleaning, clean_agents_data, clean_users, capitalize_values

home = Path.home()
if home.name == "evans":
    home = Path("D:/Dropbox")

with open("config.yaml", 'r') as file:
    params = yaml.safe_load(file)

wiki_countries_URL = params["wiki_countries_url"]
country_iso_url = params["country_codes_url"]
headers = params["headers"]
country_cols = params["country_cols"]

## defining paths >> if the path changes, so should this section only, everything else should remain the same
root_dir = home / "Fab Inc Dropbox/Fab Inc BMGF AI/10. Sector mappings"
data_dir = root_dir / "Data"

product_impact_path = data_dir / params["product_impact_path"]
product_types_path = data_dir / params["product_types_path"]
taxonomy_path = data_dir / params["guide_path"]
json_countries = root_dir / params["json_countries_path"]

# %%
product_impacts = pd.read_excel(product_impact_path) # dataframe containing the product impacts
product_types = pd.read_excel(product_types_path) # dataframe containing the product types
taxonomy = pd.read_excel(taxonomy_path, sheet_name="Taxonomy") # dataframe containing the taxonomy

# %%
### focus on the variable_ids that we have, i.e. if the id is blank, then we drop it
product_impacts = product_impacts[product_impacts["variable_group"].notna()].reset_index(drop=True)
product_impacts["variable_group"] = product_impacts["variable_group"].astype(int)

# variable groups we have
variables = list(product_impacts["variable_name"].unique())

product_impacts_copy = product_impacts.copy()
# for i,row in product_impacts.iterrows():
#     clean_agents_data(row)

col = "variable_value"
product_impacts[col] = product_impacts[col].apply(clean_agents_data)
# %%
wide_df = pd.DataFrame()
for k,pro_id in enumerate(product_impacts["product_id"].unique()):
    wide_df.at[k, "product_id"] = pro_id
    prod_subset = product_impacts[product_impacts["product_id"] == pro_id]
    prod_subset = prod_subset[prod_subset["variable_group"].notna()]
    prod_subset = prod_subset.sort_values(by="variable_group")
    for var in variables:
        var_subset = prod_subset[prod_subset["variable_name"] == var]
        if not var_subset.empty:
            var_value = var_subset["variable_value"].values[0]
            wide_df.at[k, var] = var_value

wide_df["product_id"] = wide_df["product_id"].astype(int)
# %%
products_cat_df = pd.DataFrame()
for i,row in product_types.iterrows():
    pro_id = row["product_id"]
    categories_df = pd.DataFrame(ast.literal_eval(row["variable_value"])) if pd.notna(row["variable_value"]) else pd.DataFrame()
    categories_df["product_id"] = pro_id
    products_cat_df = pd.concat([products_cat_df, categories_df], ignore_index=True)
    
# %%
full_df = wide_df.merge(products_cat_df, on="product_id", how="outer")
full_df.drop(columns=['Product Sub-type', 'Product Type', 'Product Use Cases'], inplace=True)
# %%
"""
## 1. merge with the initial dataset (dashboard dataset)
    - remove columns already in the rest of the big df.
## 2. do the cleaning based of the guidelines given by Ana
## 3. verify use case validation and product sub-type based on the taxonomy
## 4. Design the manual changes process - highly descriptive and points to the use of the rights tools (understood by
##   non-technical people) to help in building a better product database. Example is what about a specific product is not quite right?

"""
#%%
#########################x#x#x#x#x#x#x#x#x#x#x##x#x#x#x#x#x#x##x#x#x#x#x#x#x#x#x#x#x#x#*#*#*#*#*#*#*#*#*#*#*
initial_dataset_path = Path(r"D:\Dropbox\Fab Inc Dropbox\Fab Inc BMGF AI\10. Sector mappings\Product Directory Mapping Tool.xlsx")


# load this path
initial_dataset = pd.read_excel(initial_dataset_path)
initial_dataset.rename(columns={"Product_ID":"product_id"}, inplace=True)
use_cols = list(initial_dataset.columns)[:11]
initial_dataset_df = initial_dataset[use_cols].copy()
initial_dataset_df.drop(columns=["Level of Education System"], inplace=True)

# obtain a unique output of the df
initial_dataset_df = initial_dataset_df.drop_duplicates(subset=["product_id","User"], ignore_index=True)

# %%
## full merge
full_merge_df = full_df.merge(initial_dataset_df, on="product_id")


# %%
#### column-by-column cleaning >>> function to clean these columns

full_merge_df["Type of Organisation"] = full_merge_df["Type of Organisation"].replace('For-profit','For-Profit')

for col in ["Product types", "Product Subtype", "Use Cases", "User"]:
    full_merge_df[col] = full_merge_df[col].apply(lambda x: x.strip().strip("\n") if isinstance(x, str) else x)

for col in ["Product types", "Product Subtype", "Use Cases"]:
    taxonomy[col] = taxonomy[col].apply(lambda x: x.strip().strip("\n") if isinstance(x, str) else x)

# full_merge_df["Product types"] = full_merge_df["Product types"].apply(lambda x: x.strip().strip("\n") if isinstance(x, str) else x)
# full_merge_df["Product types"] = full_merge_df["Product types"].replace('Teaching ','Teaching')

# %%

#### country cleaning
with open(json_countries, 'r', encoding='utf-8') as file:
    countries_json = json.load(file)

world_countries = countries_json["objects"]["countries"]["geometries"]
country_names = sorted([item['properties']['name'] for item in world_countries])

alternative_countries = retrieve_countries(wiki_countries_URL, headers)
standard_countries = country_iso_standards(country_iso_url, headers)

[country_cleaning(full_merge_df, col, alternative_countries[1]) for col in country_cols]

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
                print("pdtype")
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
                    full_merge_df["Product types"] = full_merge_df["Product types"].replace(pdtype, cm)
                
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
                    full_merge_df["Product Subtype"] = full_merge_df["Product Subtype"].replace(spdtype, cm)
                
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
                    full_merge_df["Use Cases"] = full_merge_df["Use Cases"].replace(uctype, cm)
                
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
verified_df = full_merge_df[full_merge_df["Product types"].isin(product_cats)].copy()
verified_df["label"] = verified_df["Product types"]+"."+verified_df["Product Subtype"]+"."+verified_df["Use Cases"]

taxonomy["label"] = taxonomy["Product types"]+"."+taxonomy["Product Subtype"]+"."+taxonomy["Use Cases"]
verified_df.dropna(subset=["label"], inplace=True)
for lab in verified_df["label"].unique():
    if lab not in taxonomy["label"].values:
        filter_df = verified_df[verified_df["label"] == lab]
        pdtype = filter_df["Product types"].unique()
        subpdtype = filter_df["Product Subtype"].unique()
        uctype = filter_df["Use Cases"].unique()
        if uctype[0] not in combined_list:
            closest_match, ratio = get_closest_match(uctype[0], combined_list)
            if ratio >= 80:
                print(f"Replacing {uctype[0]} with {closest_match} | ratio: {ratio}", "\n")
                full_merge_df["Use Cases"] = full_merge_df["Use Cases"].replace(uctype[0], closest_match)
            else:
                continue
        if subpdtype[0] not in combined_list:
            closest_match, ratio = get_closest_match(subpdtype[0], combined_list)
            if ratio >= 80:
                print(f"Replacing {subpdtype[0]} with {closest_match} | ratio: {ratio}", "\n")
                full_merge_df["Product Subtype"] = full_merge_df["Product Subtype"].replace(subpdtype[0], closest_match)
            else:
                continue

        

## df to work on
verified_df = full_merge_df[full_merge_df["Product types"].isin(product_cats)].copy()
verified_df["label"] = verified_df["Product types"]+"."+verified_df["Product Subtype"]+"."+verified_df["Use Cases"]
for lab in verified_df["label"].unique():
    if lab not in taxonomy["label"].values:
        # drop rows meeting this condition
        verified_df = verified_df[verified_df["label"] != lab]
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

clean_df = verify_users(verified_df, users)

# %%[]
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
    
# %%

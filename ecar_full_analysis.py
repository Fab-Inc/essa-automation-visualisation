#%%
from pathlib import Path
import yaml

import pandas as pd

with open("config.yaml","r") as file:
    params = yaml.safe_load(file)


# %%
home = Path.home()
if home.name == "evans":
    home = Path("D:/Dropbox")

root_dir = home / params["project_dir"]
data_dir = root_dir / params["ecar_data"]

# %%
# load datasets
ecar_prod_df = pd.read_excel(data_dir / "ECAR_product_table.xls")
ecar_orgs_df = pd.read_excel(data_dir / "ECAR_organisation_table.xls")
ecar_use_case_df = pd.read_excel(data_dir / "ECAR_use_case_table_final.xls")
ecar_evidence_df = pd.read_excel(data_dir / "evidence.xls")
# %%
ddict = {"org": {
            "organisation_id":"organisation_id",
            "Orgnisation_name":"Organisation Name",
            "Type_of_Organisation":"Type of Organisation",
            "Country_headquarters":"Country Headquarters"
        },
        "product": {
            "organisation_id": "organisation_id",
            "product_id":"product_id",
            "Product_name":"Product Name",
            "Product_Website":"Product Website",
            "Product_Launch_Date": "Product Launch Date (Year)",
            "Product_Description": "Product Description",
            "Education_Level":"Level of Education System",
            "Education_Settings": "Education Settings",
            "Local_Curriculum_Alignment": "Local Curriculum Alignment",
            "Approach": "Approach (Learning/Teaching)",
            "ICT_Infrastructure": "ICT Infrastructure",
            "Availability_of_offline": "Availability of offline access",
            "Delivery_Mechanism": "Delivery Mechanism",
            "AI_Modality": "AI Modality",
            "AI_Type": "AI Type",
            "Product_Pricing_Model": "Product Pricing Model",
            "Product_Business_Model": "Product Business Model",
            "Diverse_Population": "Diverse Population",
            "Data_protection": "Data protection",
            "Focus_grade": "Focus grades",
            "Countries_implementing": "Countries Implementing in",
            "User": "User"
        },
        "evidence":{
            "product_id":"product_id",
            "Countries_with_evidence":"country_of_study",
            "Impact": "validation_label",
            "Impact_Link":"download_url"

        },
        "use_cases":{
            "product_id":"product_id",
            "product_type":"Product types",
            "product_subtype":"Product Subtype",
            "use_case": "Use Cases"
        }
}
# %%
index_dict = list(ddict.keys())
for k,df in enumerate([ecar_orgs_df,ecar_prod_df,ecar_evidence_df,ecar_use_case_df]):
    df.rename(columns=ddict[index_dict[k]], inplace=True)

df_list = [ecar_orgs_df,ecar_prod_df,ecar_evidence_df, ecar_use_case_df]
col_list = [list(val.values()) for key,val in ddict.items()]
# %%
def prepare_ecar_data(df, cols):
    new_df = df[cols]

    return new_df

def combine_tables():
    all_tables = [prepare_ecar_data(df,cols) for df,cols in zip(df_list,col_list)]

    first_merge = pd.merge(all_tables[0],all_tables[1], on="organisation_id",how="outer")

    second_merge = pd.merge(all_tables[2],all_tables[3], on="product_id",how="outer")

    final_merge  = pd.merge(first_merge,second_merge, on="product_id",how="outer")

    return final_merge

#%%
ddf = combine_tables()
# %%

import pandas as pd
from datetime import datetime, timedelta
import datetime as dt
import time
import json
import argparse
from sqlalchemy import false
from sqlalchemy import create_engine
from sqlalchemy import text

def main():   
    """

    """ 
    

    # Define lists for use
    # new_final_df = [] # store processed info of all stores to produce a bigger df of outlets

    # Begin iteration
    # Load up json file and extract details
    with open("credentials_2.json", "r") as json_file: # alter credential files here
        loaded_credentials = json.load(json_file)
    # api_key = 'f803b1f2-486e-4de7-9e6c-faa45366bb28'
    # username = loaded_credentials["username"]
    # password = loaded_credentials["password"]
    # recruit_survey_id = loaded_credentials["recruitment_survey"]
    sql_host = loaded_credentials["host"]
    sql_pass = loaded_credentials["sql_password"]
    sql_user = loaded_credentials["sql_user"]
    sql_database= loaded_credentials["sql_database"]
    sql_port = loaded_credentials["port"]

    # Connection to MySQL Engine
    my_conn = create_engine(f"mysql+mysqldb://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{sql_database}")

    def consolidate_tables_to_summaries(con, table_names):
        """
        Loop through tables and append to 2 summary tables
        """
        
        # Begin timer
        start = time.time()

        # Summary Table 1: Product Availability
        summary1_cols = ['Period', 'SubjectNum', 'Date', 'Upload', 'Outlet_Code', 'Store_Name', 'Variable',\
                         'Visit_Availability', 'In_Stock_Status', 'No_of_Facings', 'Display_Location',\
                         'Promotion_Active', 'Type_of_Promotion', 'Promo_Signage', 'Delivery_Source' ]
        summary1_name = 'sku_summary'
        
        # Summary Table 2: Promo/Sales Metrics  
        summary2_cols = ['Period', 'SubjectNum', 'Date', 'Upload', 'Outlet_Code', 'Store_Name', 'Variable',\
                         'Quantity_Delivered', 'Price', 'Estimated_Sales', 'Pack_Quantity', 'Keg_Quantity']
        summary2_name = 'sku_sales_info'
        
        # Create summary tables first (if not exist)
        create_summary1 = f"""
        CREATE TABLE IF NOT EXISTS {summary1_name} (
            Period DATE, 
            SubjectNum VARCHAR(50),
            Date DATETIME,
            Upload DATETIME,
            Variable TEXT,
            Visit_Availability TEXT, 
            In_Stock_Status TEXT,
            No_of_Facings TEXT,
            Display_Location TEXT,
            Promotion_Active TEXT,
            Type_of_Promotion TEXT,
            Promo_Signage TEXT,
            Delivery_Source TEXT
        )
        """
        create_summary2 = f"""
        CREATE TABLE IF NOT EXISTS {summary2_name} (
            Period DATE, 
            SubjectNum VARCHAR(50),
            Date DATETIME,
            Upload DATETIME,
            Variable TEXT,
            Quantity_Delivered DECIMAL(10,2),
            Price DECIMAL(10,2),
            Estimated_Sales DECIMAL(10,2), 
            Pack_Quantity INT, 
            Keg_Quantity INT
        )
        """
        
        # Execute DDL properly
        with con.connect() as conn:
            conn.execute(text(create_summary1))
            conn.execute(text(create_summary2))
            conn.commit()
        
        total_rows1, total_rows2 = 0, 0
        
        # Loop through each table and append
        for table in table_names:
            try:
                # Read table
                # period= "2025-12-20"
                df = pd.read_sql(f"SELECT * FROM {table}", con)
                
                # Summary 1: Summary data
                # Summary 1: Copy what exists (no strict column check)
                available_cols1 = [col for col in summary1_cols if col in df.columns]
                if available_cols1:
                    df_summary1 = df[available_cols1].drop_duplicates()
                    df_summary1.to_sql(summary1_name, con, if_exists='append', index=False, chunksize=1000)
                    total_rows1 += len(df_summary1)
                    print(f"✅ {table} → {summary1_name}: {len(df_summary1)} rows ({len(available_cols1)} cols)")

                # Summary 2: Same fix
                available_cols2 = [col for col in summary2_cols if col in df.columns]
                if available_cols2:
                    df_summary2 = df[available_cols2].drop_duplicates()
                    df_summary2.to_sql(summary2_name, con, if_exists='append', index=False, chunksize=1000)
                    total_rows2 += len(df_summary2)
                    print(f"✅ {table} → {summary2_name}: {len(df_summary2)} rows ({len(available_cols2)} cols)")

                    
            except Exception as e:
                print(f"⚠️ Skipped {table}: {str(e)}")
        
        # End timer
        end = time.time()
        print("-"*40)
        print(f"Program run successfully. It took {round((end - start)/60, 2)} minutes to run.")
    
        print(f"\n🎉 SUMMARY: {total_rows1} rows in {summary1_name}, {total_rows2} rows in {summary2_name}")

        

    # Usage:
    table_names = [
        "abc_lager_300ml_bottle","bel_ice_lemon_330ml_bottle", "brutal_fruit_ruby_apple_spritzer_275ml", "budweiser_355ml_bottle",\
         "club_625ml_bottle", "`club_draught_(bubra)_bottle`", "club_lager_330ml_bottle", "club_shandy_330ml_bottle",\
         "club_shandy_500ml_bottle", "corona_extra_355ml_bottle", "darling_lemon_330ml_bottle", "eagle_extra_stout_375ml_bottle",\
         "eagle_lager_375ml_bottle", "faxe_extra_strong_330ml_can", "faxe_extra_strong_500ml_can", "freedom_beer_330ml_bottle",\
         "freedom_beer_625ml_bottle", "guinness_fes_330ml_bottle", "guinness_smooth_330ml", "heinneken_330ml_bottle",\
         "gulder_625ml_bottle", "hunters_gold_330ml_bottle", "kiss_wild_strawberry_500ml_can", "orijin_300ml_bottle",\
         "orijin_330ml_can", "orijin_625ml_bottle", "savanna_dry_330ml_bottle", "smirnoff_ice_double_black_300ml_bottle",\
         "smirnoff_ice_guarana_vodka_mix_330ml_can", "`smirnoff_ice_original_(red)_300ml_bottle`", "smirnoff_ice_pineapple_punch_300ml_bottle",\
         "star_lager_330ml_bottle", "star_lager_625ml_bottle", "stella_artois_330ml_bottle", "wild_root_625ml_bottle"
    ]

    consolidate_tables_to_summaries(my_conn, table_names)

if __name__ =="__main__":
    main()

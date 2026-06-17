from functions2 import DownloadDetails, RecruitmentDownload
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt
import time
import json
import argparse
from sqlalchemy import false
from sqlalchemy import create_engine


def main():   
    """
        The function runs in an argument parser format to download one of the
        file types below from field stored in the STG app. Along with selecting
        the file type, users should also select the date(s) for which they want
        data for. 
        The table below shows on the LHS the expected arguments to be passed for
        the file type.
        
        File Types from Field
        =====================
        Input format              | File descriptive name
        ----------------------------------------------
        1. "recruit_profile"      | respondent profile
        2. "outlet_describe"      | ad and fridge branding
        3. "product_price"        | price of products
        4. "product_availability" | available products
        5. "product_status"       | product selling status

        Date convention
        ===============
        Dates or periods for download should be passed using the following format:
        YYYY-MM-DD
        Eg. 2024-01-23

        Usage
        =====
        py main_argparse.py -f [file] -s [YYYY-MM-DD] -e [YYYY-MM-DD]
        py main_argparse.py --file recruit_profile --start 2026-06-07 --end 2026-06-07
        py main_argparse.py -f product_availability -s 2026-06-07 -e 2026-06-07

        The above code downloads recruitment profile for the period 7th June 2026.

        Returns:
            pd.DataFrame
    """ 
    # Begin timer
    start = time.time()

    # Define lists for use
    new_final_df = [] # store processed info of all stores to produce a bigger df of outlets

    # Begin iteration
    # Load up json file and extract details
    with open("credentials_2.json", "r") as json_file: # alter credential files here
        loaded_credentials = json.load(json_file)
    api_key = 'f803b1f2-486e-4de7-9e6c-faa45366bb28'
    username = loaded_credentials["username"]
    password = loaded_credentials["password"]
    recruit_survey_id = loaded_credentials["recruitment_survey"]
    sql_host = loaded_credentials["host"]
    sql_pass = loaded_credentials["sql_password"]
    sql_user = loaded_credentials["sql_user"]
    sql_database= loaded_credentials["sql_database"]
    sql_port = loaded_credentials["port"]

    # Connection to MySQL Engine
    # my_conn = create_engine("mysql+mysqldb://root:T0pGunMaver123@localhost/maverick_db")
    my_conn = create_engine(f"mysql+mysqldb://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{sql_database}")

    # Setup parser arguments
    parser = argparse.ArgumentParser(description="Download Maverick Raw data from STG in different formats.")
    parser.add_argument("-f", "--file", type=str, metavar='', required=True, help="select the file type you want downloaded")
    parser.add_argument("-s", "--start", type=str, metavar='', required=True, help="input start date in YYYY-MM-DD format")
    parser.add_argument("-e", "--end", type=str, metavar='', required=True, help="input end date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    # Execute commands to download different file types
    if args.file == "recruit_profile":
        first_day = datetime.strptime(args.start, "%Y-%m-%d")
        last_day = datetime.strptime(args.end, "%Y-%m-%d")
        
        date_list = [first_day + timedelta(days=x) for x in range((last_day - first_day).days + 1)]
        date_list_formatted = [date.strftime("%Y-%m-%d") for date in date_list]
            
        for found_date in date_list_formatted:
            try:
                general = DownloadDetails()
                recruit = RecruitmentDownload()
                
                new_list = general.get_store_id(api_key, username, password, recruit_survey_id, found_date) # get store ids for given period, returns a list of store ids
                for outlet in new_list: # iterate through ids, transform their data and append them to a big list
                    dataframe_return = recruit.transform_recruitment_profile(outlet, recruit_survey_id, api_key, username, password)
                    new_final_df.append(dataframe_return)           
                # Save processed stores data
                merged_df = pd.concat(new_final_df, axis=0)
                merged_df.insert(0, 'Period', dt.datetime.today().replace(day=1).date().strftime('%Y-%m-%d')) # Add 'period' column
                # merged_df.to_excel(f'recruit_profile_{args.start}_{args.end}.xlsx', index=False)
                merged_df.to_sql(con=my_conn, name='recruit_profile', if_exists='append', index=False) # consider appending/replacing in some cases
                print("="*40)
                print("Finished process")
            except ValueError:
                print("No subject ids for the day!")
                print("="*40) 
    
    ## ------------------------------------------------------------------------------------------------------------------------------------------
    elif args.file == "outlet_describe":
    
        first_day = datetime.strptime(args.start, "%Y-%m-%d")
        last_day = datetime.strptime(args.end, "%Y-%m-%d")
        
        date_list = [first_day + timedelta(days=x) for x in range((last_day - first_day).days + 1)]
        date_list_formatted = [date.strftime("%Y-%m-%d") for date in date_list]
            
        for found_date in date_list_formatted:
            try:
                general = DownloadDetails()
                recruit = RecruitmentDownload()

                new_list = general.get_store_id(api_key, username, password, recruit_survey_id, found_date) # get store ids for given period, returns a list of store ids
                for outlet in new_list: # iterate through ids, transform their data and append them to a big list
                    dataframe_return = recruit.transform_outlet_description(outlet, recruit_survey_id, api_key, username, password)
                    new_final_df.append(dataframe_return)           
                # Save processed stores data
                merged_df = pd.concat(new_final_df, axis=0)
                merged_df.insert(0, 'Period', dt.datetime.today().replace(day=1).date().strftime('%Y-%m-%d')) # Add 'period' column
                # merged_df.to_excel(f'outlet_describe_{args.start}_{args.end}.xlsx', index=False)
                merged_df.to_sql(con=my_conn, name='outlet_describe', if_exists='append', index=False) # consider appending/replacing in some cases
                print("="*40)
                print("Finished process")
            except ValueError:
                print("No subject ids for the day!")
                print("="*40) 
    ## ------------------------------------------------------------------------------------------------------------------------------------------
    elif args.file == "product_availability":
    
        first_day = datetime.strptime(args.start, "%Y-%m-%d")
        last_day = datetime.strptime(args.end, "%Y-%m-%d")
        
        date_list = [first_day + timedelta(days=x) for x in range((last_day - first_day).days + 1)]
        date_list_formatted = [date.strftime("%Y-%m-%d") for date in date_list]
            
        for found_date in date_list_formatted:
            try:
                general = DownloadDetails()
                recruit = RecruitmentDownload()

                new_list = general.get_store_id(api_key, username, password, recruit_survey_id, found_date) # get store ids for given period, returns a list of store ids
                for outlet in new_list: # iterate through ids, transform their data and append them to a big list
                    dataframe_return = recruit.transform_product_availability(outlet, recruit_survey_id, api_key, username, password)
                    new_final_df.append(dataframe_return)           
                # Save processed stores data
                merged_df = pd.concat(new_final_df, axis=0)
                merged_df.insert(0, 'Period', dt.datetime.today().replace(day=1).date().strftime('%Y-%m-%d')) # Add 'period' column
                # merged_df.to_excel(f'product_availability_{args.start}_{args.end}.xlsx', index=False)
                merged_df.to_sql(con=my_conn, name='product_availability', if_exists='append', index=False) # consider appending/replacing in some cases
                print("="*40)
                print("Finished process")
            except ValueError:
                print("No subject ids for the day!")
                print("="*40) 
    ## ------------------------------------------------------------------------------------------------------------------------------------------
    elif args.file == "product_price":
    
        first_day = datetime.strptime(args.start, "%Y-%m-%d")
        last_day = datetime.strptime(args.end, "%Y-%m-%d")
        
        date_list = [first_day + timedelta(days=x) for x in range((last_day - first_day).days + 1)]
        date_list_formatted = [date.strftime("%Y-%m-%d") for date in date_list]
            
        for found_date in date_list_formatted:
            try:
                general = DownloadDetails()
                recruit = RecruitmentDownload()
                
                new_list = general.get_store_id(api_key, username, password, recruit_survey_id, found_date) # get store ids for given period, returns a list of store ids
                
                for outlet in new_list: # iterate through ids, transform their data and append them to a big list
                    dataframe_return = recruit.transform_product_price(outlet, recruit_survey_id, api_key, username, password)
                    new_final_df.append(dataframe_return)           
                # Save processed stores data
                merged_df = pd.concat(new_final_df, axis=0)
                merged_df.insert(0, 'Period', dt.datetime.today().replace(day=1).date().strftime('%Y-%m-%d')) # Add 'period' column
                # merged_df.to_excel(f'product_price_{args.start}_{args.end}.xlsx', index=False)
                merged_df.to_sql(con=my_conn, name='product_price', if_exists='append', index=False) # consider appending/replacing in some cases
                print("="*40)
                print("Finished process")
            except ValueError:
                print("No subject ids for the day!")
                print("="*40) 
    ## ------------------------------------------------------------------------------------------------------------------------------------------
    elif args.file == "product_status":
    
        first_day = datetime.strptime(args.start, "%Y-%m-%d")
        last_day = datetime.strptime(args.end, "%Y-%m-%d")
        
        date_list = [first_day + timedelta(days=x) for x in range((last_day - first_day).days + 1)]
        date_list_formatted = [date.strftime("%Y-%m-%d") for date in date_list]
            
        for found_date in date_list_formatted:
            try:
                general = DownloadDetails()
                recruit = RecruitmentDownload()
                
                new_list = general.get_store_id(api_key, username, password, recruit_survey_id, found_date) # get store ids for given period, returns a list of store ids
                
                for outlet in new_list: # iterate through ids, transform their data and append them to a big list
                    dataframe_return = recruit.transform_product_status(outlet, recruit_survey_id, api_key, username, password)
                    new_final_df.append(dataframe_return)           
                # Save processed stores data
                merged_df = pd.concat(new_final_df, axis=0)
                merged_df.insert(0, 'Period', dt.datetime.today().replace(day=1).date().strftime('%Y-%m-%d')) # Add 'period' column
                # merged_df.to_excel(f'product_status_{args.start}_{args.end}.xlsx', index=False)
                merged_df.to_sql(con=my_conn, name='product_status', if_exists='append', index=False) # consider appending/replacing in some cases
                print("="*40)
                print("Finished process")
            except ValueError:
                print("No subject ids for the day!")
                print("="*40) 
    else:
        print("Your input is not valid!")
    
    
    # End timer
    end = time.time()
    print("-"*40)
    print(f"Program run successfully. It took {round((end - start)/60, 2)} minutes to run.")


if __name__ =="__main__":
    main()
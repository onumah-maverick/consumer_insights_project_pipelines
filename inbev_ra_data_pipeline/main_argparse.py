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
        Input format           | File descriptive name
        ----------------------------------------------
        1. "recruit_profile"   | shop profile
        2. "social"            | individual beverage brand details

        Date convention
        ===============
        Dates or periods for download should be passed using the following format:
        YYYY-MM-DD
        Eg. 2024-01-23

        Usage
        =====
        py main_argparse.py -f [file] -s [YYYY-MM-DD] -e [YYYY-MM-DD]
        py main_argparse.py --file recruit_profile --start 2025-10-17 --end 2025-10-18
        py main_argparse.py -f recruit_profile -s 2025-10-17 -e 2026-17-18

        The above code downloads audit capture profile for the periods 17th October 2025
        to 18th October 2025

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
    api_key = 'paste here'
    username = loaded_credentials["username"]
    password = loaded_credentials["password"]
    recruit_survey_id = loaded_credentials["recruitment_survey"]
    sql_host = loaded_credentials["host"]
    sql_pass = loaded_credentials["sql_password"]
    sql_user = loaded_credentials["sql_user"]
    sql_database= loaded_credentials["sql_database"]
    sql_port = loaded_credentials["port"]

    # Connection to MySQL Engine
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
                # merged_df.to_excel(f'profile_{args.start}_{args.end}.xlsx', index=False)
                merged_df.to_sql(con=my_conn, name='profile', if_exists='append', index=False) # consider appending/replacing in some cases
                print("="*40)
                print("Finished process")
            except ValueError:
                print("No subject ids for the day!")
                print("="*40) 
    ## ------------------------------------------------------------------------------------------------------------------------------------------
    elif args.file == "social":
        first_day = datetime.strptime(args.start, "%Y-%m-%d")
        last_day = datetime.strptime(args.end, "%Y-%m-%d")
        
        date_list = [first_day + timedelta(days=x) for x in range((last_day - first_day).days + 1)]
        date_list_formatted = [date.strftime("%Y-%m-%d") for date in date_list]
        
        for found_date in date_list_formatted:
            try:
                general = DownloadDetails()
                recruit = RecruitmentDownload()
                new_list = general.get_store_id(api_key, username, password, recruit_survey_id, found_date)
                
                for count, outlet in enumerate(new_list):
                    print(f"Load: {count} | Date: {found_date} | Outlet: {outlet}")
                    
                    # Get list of transformed DataFrames (NOT dict)
                    table_list = recruit.transform_social_profile(outlet, recruit_survey_id, api_key, username, password)
                    
                    if not table_list:
                        print(f"No data for outlet {outlet}")
                        continue
                    
                    # Add Period column and save each table
                    for i, df in enumerate(table_list):
                        # Get variable name from DataFrame (first row, Variable column)
                        variable_name = df['Variable'].iloc[0] if 'Variable' in df.columns else f"table_{i}"
                        table_name_lower = variable_name.lower().replace(" ", "_").replace("/", "_")
                        
                        # Add Period column
                        df.insert(0, 'Period', dt.datetime.today().replace(day=1).date().strftime('%Y-%m-%d'))
                        
                        # Save to Excel
                        # filename = f'{table_name_lower}_{args.start}_{args.end}.xlsx'
                        # df.to_excel(filename, index=False)
                        # print(f"Saved: {filename} ({df.shape[0]} rows, {df.shape[1]} cols)")
                        sql_table = table_name_lower.replace(" ","_").replace("-","_")[:64]
                        df.to_sql(con=my_conn, name=sql_table, if_exists='append', index=False, chunksize=1000, method='multi')
                        print(f"Saved to SQL: {sql_table}")            
                    print("="*60)
                    print(f"✅ Finished outlet {outlet} | {len(table_list)} tables saved")
                
            except TypeError as ve:#ValueError as ve:
                print(f"No subject IDs for {found_date}: {ve}")
            except Exception as e:
                print(f"Error processing {found_date}: {str(e)}")
            finally:
                print("="*60)
    else:
        print("Invalid file type!")
    
    
    # End timer
    end = time.time()
    print("-"*40)
    print(f"Program run successfully. It took {round((end - start)/60, 2)} minutes to run.")


if __name__ =="__main__":
    main()

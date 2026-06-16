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
    Tooling to create auxiliary tables from "brand_awareness" table.  
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
    my_conn = create_engine(f"mysql+mysqldb://{sql_user}:{sql_pass}@{sql_host}:{sql_port}/{sql_database}")

    def awareness_pull(database, start_date, end_date):
        """
        Reads and queries data from the "brand_awareness" table for a given period.
        """
        # SQL query to run
        query = f""" SELECT * FROM {database}.brand_awareness where Upload BETWEEN '{start_date}' AND '{end_date}';"""
        # Read result into dataframe
        raw_data = pd.read_sql(query, my_conn)
        
        return raw_data
    
    
    def modify_table(column_name):
        """
        Creates new table with single column name and unique Subject numbers
        """
        # Save datafetch from "brand_awareness" table
        data_table = awareness_pull('nutrifoods_bht', '2025-10-30 00:00:00','2025-10-31 00:00:00')
        # Create pivot table from specific column in "brand_awareness" table
        # table_pivot = data_table.pivot_table(index=column_name, values='SubjectNum', aggfunc=pd.Series.nunique).reset_index()
        table_pivot = data_table.groupby('SubjectNum').agg(Distinct_SubjectNum_Count=('SubjectNum', 'nunique'), Product_List=(f'{column_name}', lambda x: ', '.join(x.unique().astype(str))))
        # Convert pivot table into normal dataframe
        output = table_pivot.reset_index()
        # Save results in new table bearing column name
        output_table = output.to_sql(con=my_conn, name=column_name, if_exists='append', index=False)
        print("Database load-up done")
        return output_table

    iterator_list = ['biscuit_tom', 'biscuit_awareness', 'biscuit_extra_aware', 'biscuit_advertising', 'biscuit_consumed',\
        'biscuit_consumed_months', 'biscuit_consumed_days', 'biscuit_consumed_often', 'biscuit_consumed_mcberry',\
        'biscuit_consumed_nutrisnax', 'biscuit_consumed_perk', 'biscuit_consumed_royal', 'biscuit_consumed_yum']
  

    # Recursively populate database tables
    for i, j in enumerate(iterator_list):
        print(f'Loading Data: {j} table')
        print(time.strftime('%d/%m/%Y %H:%M:%S'))
        print(modify_table(j), end="\n\n")


if __name__ =="__main__":
    main()
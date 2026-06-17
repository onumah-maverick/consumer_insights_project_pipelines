import datetime
import json
import time
import warnings
from typing import Dict, List , Union 
import numpy as np

import bs4
import pandas as pd
import requests
from copy import deepcopy
from bs4 import BeautifulSoup
from mysql.connector.constants import ClientFlag
from requests.auth import HTTPBasicAuth
from sqlalchemy import false
from sqlalchemy import create_engine
from tqdm import tqdm
import xml.etree.ElementTree as ET
import csv
import tempfile
import datetime as dt
import time
from datetime import datetime, timedelta
import re

class DownloadDetails:
    @staticmethod
    def data_formatting(surveyIDs):
            '''
            This function performs data cleaning operations on extracted subject ids stored in a list.
            Gets response text from API pull and removes unwanted punctuations. 
            
            Argument:
                surveyIDs (list)
            
            Returns:
                list: An expected list format
            '''
            surveyIDs = surveyIDs.replace('[', '')
            surveyIDs = surveyIDs.replace(']', '')
            surveyIDs = surveyIDs.replace('\r', '')
            surveyIDs = surveyIDs.replace('\n', '')
            surveyIDs = surveyIDs.strip()
            surveyIDs = surveyIDs.replace(' ', '')
            surveyIDs = surveyIDs.split(',')
            return surveyIDs

# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def get_store_id(api_key, username, password, survey_id, prime_date):
        """
        This function extracts the survey ids given a specific survey id and date periods.
        The data cleaning function is then called on the extracted ids.

        Arguments:
            prime_date (iterator variable from list)
            survey_id (str)

        Returns:
            list: List containing subject ids for the prime date
        """
        start_date = end_date = prime_date
        print(start_date, end_date, sep='\n')

        # Download features
        url = f'http://api.dooblo.net/newapi/SurveyInterviewIDs?surveyIDs={survey_id}&dateStart={start_date}T00%3a00%3a00.0000000%2b00%3a00&dateEnd={end_date}T23%3a59%3a59.9990000%2b00%3a00&dateType=Upload'
        payload = {}
        headers = {
            'Cookie': 'ASP.NET_SessionId=fqtuuiimuc0ij43ejti02ktu'
        }
        response = requests.request("GET", url, headers=headers, data=payload, auth=HTTPBasicAuth(
            f"{api_key}/{username}", f"{password}"))
        print('HTTP Request response completed')
        surveyIDs = response.text
        backbone = DownloadDetails()
        list_subjects = backbone.data_formatting(surveyIDs)
        print(f"Number of subject ids: {len(list_subjects)}") # store extracted subject_ids in a list
        print("-"*40)
        return list_subjects  

# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def download_xml(subj_id, survey_id, api_key, username, password):
        """
        This function downloads retail audit data for a given subject id. Makes API call to STG servers.
        Displays information containing outlet name, auditor, audited items.
        
        Arguments:
            subj_id (str): a single subject id from the list of subject ids
            survey_id (str): ID for survey
            api_key (str): API Key
            username (str): User name
            password (str): User password
        
        Returns:
            response (xml formatted data)
        """    
        url = f"http://api.dooblo.net/newapi/SurveyInterviewData?subjectIDs={subj_id}&surveyID={survey_id}&onlyHeaders=false&includeNulls=false"
        payload = {}
        headers = {
            'Cookie': 'ASP.NET_SessionId=fqtuuiimuc0ij43ejti02ktu',
            'Accept': 'text/xml',
            'accept-encoding': 'UTF-8'
        }
        response = requests.request("GET", url, headers=headers, data=payload, auth=HTTPBasicAuth(
            f"{api_key}/{username}", f"{password}"))
        return response

# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def xml_to_list(response):
        """
        This function parses the xml formatted data into a list format.
        
        Argument:
            response(xml formatted data)
        
        Returns:
            data(list)
        """
        # Initialize lists to store data
        data = []

        # Parse the XML content directly from the response text
        root = ET.fromstring(response.text)

        # Extract data from XML tree
        for element in root.iter():
            if element.text and element.text.strip():
                data.append([element.tag, "text", element.text])
            for attribute, value in element.attrib.items():
                data.append([element.tag, attribute, value])
        return data
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def explode_columns(df, columns, split_value):
        """
        Explode multiple comma-separated columns into new rows.
        Keeps other columns duplicated.
        Drops rows where all target columns are NaN.
        """
        if isinstance(columns, str):
            columns = [columns]

        df = df.copy()

        # 1. Drop rows where all target columns are NaN
        df = df.dropna(subset=columns, how="all")

        # 2. Convert strings into lists
        def to_list(x):
            if pd.isna(x):
                return []   # explode will drop these
            return [v.strip() for v in str(x).split(split_value) if v.strip()]

        for col in columns:
            df[col] = df[col].apply(to_list)

        # 3. Explode sequentially
        for col in columns:
            df = df.explode(col, ignore_index=True)

        return df
    
# ------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------
class RecruitmentDownload:
    @staticmethod
    def transform_recruitment_profile(subj_id, survey_id, api_key, username, password):
        """
        Extract the values you need
        The parsed xml data is grouped into chapters. The target chapters list is used to select the desired chapters.
        The chapters are stored in a dataframe from which the necessary variables are selected.
        """
        try:
            backbone = DownloadDetails()
            response = backbone.download_xml(subj_id, survey_id, api_key, username, password)
            data_list = backbone.xml_to_list(response)
            df = pd.DataFrame(data_list, columns=["Element", "Attribute", "Value"])
            #---------------------------------------------------------------------------------------------------------------------
            df_items_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['Enumerator_Name', 'gps_address', 'Visit_Date', 'Region', 'Store_Name',
                        'Contact', 'Outlet_Code',]

            # Initialize a dictionary to store extracted values
            extracted_data = {}

            # Iterate through the list of variables
            for variable in variables:
                # Find the index where 'Element' is 'FullVariable' and 'Value' is the current variable
                indices = df_items_use.index[(df_items_use['Element'] == 'FullVariable') & (df_items_use['Value'] == variable)]

                if not indices.empty:
                    index = indices[0]  # Get the first index if it exists
                    # Check if there is a next row
                    if index + 1 < len(df_items_use):
                        extracted_value = df_items_use.loc[index + 1, 'Value']
                    else:
                        extracted_value = float('nan')  # Assign NaN if there is no next row
                else:
                    extracted_value = None  # Assign None if the variable is not found

                # Assign the extracted value to the corresponding variable in the dictionary
                extracted_data[variable] = extracted_value

            # Create a DataFrame from the extracted data
            audit_items_df = pd.DataFrame([extracted_data])

            # Splitting up GPS attributes into individual columns
            # Regex pattern to extract the desired fields
            pattern = (
                r'Latitude:\s*(.*?)\s*\(.*?\)\r?\n'
                r'\s*Longitude:\s*(.*?)\s*\(.*?\)\r?\n'
                r'\s*Captured at:\s*(.*?)\r?\n'
                r'(?:\s*Altitude:\s*(.*?)\r?\n)?'
                r'(?:\s*Bearing:\s*(.*?)\r?\n)?'
                r'(?:\s*Speed:\s*(.*?)(?:\s*km/h)?\s*)?')

            cols = ['GPS_Latitude', 'GPS_Longitude', 'GPS_Date', 'GPS_Altitude', 'GPS_Bearing', 'GPS_Speed (km/h)']
            audit_items_df[cols] = audit_items_df['gps_address'].str.extract(pattern, expand=True)
            audit_items_df.drop(columns=["gps_address"], inplace=True) # Remove original GPS column
            #-------------------------------------------------------------------------------------------------------------
            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','VisitStart','VisitEnd','ClientDuration','Date'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            durations = df_result_extract[df_result_extract['Element'] == 'ClientDuration']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()
            visit_starts = df_result_extract[df_result_extract['Element'] == 'VisitStart']['Value'].tolist()
            visit_ends = df_result_extract[df_result_extract['Element'] == 'VisitEnd']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                              'VisitStart': visit_starts[0] if visit_starts else None,
                              'VisitEnd': visit_ends[0] if visit_ends else None,
                              'NetDuration': durations[0] if durations else None,
                              'Date': dates[0] if dates else None,
                              'Upload': uploads[0] if uploads else None}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            transformed_dataframes.append(df_transformed)

            # Concatenate all transformed dataframes into a single dataframe
            df_pivoted = pd.concat(transformed_dataframes, ignore_index=True)
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['Date'] = df_pivoted['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['VisitStart'] = df_pivoted['VisitStart'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['VisitEnd'] = df_pivoted['VisitEnd'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S') if (isinstance(x, str) and len(x)>0) else None)
           
            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)

        except ArithmeticError:
            print("Desired values not available")
        else:
            return new_combined_df
# -----------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_social_profile(subj_id, survey_id, api_key, username, password):
        """
        Extract the values you need
        The parsed xml data is grouped into chapters. The target chapters list is used to select the desired chapters.
        The chapters are stored in a dataframe from which the necessary variables are selected.
        """
        try:
            backbone = DownloadDetails()
            response = backbone.download_xml(subj_id, survey_id, api_key, username, password)
            data_list = backbone.xml_to_list(response)
            df = pd.DataFrame(data_list, columns=["Element", "Attribute", "Value"])
            df_items_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)

            # Product variables and metrics
            variables = ['BUDWEISER 355ML BOTTLE','CLUB LAGER 330ML BOTTLE','CLUB 625ML BOTTLE','CLUB DRAUGHT (BUBRA) BOTTLE',\
                        'CORONA EXTRA 355ML BOTTLE','EAGLE LAGER 375ML BOTTLE','EAGLE EXTRA STOUT 375ML BOTTLE','STELLA ARTOIS 330ML BOTTLE',\
                        'CLUB SHANDY 330ML BOTTLE','CLUB SHANDY 500ML BOTTLE','WILD ROOT 625ML BOTTLE','BRUTAL FRUIT RUBY APPLE SPRITZER 275ML',\
                        'ABC LAGER 300ML BOTTLE','GUINNESS FES 330ML BOTTLE','GUINNESS SMOOTH 330ML','HEINNEKEN 330ML BOTTLE',\
                        'STAR LAGER 330ML BOTTLE','STAR LAGER 625ML BOTTLE','GULDER 625ML BOTTLE','ORIJIN 300ML BOTTLE','ORIJIN 625ML BOTTLE',\
                        'ORIJIN 330ML CAN','SMIRNOFF ICE DOUBLE BLACK 300ML BOTTLE','SMIRNOFF ICE GUARANA VODKA MIX 330ML CAN',\
                        'SMIRNOFF ICE PINEAPPLE PUNCH 300ML BOTTLE','SMIRNOFF ICE ORIGINAL (RED) 300ML BOTTLE','FREEDOM BEER 330ML BOTTLE',\
                        'FREEDOM BEER 625ML BOTTLE','HUNTERS GOLD 330ML BOTTLE','SAVANNA DRY 330ML BOTTLE','DARLING LEMON 330ML BOTTLE',\
                        'FAXE EXTRA STRONG 330ML CAN','FAXE EXTRA STRONG 500ML CAN','KISS WILD STRAWBERRY 500ML CAN','BEL ICE LEMON 330ML BOTTLE']

            metrics = ['Visit_Availability','In_Stock_Status', 'No_of_Facings', 'Display_Location', 'Promotion_Active',\
                    'Type_of_Promotion', 'Promo_Signage', 'Delivery_Source', 'Quantity_Delivered', 'Price',\
                    'Estimated_Sales', 'Pack_Quantity', 'Keg_Quantity']

            # Create DataFrames for each variable
            variable_dfs = {}
            for variable in variables:
                variable_data = {}
                for metric in metrics:
                    extended_variable = f"{variable}_{metric}"
                    indices = df_items_use.index[
                        (df_items_use['Element'] == 'FullVariable') & 
                        (df_items_use['Value'] == extended_variable)
                    ]
                    
                    if not indices.empty:
                        index = indices[0]
                        extracted_value = df_items_use.loc[index + 1, 'Value'] if index + 1 < len(df_items_use) else float('nan')
                    else:
                        extracted_value = None
                    
                    variable_data[metric] = extracted_value
                
                df_variable = pd.DataFrame([variable_data])
                df_variable['Variable'] = variable
                cols = ['Variable'] + metrics
                variable_dfs[variable] = df_variable[cols]

            # Create table_list from dictionary (no manual assignments needed)
            table_list = [variable_dfs[var] for var in variables if var in variable_dfs]

            # Create auxiliary table (SubjectNum, Date, Upload)
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','Date'])]
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']]

            extracted_data = {
                'SubjectNum': df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].iloc[0] if not df_result_extract[df_result_extract['Element'] == 'SubjectNum'].empty else None,
                'Date': df_result_extract[df_result_extract['Element'] == 'Date']['Value'].iloc[0] if not df_result_extract[df_result_extract['Element'] == 'Date'].empty else None,
                'Upload': df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].iloc[0] if not df_result_extract[df_result_extract['Element'] == 'Upload'].empty else None
            }

            df_pivoted = pd.DataFrame([extracted_data])
            
            # Convert datetime strings (safer handling)
            for col in ['Upload', 'Date']:
                if col in df_pivoted.columns and pd.notna(df_pivoted[col].iloc[0]):
                    try:
                        cleaned_date = re.sub('T|Z', '', str(df_pivoted[col].iloc[0]))
                        df_pivoted[col] = pd.to_datetime(cleaned_date, format='%Y-%m-%d%H:%M:%S')
                    except:
                        pass  # Keep as-is if conversion fails

            # Add auxiliary table + explode Display_Location for ALL tables
            for i, table in enumerate(table_list):
                # Concat auxiliary table
                table_list[i] = pd.concat([df_pivoted, table], axis=1)
                
                # Explode Display_Location column (split by comma)
                if 'Display_Location' in table_list[i].columns:
                    # Convert to string and split by comma first (if not already list)
                    table_list[i]['Display_Location'] = table_list[i]['Display_Location'].astype(str).str.split(',')
                    table_list[i] = table_list[i].explode('Display_Location')
                    table_list[i]['Display_Location'] = table_list[i]['Display_Location'].str.strip()
                
                print(f"Table {i+1}: {table_list[i].shape}")

            return table_list

        except Exception as e:
            print(f"Error in transform_social_profile: {str(e)}")
            return []

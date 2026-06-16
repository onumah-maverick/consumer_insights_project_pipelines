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
    
    @staticmethod
    def transform_categories_and_segments(df):
        """
        Transforms a DataFrame to expand rows based on 'Category', 'segment_wet', and 'segment_dry' columns.
        Handles single, multiple (comma-separated), and specific 'Wet'/'Dry Hair' paired logic.

        Args:
            df (pd.DataFrame): The input DataFrame. Expected columns:
                            'Period', 'SubjectNum', 'Date', 'Upload', 'Outlet_code',
                            'Category', 'segment_wet', 'segment_dry'.

        Returns:
            pd.DataFrame: A new DataFrame with expanded rows.
        """
       
        result_rows = []

        for idx, row in df.iterrows():
            categories = [c.strip() for c in str(row.get('Category', '')).split(',')] if pd.notna(row.get('Category')) else ['']
            cat_lower_sorted = sorted([c.lower() for c in categories])

            # Special 'Wet' + 'Dry Hair' combo, keep same logic
            if cat_lower_sorted == ['dry hair', 'wet']:
                segment_wet = [s.strip() for s in str(row.get('segment_wet', '')).split(',')] if pd.notna(row.get('segment_wet')) else ['']
                segment_dry = [s.strip() for s in str(row.get('segment_dry', '')).split(',')] if pd.notna(row.get('segment_dry')) else ['']

                # Explode 'Wet' rows
                for wet_val in segment_wet:
                    new_row = row.copy()
                    new_row['Category'] = 'Wet'
                    new_row['segment_wet'] = wet_val
                    new_row['segment_dry'] = ''
                    result_rows.append(new_row)

                # Explode 'Dry Hair' rows
                for dry_val in segment_dry:
                    new_row = row.copy()
                    new_row['Category'] = 'Dry Hair'
                    new_row['segment_dry'] = dry_val
                    new_row['segment_wet'] = ''
                    result_rows.append(new_row)

            else:
                # For other cases, explode Category, segment_wet, and segment_dry individually
                # Step 1: make lists from each column or set to [''] for empty/NaN
                cats = [c.strip() for c in str(row.get('Category', '')).split(',')] if pd.notna(row.get('Category')) else ['']
                wets = [s.strip() for s in str(row.get('segment_wet', '')).split(',')] if pd.notna(row.get('segment_wet')) else ['']
                drys = [s.strip() for s in str(row.get('segment_dry', '')).split(',')] if pd.notna(row.get('segment_dry')) else ['']

                # Step 2: For each exploded category, explode wet and dry segment values separately
                # This will generate combined rows for all wet and dry segments matched with categories

                # To avoid a full cartesian product of all three exploded columns (which can get big),
                # you can explode Category first, then explode wet and dry separately per category if needed

                # Explode category first
                for cat in cats:
                    # For each category, explode wet segments
                    for wet_val in wets:
                        new_row = row.copy()
                        new_row['Category'] = cat
                        new_row['segment_wet'] = wet_val
                        new_row['segment_dry'] = ''
                        result_rows.append(new_row)

                    # Then explode dry segments similarly
                    for dry_val in drys:
                        new_row = row.copy()
                        new_row['Category'] = cat
                        new_row['segment_wet'] = ''
                        new_row['segment_dry'] = dry_val
                        result_rows.append(new_row)

        # Combine all exploded rows into one dataframe
        combined_df = pd.DataFrame(result_rows).reset_index(drop=True)

        return combined_df

# ------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------
class RecruitmentDownload:
    @staticmethod
    def transform_location(subj_id, survey_id, api_key, username, password):
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
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)
            #df_items_use['Value'] = df_items_use['Value'].str.replace(r'I_\d+_', '', regex=True)

            # List of FullVariable values to extract
            variables = ['Outlet_code', 'GPS']

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
            audit_items_df[cols] = audit_items_df['GPS'].str.extract(pattern, expand=True)
            audit_items_df.drop(columns=["GPS"], inplace=True) # Remove original GPS column

            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Date','Upload'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                              'Date': dates[0] if dates else None,
                              'Upload': uploads[0] if uploads else None}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            transformed_dataframes.append(df_transformed)

            # Concatenate all transformed dataframes into a single dataframe
            df_pivoted = pd.concat(transformed_dataframes, ignore_index=True)
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['Date'] = df_pivoted['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
               
            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)

        except TypeError:
            print("Desired values not available")
        # except ET.ParseError:
        #     print("Problem with xml")
        else:
            return new_combined_df

# ------------------------------------------------------------------------------------------------------------------------------------------
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
            df_items_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)
            #df_items_use['Value'] = df_items_use['Value'].str.replace(r'I_\d+_', '', regex=True)

            # List of FullVariable values to extract
            variables = ['Auditor', 'country', 'city', 'market_choice', 'Section',
                        'outlet_name', 'Outlet_code', 'outlet_owner', 'Contact', 
                        'participation', 'time_to_audit']

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

        except TypeError:
            print("Desired values not available")
        # except ET.ParseError:
        #     print("Problem with xml")
        else:
            return new_combined_df
# -----------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_supplier_profile(subj_id, survey_id, api_key, username, password):
        """
        Extract the values you need
        The parsed xml data is grouped into chapters. The target chapters list is used to select the desired chapters.
        The chapters are stored in a dataframe from which the necessary variables are selected.
        """
        try:
            backbone = DownloadDetails()
            response = backbone.download_xml(subj_id, survey_id, api_key, username, password)
            # print(response)
            data_list = backbone.xml_to_list(response)
            df = pd.DataFrame(data_list, columns=["Element", "Attribute", "Value"])
            df_items_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['Outlet_code', 'Source']

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

            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','Date'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                              'Date': dates[0] if dates else None,
                              'Upload': uploads[0] if uploads else None}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            transformed_dataframes.append(df_transformed)

            # Concatenate all transformed dataframes into a single dataframe
            df_pivoted = pd.concat(transformed_dataframes, ignore_index=True)
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['Date'] = df_pivoted['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
                       
            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)
        except TypeError:
            print("Desired values not available")
        else:
            return new_combined_df
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_extra_category(subj_id, survey_id, api_key, username, password):
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
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['Outlet_code', 'category_extra']

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

            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','Date'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                              'Date': dates[0] if dates else None,
                              'Upload': uploads[0] if uploads else None}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            transformed_dataframes.append(df_transformed)

            # Concatenate all transformed dataframes into a single dataframe
            df_pivoted = pd.concat(transformed_dataframes, ignore_index=True)
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['Date'] = df_pivoted['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
                       
            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)

            # Split up multiple-choice column rows
            new_combined_df['category_extra'] = new_combined_df['category_extra'].str.split(',')

            # Explode lists into multiple rows
            new_combined_df = new_combined_df.explode('category_extra').reset_index(drop=True)
        except TypeError:
            print("Desired values not available")
        # except ET.ParseError:
        #     print("Problem with xml")
        else:
            return new_combined_df
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_category(subj_id, survey_id, api_key, username, password):
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
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['Outlet_code', 'Category', 'segment_wet', 'segment_dry']

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

            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','Date'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                              'Date': dates[0] if dates else None,
                              'Upload': uploads[0] if uploads else None}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            transformed_dataframes.append(df_transformed)

            # Concatenate all transformed dataframes into a single dataframe
            df_pivoted = pd.concat(transformed_dataframes, ignore_index=True)
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['Date'] = df_pivoted['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
                       
            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)
            exploded_data = backbone.transform_categories_and_segments(new_combined_df)

            # Remove rows where BOTH segment_wet AND segment_dry are empty strings or NaN
            cleaned_df = exploded_data.loc[~((exploded_data['segment_wet'].fillna('') == '') & (exploded_data['segment_dry'].fillna('') == ''))].reset_index(drop=True)

        except TypeError:
            print("Desired values not available")
        # except ET.ParseError:
        #     print("Problem with xml")
        else:
            return cleaned_df
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_outlet_type(subj_id, survey_id, api_key, username, password):
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
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['Outlet_code', 'outlet_type', 'Salon', 'Retail']

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

            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','Date'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                              'Date': dates[0] if dates else None,
                              'Upload': uploads[0] if uploads else None}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            transformed_dataframes.append(df_transformed)

            # Concatenate all transformed dataframes into a single dataframe
            df_pivoted = pd.concat(transformed_dataframes, ignore_index=True)
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['Date'] = df_pivoted['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
                       
            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)
        except TypeError:
            print("Desired values not available")
        # except ET.ParseError:
        #     print("Problem with xml")
        else:
            return new_combined_df
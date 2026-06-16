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
# ------------------------------------------------------------------------------------------------------------------------------------------
class RecruitmentDownload:
    @staticmethod
    def transform_recruitment_items(subj_id, survey_id, api_key, username, password):
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
            df_items_use['Value'] = df_items_use['Value'].str.replace(r'I_\d+_', '', regex=True)

            # List of FullVariable values to extract
            variables = ['outlet_code', 'item_category', 'item_catid', 'item_barcode', 'item_name',
                'item_manufacturer', 'item_brand', 'item_pack_type', 'itemcode',
                'item_weight', 'item_unit', 'item_sales_duration', 'item_sales', 'item_price',
                'country_of_origin','item_observation']
            
            # Main logic to pick up needed parts
            all_items = []
            current_item = {}
            first_item = True  # Flag to handle first item specially

            for i in range(len(df_items_use)):
                row = df_items_use.iloc[i]
                
                if row['Element'] == 'FullVariable' and row['Value'] in variables:
                    var_name = row['Value']
                    
                    if i + 1 < len(df_items_use) and df_items_use.iloc[i + 1]['Element'] == 'QuestionAnswer':
                        var_value = df_items_use.iloc[i + 1]['Value']
                    else:
                        var_value = np.nan
                    
                    # If we hit a new item_category and it's not the first item, save the previous item
                    if var_name == 'item_category':
                        if not first_item:
                            all_items.append(current_item)
                            current_item = {}
                        else:
                            first_item = False
                    
                    # Add/update the variable in current item
                    current_item[var_name] = var_value

            # Append the last item after loop ends
            if current_item:
                all_items.append(current_item)

            # Convert list of dicts to DataFrame for easier analysis
            audit_items_df = pd.DataFrame(all_items)

            # Create a DataFrame from the extracted data
            #audit_items_df = pd.DataFrame([df_all_items])
            audit_items_df= audit_items_df.rename(columns={"scan":"item_barcode"})
            audit_items_df['item_name']= audit_items_df['item_name'].str.replace(r"\(.*\)", "", regex=True)
            audit_items_df['outlet_code'] = audit_items_df['outlet_code'].fillna(audit_items_df['outlet_code'].iloc[0]) # fill missing values in outlet code column


            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            # Initialize lists to store SubjectNum and Upload values
            subject_nums = []
            uploads = []

            # Iterate through the DataFrame, pairing SubjectNum and Upload values
            for i in range(0, len(df_result_extract), 2):
                subject_nums.append(df_result_extract['Value'][i] if i < len(df_result_extract) else None)
                uploads.append(df_result_extract['Value'][i+1] if i+1 < len(df_result_extract) else None)

            # Create the final DataFrame
            df_pivoted = pd.DataFrame({'SubjectNum': subject_nums, 'Upload': uploads})
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))

            # Combine dataframes and drop N/As
            df_pivoted = pd.concat([df_pivoted] * len(audit_items_df), ignore_index=True) # new dataframe to match size of audit_items_df
            new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)
            new_combined_df = new_combined_df[new_combined_df.item_category != "DONE"] # remove rows with category as done
        except KeyError:
            print("Desired values not available")
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
            df_items_use['Value'] = df_items_use['Value'].str.replace(r'I_\d+_', '', regex=True)

            # List of FullVariable values to extract
            variables = ['country_name', 'city', 'outlet_code', 'outlet_name', 'outlet_type',
                'outlet_type_code', 'owner_name', 'outlet_direction', 'landmark',
                'water_stock', 'soft_drink_presence',
                'soft_drink_count', 'contact', 'address','iterindex','shop_observation']

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
            pattern = r'Latitude:\s*(.*?)\s*\(.*?\)\n\s*Longitude:\s*(.*?)\s*\(.*?\)\n\s*Captured at:\s*(.*?)\n\s*Altitude:\s*(.*?)\n\s*Bearing:\s*(.*?)\s*\n\s*Speed:\s*(.*?)\s*km/h'
            audit_items_df[['GPS_Latitude', 'GPS_Longitude', 'GPS_Date', 'GPS_Altitude', 'GPS_Bearing', 'GPS_Speed (km/h)']] = audit_items_df['address'].str.extract(pattern, expand=True)
            audit_items_df.drop(columns=["address"], inplace=True) # Remove original GPS column
            audit_items_df= audit_items_df.rename(columns={"iterindex":"item_count"})

            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','VisitStart','VisitEnd','ClientDuration','Date','SurveyorName'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            surveyor_names = df_result_extract[df_result_extract['Element'] == 'SurveyorName']['Value'].tolist()
            durations = df_result_extract[df_result_extract['Element'] == 'ClientDuration']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()
            visit_starts = df_result_extract[df_result_extract['Element'] == 'VisitStart']['Value'].tolist()
            visit_ends = df_result_extract[df_result_extract['Element'] == 'VisitEnd']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                'Date': dates[0] if dates else None,
                'SurveyorName': surveyor_names[0] if surveyor_names else None,
                'NetDuration': durations[0] if durations else None,
                'Upload': uploads[0] if uploads else None,
                'VisitStart': visit_starts[0] if visit_starts else None,
                'VisitEnd': visit_ends[0] if visit_ends else None,}

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
            data_list = backbone.xml_to_list(response)
            df = pd.DataFrame(data_list, columns=["Element", "Attribute", "Value"])
            df_items_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)
            df_items_use['Value'] = df_items_use['Value'].str.replace(r'I_\d+_', '', regex=True)

            # List of FullVariable values to extract
            variables = ['outlet_code', 'country_name', 'city', 'outlet_name', 'outlet_type',
                'outlet_type_code', 'owner_name']

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
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','Date','SurveyorName'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            transformed_dataframes = []

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            surveyor_names = df_result_extract[df_result_extract['Element'] == 'SurveyorName']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                'Date': dates[0] if dates else None,
                'SurveyorName': surveyor_names[0] if surveyor_names else None,
                'Upload': uploads[0] if uploads else None,}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            transformed_dataframes.append(df_transformed)

            # Concatenate all transformed dataframes into a single dataframe
            df_pivoted = pd.concat(transformed_dataframes, ignore_index=True)
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            df_pivoted['Date'] = df_pivoted['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))

            # Your supplier list
            suppliers = ["Open Market/ Marché libre",
                "Bulk suppliers/ Fournisseurs en vrac",
                "Wholesalers/ Grossisters",
                "Manufacturers/ Fabricants",
                "Nearby retailers/ Détailants à proximité"]

            # Find the indices safely
            purch_idx_list = df.index[(df['Element'] == 'FullVariable') & (df['Value'] == 'purch_freq')].tolist()
            water_idx_list = df.index[(df['Element'] == 'FullVariable') & (df['Value'] == 'water_stock')].tolist()

            # If either index is missing, return empty DataFrame with supplier columns
            if not purch_idx_list or not water_idx_list:
                result_df = pd.DataFrame([{supplier: '' for supplier in suppliers}])
            else:
                start_idx = purch_idx_list[0]
                end_idx = water_idx_list[0]

                # Ensure correct order (start before end)
                if start_idx < end_idx:
                    result = df.iloc[start_idx:end_idx+1]
                else:
                    result = df.iloc[end_idx:start_idx+1]

                # Look for a TopicAnswer row with a comma-separated string
                topicanswer_rows = result[(result['Element'] == 'TopicAnswer')]
                answer_row = topicanswer_rows[topicanswer_rows['Value'].str.contains(',', na=False)]
                
                if not answer_row.empty:
                    # There is a comma-separated answer string
                    answer_string = answer_row.iloc[0]['Value']
                    answers = [x.strip() for x in answer_string.split(',')]
                    # Pad or trim to ensure exactly 5 answers
                    while len(answers) < len(suppliers):
                        answers.append('')
                    answers = answers[:len(suppliers)]
                    data = dict(zip(suppliers, answers))
                    result_df = pd.DataFrame([data])
                else:
                    # Fallback: Use row-based extraction as before
                    result_use = result.loc[(result['Element'] == 'TopicAnswer') | (result['Element'] == 'Text')]
                    supplier_rows = result_use[(result_use['Element'] == 'Text') & (result_use['Value'].isin(suppliers))]
                    supplier_freq = {}
                    for idx in supplier_rows.index:
                        slice_df = result_use.loc[idx+1:]
                        next_topicanswer = slice_df[slice_df['Element'] == 'TopicAnswer']
                        if not next_topicanswer.empty:
                            freq = next_topicanswer.iloc[0]['Value']
                            supplier_name = result_use.loc[idx, 'Value']
                            supplier_freq[supplier_name] = freq
                    data = {supplier: supplier_freq.get(supplier, '') for supplier in suppliers}
                    result_df = pd.DataFrame([data])

            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_pivoted, audit_items_df, result_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)

        except TypeError:
            print("Desired values not available")
        else:
            return new_combined_df

# ------------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------------------------
class AuditCaptureDetails:
    @staticmethod
    def transform_old_items(subj_id, survey_id, api_key, username, password):
        """
        This function creates and stores the data expected for new items in a dataframe.
        The variables that define new items are selected and manipulated in order to arrive
        at a desired dataframe format. Responses from the FullVariable, QuestionAnswer sections
        are selected.
        
        Arguments:
            subj_id (str)
            survey_id (str)
            api_key (str)
            username (str)
            password (str)
        
        Returns:
            df_items_store_details (pd.DataFrame)
        """
        try:
            backbone = DownloadDetails()
            response = backbone.download_xml(subj_id, survey_id, api_key, username, password)
            data_list = backbone.xml_to_list(response)
            df = pd.DataFrame(data_list, columns=["Element", "Attribute", "Value"])
            df_items_use = df.loc[(df['Element'] == 'Text') | (df['Element'] == 'TopicAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)

            # List of FullVariable values to extract
            variables = ['ITEM_NAME', 'ITEM_NO', 'BARCODE', 'CATEGORY', 'CATEGORY_CODE',
                'MANUFACTURER', 'BRAND_NAME', 'ITEM_CODE', 'ITEM_WEIGHT',
                'ITEM_UNIT', 'PACK_TYPE', 'SALES', 'SALES PRICE']

            # Main logic to pick up needed parts
            all_items = []
            current_item = {}
            first_item = True  # Flag to handle first item specially

            for i in range(len(df_items_use)):
                row = df_items_use.iloc[i]
                
                if row['Element'] == 'Text' and row['Value'] in variables:
                    var_name = row['Value']
                    
                    if i + 1 < len(df_items_use) and df_items_use.iloc[i + 1]['Element'] == 'TopicAnswer':
                        var_value = df_items_use.iloc[i + 1]['Value']
                    else:
                        var_value = np.nan
                    
                    # If we hit a new item_category and it's not the first item, save the previous item
                    if var_name == 'ITEM_NAME':
                        if not first_item:
                            all_items.append(current_item)
                            current_item = {}
                        else:
                            first_item = False
                    
                    # Add/update the variable in current item
                    current_item[var_name] = var_value

            # Append the last item after loop ends
            if current_item:
                all_items.append(current_item)

            # Convert list of dicts to DataFrame for easier analysis
            audit_items_df = pd.DataFrame(all_items)
            #audit_items_df

            ## -----------------------------------------------------------------------------------------------------------------
            df_items_use_2 = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_items_use_2 = df_items_use_2.reset_index(drop=True)#.drop(["Element"], axis=1)
            df_items_use_2['Value'] = df_items_use_2['Value'].str.replace(r'I_\d+_', '', regex=True)

            # List of FullVariable values to extract
            variables_2 = ['old_current_sales', 'old_current_price', 'outlet_code']

            # Main logic to pick up needed parts
            all_items_2 = []
            current_item_2 = {}
            first_item_2 = True  # Flag to handle first item specially

            for i in range(len(df_items_use_2)):
                row_2 = df_items_use_2.iloc[i]
                
                if row_2['Element'] == 'FullVariable' and row_2['Value'] in variables_2:
                    var_name_2 = row_2['Value']
                    
                    if i + 1 < len(df_items_use_2) and df_items_use_2.iloc[i + 1]['Element'] == 'QuestionAnswer':
                        var_value_2 = df_items_use_2.iloc[i + 1]['Value']
                    else:
                        var_value_2 = np.nan
                    
                    # If we hit a new item_category and it's not the first item, save the previous item
                    if var_name_2 == 'old_current_sales':
                        if not first_item_2:
                            all_items_2.append(current_item_2)
                            current_item_2 = {}
                        else:
                            first_item_2 = False
                    
                    # Add/update the variable in current item
                    current_item_2[var_name_2] = var_value_2

            # Append the last item after loop ends
            if current_item_2:
                all_items_2.append(current_item_2)

            # Convert list of dicts to DataFrame for easier analysis
            audit_items_df_2 = pd.DataFrame(all_items_2)
            audit_items_df_2['outlet_code'] = audit_items_df_2['outlet_code'].fillna(audit_items_df_2['outlet_code'].iloc[0]) # fill missing values in outlet code column

            ## ------------------------------------------------------------------------------------------------

            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            # Initialize lists to store SubjectNum and Upload values
            subject_nums = []
            uploads = []

            # Iterate through the DataFrame, pairing SubjectNum and Upload values
            for i in range(0, len(df_result_extract), 2):
                subject_nums.append(df_result_extract['Value'][i] if i < len(df_result_extract) else None)
                uploads.append(df_result_extract['Value'][i+1] if i+1 < len(df_result_extract) else None)

            # Create the final DataFrame
            df_pivoted = pd.DataFrame({'SubjectNum': subject_nums, 'Upload': uploads})
            df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))

            final_old_items = pd.concat([df_pivoted, audit_items_df,audit_items_df_2], axis=1)
            final_old_items['SubjectNum'] = final_old_items['SubjectNum'].fillna(final_old_items['SubjectNum'].iloc[0]) # fill missing values in outlet code column
            final_old_items['Upload'] = final_old_items['Upload'].fillna(final_old_items['Upload'].iloc[0]) # fill missing values in outlet code column

            # Re-order columns
            final_old_items = final_old_items.iloc[:,[0,1,13,2,3,4,5,6,7,8,9,10,11,12,14,15]]
                        
        except IndexError:
            print("Null")
        else:
            return final_old_items    
    
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_audit_capture_profile(subj_id, survey_id, api_key, username, password):
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
            variables = ['surveyor', 'outlet_name', 'outlet_code', 'address','prev_item_count','item_count']

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
            audit_profile_df = pd.DataFrame([extracted_data])

            # Splitting up GPS attributes into individual columns
            # Regex pattern to extract the desired fields
            pattern = r'Latitude:\s*(.*?)\s*\(.*?\)\n\s*Longitude:\s*(.*?)\s*\(.*?\)\n\s*Captured at:\s*(.*?)\n\s*Altitude:\s*(.*?)\n\s*Bearing:\s*(.*?)\s*\n\s*Speed:\s*(.*?)\s*km/h'
            audit_profile_df[['GPS_Latitude', 'GPS_Longitude', 'GPS_Date', 'GPS_Altitude', 'GPS_Bearing', 'GPS_Speed (km/h)']] = audit_profile_df['address'].str.extract(pattern, expand=True)
            audit_profile_df.drop(columns=["address"], inplace=True) # Remove original GPS column


            ## --------------------------------------------------------------------------------------------------
            result_use = df.loc[(df['Element'] == 'TopicAnswer') | (df['Element'] == 'Text')].reset_index()
            external_list_variables = ['Previous Date', 'Country', 'City', 'Outlet Type Description',\
                                    'Outlet Type Code', 'Name of owner', 'Landmark', 'Direction']

            # Initialize a dictionary to store extracted values
            second_data = {}

            # Iterate through the list of variables
            for variable in external_list_variables:
                # Find the index where 'Element' is 'Text' and 'Value' is the current variable
                new_indices = result_use.index[(result_use['Element'] == 'Text') & (result_use['Value'] == variable)]

                if not new_indices.empty:
                    new_index = new_indices[0]  # Get the first index if it exists
                    # Check if there is a next row
                    if new_index + 1 < len(result_use):
                        extracted_value_new = result_use.loc[new_index + 1, 'Value']
                    else:
                        extracted_value_new = float('nan')  # Assign NaN if there is no next row
                else:
                    extracted_value_new = None  # Assign None if the variable is not found

                # Assign the extracted value to the corresponding variable in the dictionary
                second_data[variable] = extracted_value_new

            # Create a DataFrame from the extracted data
            audit_profile_2 = pd.DataFrame([second_data])

            ## ----------------------------------------------------------------------------------------------
            # SubjectNum and Upload dataframes
            df_extract = df[df['Element'].isin(['SubjectNum','Upload','VisitStart','VisitEnd','ClientDuration','Date','SurveyorName'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
            df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

            # Extract lists of SubjectNum, Upload etc
            subject_nums = df_result_extract[df_result_extract['Element'] == 'SubjectNum']['Value'].tolist()
            dates = df_result_extract[df_result_extract['Element'] == 'Date']['Value'].tolist()
            surveyor_names = df_result_extract[df_result_extract['Element'] == 'SurveyorName']['Value'].tolist()
            durations = df_result_extract[df_result_extract['Element'] == 'ClientDuration']['Value'].tolist()
            uploads = df_result_extract[df_result_extract['Element'] == 'Upload']['Value'].tolist()
            visit_starts = df_result_extract[df_result_extract['Element'] == 'VisitStart']['Value'].tolist()
            visit_ends = df_result_extract[df_result_extract['Element'] == 'VisitEnd']['Value'].tolist()

            # Create a dictionary of the values, handling missing data
            extracted_data = {'SubjectNum': subject_nums[0] if subject_nums else None,
                'Date': dates[0] if dates else None,
                'SurveyorName': surveyor_names[0] if surveyor_names else None,
                'NetDuration': durations[0] if durations else None,
                'Upload': uploads[0] if uploads else None,
                'VisitStart': visit_starts[0] if visit_starts else None,
                'VisitEnd': visit_ends[0] if visit_ends else None,}

            # Create the transformed DataFrame
            df_transformed = pd.DataFrame([extracted_data])
            # Re-order columns
            df_transformed = df_transformed.iloc[:,[0,4,2,1,3,5,6]]

            # Combine dataframes and drop N/As
            new_combined_df = pd.concat([df_transformed, audit_profile_2, audit_profile_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)

            # Formatting dates
            new_combined_df['Upload'] = new_combined_df['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            new_combined_df['Date'] = new_combined_df['Date'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            new_combined_df['VisitStart'] = new_combined_df['VisitStart'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))
            new_combined_df['VisitEnd'] = new_combined_df['VisitEnd'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S') if (isinstance(x, str) and len(x)>0) else None)
            
        except KeyError:
            print("Too many missing columns")
        else:
            return new_combined_df
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_new_items(subj_id, survey_id, api_key, username, password):
            """
            Extract the values you need
            Load csv file into dataframe and then select responses in the FullVariable, QuestionAnswer sections
            Create a DataFrame from the extracted data
            """
            try:
                backbone = DownloadDetails()
                response = backbone.download_xml(subj_id, survey_id, api_key, username, password)
                data_list = backbone.xml_to_list(response)
                df = pd.DataFrame(data_list, columns=["Element", "Attribute", "Value"])
                df_items_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
                df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)
                df_items_use['Value'] = df_items_use['Value'].str.replace(r'I_\d+_', '', regex=True)

                # List of FullVariable values to extract
                variables = ['outlet_code', 'item_category', 'item_catid', 'item_barcode', 'item_name',
                    'item_manufacturer', 'item_brand', 'item_pack_type', 'itemcode',
                    'item_weight', 'item_unit', 'item_sales_duration', 'item_sales', 'item_price',
                    'country_of_origin','item_observation']

                # Main logic to pick up needed parts
                all_items = []
                current_item = {}
                first_item = True  # Flag to handle first item specially

                for i in range(len(df_items_use)):
                    row = df_items_use.iloc[i]
                    
                    if row['Element'] == 'FullVariable' and row['Value'] in variables:
                        var_name = row['Value']
                        
                        if i + 1 < len(df_items_use) and df_items_use.iloc[i + 1]['Element'] == 'QuestionAnswer':
                            var_value = df_items_use.iloc[i + 1]['Value']
                        else:
                            var_value = np.nan
                        
                        # If we hit a new item_category and it's not the first item, save the previous item
                        if var_name == 'item_category':
                            if not first_item:
                                all_items.append(current_item)
                                current_item = {}
                            else:
                                first_item = False
                        
                        # Add/update the variable in current item
                        current_item[var_name] = var_value

                # Append the last item after loop ends
                if current_item:
                    all_items.append(current_item)

                # Convert list of dicts to DataFrame for easier analysis
                audit_items_df = pd.DataFrame(all_items)

                # Create a DataFrame from the extracted data
                #audit_items_df = pd.DataFrame([df_all_items])
                audit_items_df= audit_items_df.rename(columns={"scan":"item_barcode"})
                audit_items_df['item_name']= audit_items_df['item_name'].str.replace(r"\(.*\)", "", regex=True)
                audit_items_df['outlet_code'] = audit_items_df['outlet_code'].fillna(audit_items_df['outlet_code'].iloc[0]) # fill missing values in outlet code column


                # SubjectNum and Upload dataframes
                df_extract = df[df['Element'].isin(['SubjectNum','Upload'])] # the loaded csv file has columns Element, Attribute and Value. In the element column, for items, we pick the listed variables of interest ie. fullvariable, questionanswer,...
                df_result_extract = df_extract[df_extract['Attribute'].isin(['text'])].reset_index(drop=True)[['Element','Value']] # picks selected data points with Attribute as 'Text' only, resets the index to start from 0 and then drops other columns leaving Element and Value

                # Initialize lists to store SubjectNum and Upload values
                subject_nums = []
                uploads = []

                # Iterate through the DataFrame, pairing SubjectNum and Upload values
                for i in range(0, len(df_result_extract), 2):
                    subject_nums.append(df_result_extract['Value'][i] if i < len(df_result_extract) else None)
                    uploads.append(df_result_extract['Value'][i+1] if i+1 < len(df_result_extract) else None)

                # Create the final DataFrame
                df_pivoted = pd.DataFrame({'SubjectNum': subject_nums, 'Upload': uploads})
                df_pivoted['Upload'] = df_pivoted['Upload'].apply(lambda x: datetime.strptime(re.sub('T|Z', '', x), '%Y-%m-%d%H:%M:%S'))

                # Combine dataframes and drop N/As
                df_pivoted = pd.concat([df_pivoted] * len(audit_items_df), ignore_index=True) # new dataframe to match size of audit_items_df
                new_combined_df = pd.concat([df_pivoted, audit_items_df], axis=1)
                new_combined_df = new_combined_df.dropna(how='all', axis=0)
                new_combined_df = new_combined_df[new_combined_df.item_category != "DONE"] # remove rows with category as done
            except KeyError:
                print("New item not found")
            else:
                return new_combined_df





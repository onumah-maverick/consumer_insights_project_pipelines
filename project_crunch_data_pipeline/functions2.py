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
    def transform_advert(subj_id, survey_id, api_key, username, password):
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
            #--------------------------------------------------------------------------------------------------------
            df_brand_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_brand_use = df_brand_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['first_ad_view', 'first_ad_brand', 'first_ad_impression','first_ad_extra_impression',
                         'second_ad_view', 'second_ad_brand', 'second_ad_impression', 'second_ad_extra_impression']

            # Initialize a dictionary to store extracted values
            extracted_data = {}

            # Iterate through the list of variables
            for variable in variables:
                # Find the index where 'Element' is 'FullVariable' and 'Value' is the current variable
                indices = df_brand_use.index[(df_brand_use['Element'] == 'FullVariable') & (df_brand_use['Value'] == variable)]

                if not indices.empty:
                    index = indices[0]  # Get the first index if it exists
                    # Check if there is a next row
                    if index + 1 < len(df_brand_use):
                        extracted_value = df_brand_use.loc[index + 1, 'Value']
                    else:
                        extracted_value = float('nan')  # Assign NaN if there is no next row
                else:
                    extracted_value = None  # Assign None if the variable is not found

                # Assign the extracted value to the corresponding variable in the dictionary
                extracted_data[variable] = extracted_value

            # Create a DataFrame from the extracted data
            advert_df = pd.DataFrame([extracted_data])
            #---------------------------------------------------------------------------------------------------
            df_items_use = df.loc[(df['Element'] == 'Text') | (df['Element'] == 'TopicAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)

            # List of FullVariable values to extract
            variables = ["You enjoyed watching it a lot", "It’s a bit difficult to understand",
                         "The points made were relevant to you", "The points made were believable",
                         "It made you more likely to consume the brand", "The advert made me love the brand",
                         "You enjoyed watching it a lot.", "It’s a bit difficult to understand.",
                         "The points made were relevant to you.", "The points made were believable.",
                         "It made you more likely to consume the brand.", "The advert made me love the brand.",
                        ]
            
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
                    if var_name == "You enjoyed watching it a lot":
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

            # Combine dataframes
            final_old_items = pd.concat([df_pivoted, advert_df, audit_items_df],axis=1)
            final_old_items['SubjectNum'] = final_old_items['SubjectNum'].fillna(final_old_items['SubjectNum'].iloc[0]) # fill missing values in outlet code column
            final_old_items['Upload'] = final_old_items['Upload'].fillna(final_old_items['Upload'].iloc[0]) # fill missing values in outlet code column

            # Explode dataframe
            exploded_data = backbone.explode_columns(final_old_items, ['first_ad_extra_impression', 'second_ad_extra_impression'], ".,")
            
        except ArithmeticError:
            print("Null")
        else:
            return exploded_data  


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
            #---------------------------------------------------------------------------------------------------------------------
            df_items_use = df.loc[(df['Element'] == 'FullVariable') | (df['Element'] == 'QuestionAnswer')]
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['surveyor', 'title', 'prenom', 'surname', 'phone_number',
                        'address', 'city', 'respondent_id', 'survey_agree', 'survey_no',
                        'occupation_conflict', 'age','age_range','gender','income',
                        'contact_back']

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
            #---------------------------------------------------------------------------------------------------------------------
            df_profile_extra = df.loc[(df['Element'] == 'Text') | (df['Element'] == 'TopicAnswer')]
            df_profile_extra = df_profile_extra.reset_index(drop=True)

            # List of FullVariable values to extract
            variables = ['Toothpaste', 'Biscuits/ Crackers/ Wafers', 'Food Seasoning',
                         'Coffee or Beverages', 'Drinking Yoghurt','Name confirm',
                         'Phone confirm']
            
            # Main logic to pick up needed parts
            all_items = []
            current_item = {}
            first_item = True  # Flag to handle first item specially

            for i in range(len(df_profile_extra)):
                row = df_profile_extra.iloc[i]
                
                if row['Element'] == 'Text' and row['Value'] in variables:
                    var_name = row['Value']
                    
                    if i + 1 < len(df_profile_extra) and df_profile_extra.iloc[i + 1]['Element'] == 'TopicAnswer':
                        var_value = df_profile_extra.iloc[i + 1]['Value']
                    else:
                        var_value = np.nan
                    
                    # If we hit a new item_category and it's not the first item, save the previous item
                    if var_name == 'Toothpaste':
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
            profile_df = pd.DataFrame(all_items)
            
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
            new_combined_df = pd.concat([df_pivoted, audit_items_df, profile_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)

        except ArithmeticError:
            print("Desired values not available")
        else:
            return new_combined_df
# -----------------------------------------------------------------------------------------------------------------------------------------
# Good Biscuit
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
            df_items_use = df_items_use.reset_index(drop=True)#.drop(["Element"], axis=1)

            # List of FullVariable values to extract
            variables = ['house_items', 'house_cook', 'house_toilet', 'house_water',
                         'education', 'residence_area', 'house_type', 'occupation',
                         'total_score', 'sec_score']

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

            # Explode dataframe
            exploded_data = backbone.explode_columns(new_combined_df, ['house_items', 'house_cook'], ",")

        except ArithmeticError:
            print("Desired values not available")
        else:
            return exploded_data
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_media_habits(subj_id, survey_id, api_key, username, password):
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
            variables = ['cable_channels']

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

            #---------------------------------------------------------------------------------------------------------------------
            df_profile_extra = df.loc[(df['Element'] == 'Text') | (df['Element'] == 'TopicAnswer')]
            df_profile_extra = df_profile_extra.reset_index(drop=True)

            # List of FullVariable values to extract
            variables = ['Watch TV','Listen to Radio', 'Access Internet/Websites/Social Media platform',
                        'Read Newspaper/ Read Magazine','TV 1', 'TV 2', 'TV 3', 'TV 4', 'TV 5', 'Radio 1',
                        'Radio 2', 'Radio 3', 'Radio 4', 'Radio 5', 'Platform 1', 'Platform 2', 'Platform 3',
                        'Platform 4', 'Platform 5']
            
            # Main logic to pick up needed parts
            all_items = []
            current_item = {}
            first_item = True  # Flag to handle first item specially

            for i in range(len(df_profile_extra)):
                row = df_profile_extra.iloc[i]
                
                if row['Element'] == 'Text' and row['Value'] in variables:
                    var_name = row['Value']
                    
                    if i + 1 < len(df_profile_extra) and df_profile_extra.iloc[i + 1]['Element'] == 'TopicAnswer':
                        var_value = df_profile_extra.iloc[i + 1]['Value']
                    else:
                        var_value = np.nan
                    
                    # If we hit a new item_category and it's not the first item, save the previous item
                    if var_name == 'Name confirm':
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
            profile_df = pd.DataFrame(all_items)
            #----------------------------------------------------------------------------------------------------------------------           

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
            new_combined_df = pd.concat([df_pivoted, profile_df, audit_items_df], axis=1)
            new_combined_df = new_combined_df.dropna(how='all', axis=0)

            # Explode dataframe
            exploded_data = backbone.explode_columns(new_combined_df, ['cable_channels'], ",")

        except ArithmeticError:
            print("Desired values not available")
        else:
            return exploded_data
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_brand_awareness(subj_id, survey_id, api_key, username, password):
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
            variables = ['biscuit_tom', 'biscuit_awareness', 'biscuit_extra_aware', 'biscuit_advertising',
                         'biscuit_consumed', 'biscuit_consumed_months','biscuit_consumed_days', 
                         'biscuit_consumed_often', 'biscuit_consumed_mcberry','biscuit_consumed_nutrisnax', 
                         'biscuit_consumed_perk', 'biscuit_consumed_royal', 'biscuit_consumed_yum']

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
            
            # Explode dataframe
            exploded_data = backbone.explode_columns(new_combined_df, ['biscuit_awareness', 'biscuit_extra_aware',\
                                                                       'biscuit_advertising', 'biscuit_consumed', 'biscuit_consumed_months',\
                                                                        'biscuit_consumed_days', 'biscuit_consumed_mcberry',\
                                                                        'biscuit_consumed_nutrisnax','biscuit_consumed_perk',\
                                                                        'biscuit_consumed_royal','biscuit_consumed_yum',], ",")
            
            iterator_list = ['biscuit_tom', 'biscuit_awareness', 'biscuit_extra_aware', 'biscuit_advertising', 'biscuit_consumed',\
            'biscuit_consumed_months', 'biscuit_consumed_days', 'biscuit_consumed_often', 'biscuit_consumed_mcberry',\
            'biscuit_consumed_nutrisnax', 'biscuit_consumed_perk', 'biscuit_consumed_royal', 'biscuit_consumed_yum']
    

            # Recursively populate database tables
            output_tables = {}

            for i, j in enumerate(iterator_list):
                print("=" * 50)
                print(f'Loading Data: {j} table')
                table_pivot = exploded_data.groupby('SubjectNum').agg(
                    Distinct_SubjectNum_Count=('SubjectNum', 'nunique'),
                    Product_List=(f'{j}', lambda x: ', '.join(x.dropna().unique().astype(str)))
                ).reset_index()

                output_tables[j] = table_pivot
        except TypeError:
            print("Desired values not available")
        except np._core._exceptions._ArrayMemoryError as e:
            print(f"MemoryError while processing")
        else:
            return output_tables
# ------------------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def transform_biscuit_overview(subj_id, survey_id, api_key, username, password):
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
            variables = ['biscuit_freq', 'biscuit_purchase','biscuit_influence', 
                         'biscuit_eat_change', 'biscuit_decrease_reason', 'biscuit_satisfy',]

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

            # Explode dataframe
            exploded_data = backbone.explode_columns(new_combined_df, ['biscuit_influence'], ",")

        except TypeError:
            print("Desired values not available")
        else:
            return exploded_data

# ------------------------------------------------------------------------------------------------------------------------------------------
# Good
    @staticmethod
    def transform_sku_filter(subj_id, survey_id, api_key, username, password):
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
            variables = ['NUTRISNAX NUTRI MORN OATS','NUTRISNAX CHOCO DIGESTIVE','NUTRISNAX TEA TIME',\
                         'PERK CHOCO FILLED COOKIES','PERK COCONUT COOKIES','PERK CHOCO BUTTER COOKIES',\
                         'PERK BUTTER COOKIES',\
                         'NUTRISNAX NUTRI MORN OATS.', 'NUTRISNAX CHOCO DIGESTIVE.', 'NUTRISNAX TEA TIME.',\
                         'PERK CHOCO BUTTER COOKIES.', 'PERK BUTTER COOKIES.', 'PERK CHOCO FILLED COOKIES.',\
                         'PERK COCONUT COOKIES.',
                        ]
            
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
                    if var_name == 'Toothpaste':
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

            final_old_items = pd.concat([df_pivoted, audit_items_df],axis=1)
            final_old_items['SubjectNum'] = final_old_items['SubjectNum'].fillna(final_old_items['SubjectNum'].iloc[0]) # fill missing values in outlet code column
            final_old_items['Upload'] = final_old_items['Upload'].fillna(final_old_items['Upload'].iloc[0]) # fill missing values in outlet code column
                        
        except IndexError:
            print("Null")
        else:
            return final_old_items    

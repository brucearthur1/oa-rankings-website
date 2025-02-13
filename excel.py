import os
import pandas as pd
import openpyxl
import xlrd
from database import get_sheets_from_event, store_events_from_excel, store_race_from_excel
from datetime import datetime, timezone
from pytz import timezone
import pandas as pd

def parse_result_from_df(df):
    # Assuming your DataFrame is named df
    partial_df = df.iloc[1:91, 1:5]

    # Additional check to prevent stats from being loaded as results. This can happen if rows have been deleted from the excel worksheet
    partial_df = partial_df.dropna(subset=[partial_df.columns[0]])
    parsed_rows = []

    for i in range(len(partial_df)):
        current_row = partial_df.iloc[i]
        if i > 0:
            previous_row = partial_df.iloc[i - 1]
            if current_row[partial_df.columns[0]] != previous_row[partial_df.columns[0]] + 1:
                break
        parsed_rows.append(current_row)

    # Convert the list of parsed rows to a DataFrame
    parsed_df = pd.DataFrame(parsed_rows, columns=partial_df.columns)
    # Drop rows that are empty in column 2 in the sliced DataFrame
    parsed_df = parsed_df.dropna(subset=[parsed_df.columns[2]])
    # Convert the DataFrame to a list of tuples for insertion into MySQL
    data_to_insert = [tuple(row) for row in parsed_df.to_numpy()]
    # Print the parsed DataFrame to verify the results
    print(parsed_df)

    return data_to_insert



def add_multiple_races_for_list_year(input):
    df_list = load_multiple_from_xlsx(input)
    # Slice the DataFrame to start from row 2 (index 1) and columns B to E (index 1 to 4) 
    for df in df_list:
        data_to_insert = parse_result_from_df(df[1])
        #store this in the DB
        store_race_from_excel(df[0]['short_file'], data_to_insert)
    return df_list
    

def import_events_from_excel(input):

    df = load_from_xls(input)
    print(f"DataFrame shape: {df.shape}")
    if int(input['start']) < 2:
        input['start'] = '2'
    # Slice the DataFrame to start from row start to finish and columns (index 0 to 9) 
    partial_df = df.iloc[int(input['start'])-2:int(input['finish'])-1, 0:10] 
    print(f"Partial DataFrame shape: {partial_df.shape}")

    # Drop the 6th and 7th columns (index 5 and 6)
    partial_df = partial_df.drop(partial_df.columns[[5, 6]], axis=1)
    print(f"Partial DataFrame shape after dropping columns: {partial_df.shape}")

    # Drop rows if all rows are empty in the sliced DataFrame 
    parsed_df = partial_df.dropna(how='all')
    print(f"Parsed DataFrame shape after dropna: {parsed_df.shape}")

    # Format the date column to DD/MM/YYYY 
    parsed_df['Date'] = parsed_df['Date'].dt.strftime('%Y-%m-%d')
    print(f"Parsed DataFrame after date formatting:\n{parsed_df}")

    # Convert the DataFrame to a list of tuples for insertion into MySQL 
    data_to_insert = [tuple(row) for row in parsed_df.to_numpy()]
    print(f"Data to insert (first 5 rows): {data_to_insert[:5]}")
    print(f"Total rows to insert: {len(data_to_insert)}")    #store this in the DB

    store_events_from_excel(data_to_insert)

    df_html = parsed_df.to_html()

    return df_html

def load_from_xls(form_data):
    # Define the file path and sheet name 
    file_path = form_data['path_file'] 
    sheet_name = form_data['sheet']
    print(file_path)
    print(sheet_name)
    # Read the data into a DataFrame 
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd') 
    
    # Read the data into a DataFrame 
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd') 
    
    # Replace NaN values with pd.NA using applymap and a lambda function    
    df = df.applymap(lambda x: pd.NA if pd.isna(x) else x)
    
    # Replace NaN values with None using applymap and a lambda function 
    parsed_df = df.where(pd.notnull(df), None)

    sydney_tz = timezone('Australia/Sydney')
    print(f'Finished loading data from Excel file: time={datetime.now(sydney_tz)}')
    print(parsed_df)
    return parsed_df


def load_from_xlsx(form_data):
    # Define the file path and sheet name 
    file_path = form_data['path_file'] 
    sheet_name = form_data['sheet']
    print(file_path)
    print(sheet_name)
    # Read the data into a DataFrame 
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl') 
    # Replace NaN values with None 
    parsed_df = df.where(pd.notnull(df), None)
    #parsed_df = df.applymap(lambda x: None if pd.isna(x) else x)
    print(parsed_df)
    return parsed_df


def load_multiple_from_xlsx(form_data):
    # Define the file path and sheet name 
    file_path = form_data['path_file'] 
    list = form_data['list']
    
    year = os.path.basename(os.path.dirname(file_path))
    print(year)  

    sheets = get_sheets_from_event(list, year)
    parsed_df_list = []
    for sheet_name in sheets:
        # Read the data into a DataFrame 
        if sheet_name['short_file'] != 'WRE':
            df = pd.read_excel(file_path, sheet_name=sheet_name['short_file'], engine='openpyxl') 
            # Replace NaN values with None 
            parsed_df_row = df.where(pd.notnull(df), None)
            row = [sheet_name, parsed_df_row]
            parsed_df_list.append(row)
        
    return parsed_df_list

import pandas as pd
import openpyxl
import xlrd

def load_from_xls(form_data):
    # Define the file path and sheet name 
    file_path = form_data['path_file'] 
    sheet_name = form_data['sheet']
    print(file_path)
    print(sheet_name)
    # Read the data into a DataFrame 
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='xlrd') 
    
    # Replace NaN values with None using fillna for the specific 'Eventor ID' column 
    df = df.where(pd.notnull(df), None)
    # Replace NaN values with None using applymap and a lambda function 
    parsed_df = df.map(lambda x: None if pd.isna(x) else x) 

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

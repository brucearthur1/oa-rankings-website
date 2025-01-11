import pandas as pd
import openpyxl
import xlrd

def load_race_from_excel(form_data):
    # Define the file path and sheet name 
    file_path = form_data['path_file'] 
    sheet_name = form_data['sheet']
    # Read the data into a DataFrame 
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl') 
    # Replace NaN values with None 
    parsed_df = df.where(pd.notnull(df), None)
    return parsed_df
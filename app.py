#!/usr/bin/env python
# coding: utf-8

# STREAMLIT MAIN ENGINE PERFORMANCE EVALUATION (HF DATA)-v2.0

# In[1]:


import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import time
import os
import datetime
import math
import random
from auth import load_authenticator
from logger import setup_logger


# In[2]:

# Page layout ## Page expands to full width
st.set_page_config(layout='wide')

# === Authentication ===
authenticator = load_authenticator()
name, auth_status, username = authenticator.login('Login', 'main')
logger = setup_logger()

if auth_status:
    # === Password Reset Check ===
    if authenticator.credentials["usernames"][username].get("password_reset", False):
        st.warning("🔒 You are required to reset your password.")
        if st.button("Change Password"):
            authenticator.reset_password(username)
            st.success("✅ Password updated. Please log in again.")
            st.stop()
    
    authenticator.logout('Logout', 'main')

    st.markdown("<h1 style='color: blue; font-size: 24px;'>MAIN ENGINE PERFORMANCE EVALUATION</h1>", unsafe_allow_html=True)

    # Inputs for ME performance
    mode = st.radio(
        "How do you want to provide Inputs for Evaluating Main Engine Performance?",
        ("Dataset", "Manual Inputs")
    )

    if mode == "Dataset":    #DATASET SECTION    
        # Sidebar - Upload live dataset
        with st.header('1. Upload your CSV data'):
            uploaded_file = st.file_uploader("Upload your Live data CSV file", type=["csv"])

        if uploaded_file is not None:
            # Read the uploaded file into a DataFrame
            df = pd.read_csv(uploaded_file)
        
            #df.rename(columns={'dataTime': 'Datetime'}, inplace=True)
        
            # Impute null values to 0
            df.fillna(0, inplace=True)
        
            # Ensure the DataFrame has a Datetime column
            if 'Datetime' not in df.columns:
                st.error("The dataset must contain a 'Datetime' column.")
            else:
                df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')
                if df['Datetime'].isna().any():
                    st.warning("Some rows have invalid Datetime values and will be excluded.")
                    df = df.dropna(subset=['Datetime'])
            
                # Display the date input widgets for selecting the date range
                st.markdown('**1. Select Datetime Range**')
                start_date = st.date_input('Start date', min(df['Datetime']))
                end_date = st.date_input('End date', max(df['Datetime']))

                if start_date > end_date:
                    st.error('Error: End date must fall after start date.')
                else:
                    # Filter the DataFrame based on the selected date range
                    df1 = df[(df['Datetime'] >= pd.to_datetime(start_date)) & (df['Datetime'] <= pd.to_datetime(end_date))]

                    if df1.empty:
                        st.write('Datetime not in range.')
                    else:
                        # Display the filtered DataFrame
                        st.markdown('**1.1. Glimpse of Live dataset**')
                        st.write(df1)                
                        
                        # VOYAGE INPUTS SECTION
                        st.markdown('**2. Voyage Inputs**')
                        #perf_date = st.date_input("Performance analysis Date")
                        vessel = st.text_input("Enter name of Vessel", value="VESSEL")
                        voy_from = st.text_input("Voyage from port", value="SINGAPORE")
                        voy_to = st.text_input("Voyage to port", value="DALIAN")
                        condition = st.selectbox("Select the Vessel Condition:", ["Ballast", "Laden", "Partly-Laden"])
                        engine = st.text_input("Enter Engine Type and Specs.", value="MAN B&W 6S60ME-C")
                        cmcr_power = st.number_input("Enter the Engine CMCR Power Value(KW): ", min_value=1.0, step=100.0)
                        cmcr_rpm = st.number_input("Enter the Engine CMCR RPM Value: ", min_value=1.0, step=5.0)
        
            
                        df1['Datetime'] = pd.to_datetime(df1['Datetime'])
                
                        #RUN MODEL ON UPLOADED DATA    
                        pi = 3.14159265359                            
        
                        # Wind force BF calculations-------------------------------------------                
                        # Convert AWD to radians (vectorized operation)
                        df1['AWD_R'] = np.radians(df1['AWD'])

                        # Calculate True Wind Speed (TWS)
                        df1['TWS'] = np.sqrt(
                            df1['SOG']**2 + df1['AWS']**2 - 2 * df1['SOG'] * df1['AWS'] * np.cos(df1['AWD_R'])
                        )                    
                        
                        def calculate_rwa(row):
                            try:
                                if (pd.notna(row['AWS']) != 0) or (pd.notna(row['SOG']) != 0) or (pd.notna(row['TWS']) != 0):
                                    numerator = row['AWS']**2 - row['TWS']**2 - row['SOG']**2
                                    denominator = 2 * row['TWS'] * row['SOG']    
        
                                    if denominator !=0:
                                        ratio = numerator / denominator               
                            
                                    # Ensure the ratio falls within the valid range for acos
                                    if -1 <= ratio <= 1:
                                        rwa = math.acos(ratio) * 180 / math.pi 
                                        return rwa
                                    else:
                                        return None  # Invalid input for acos
                                
                                else:
                                    return None  # Wind_Speed or Speed_over_ground is null or 0
                    
                            except Exception:
                                return None  # Return None in case of any exception
            
                        df1['RWA'] = df1.apply(calculate_rwa, axis=1)        

                        df1['RWA'] = df1.apply(lambda row:
                                            row['HEADING'] - row['RWA'] if row['HEADING'] > 180 and row['AWD'] > 180
                                            else row['HEADING'] - row['RWA'] + 360 if row['HEADING'] < 180 and row['AWD'] > 180
                                            else row['HEADING'] + row['RWA'] - 360 if row['HEADING'] > 180 and row['AWD'] < 180
                                            else row['HEADING'] + row['RWA'] , axis=1)
        
        
                        df1['TWD'] = df1.apply(lambda row:
                                            360 + row['RWA'] if row['RWA'] < 0
                                            else row['RWA'] -360 if row['RWA'] >=360
                                            else row['RWA'], axis=1)      
        
        
                        df1['TWA'] = df1.apply(lambda row:
                                            row['TWD'] - row['HEADING'] - 360 if (row['TWD'] - row['HEADING']) > 180
                                            else row['TWD'] - row['HEADING'] + 360 if (row['TWD'] - row['HEADING']) < -180
                                            else row['TWD'] - row['HEADING'], axis=1)
        
        
                        df1['Windforce_BF'] = df1['TWS'].apply(lambda x:
                                                            0 if x is not None and x < 1
                                                            else 1 if x is not None and x <= 3
                                                            else 2 if x is not None and x <= 6
                                                            else 3 if x is not None and x <= 10
                                                            else 4 if x is not None and x <= 16
                                                            else 5 if x is not None and x <= 21
                                                            else 6 if x is not None and x <= 27
                                                            else 7 if x is not None and x <= 33
                                                            else 8 if x is not None and x <= 40
                                                            else 9 if x is not None and x <= 47
                                                            else 10 if x is not None and x <= 55
                                                            else 11 if x is not None and x < 63
                                                            else 12 if x is not None and x >=63
                                                            else None)    
        
                    #-------------------------------------------------------------------------------------------------------------- 
                        df1['Current_Cal'] = df1['STW'] - df1['SOG']          
                        df1['Power%'] = round(df1['Power']/cmcr_power*100,2)
                        df1['speed%'] = round(df1['RPM']/cmcr_rpm*100,2)
                        df1['trim'] = df1['Draft_Aft'] - df1['Draft_Fwd']
                        # Design Data Collection--------------------------------------------------------------------------------------------

                        # Data for Line 8
                        line8_speed = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 103.2, 108]
                        line8_power = [0, 0.08638376, 0.691070079, 2.332361516, 5.528560631, 10.79796998, 18.65889213, 29.62962963,
                                44.22848504, 62.97376093, 86.38375985, 94.94480233, 108.8186589]

                        # Data for Line 7
                        line7_speed = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
                        line7_power = [0, 0.1, 0.8, 2.7, 6.4, 12.5, 21.6, 34.3, 51.2, 72.9, 100]

                        # Data for Line 5-1-13
                        line5113_speed = [0, 40, 60, 96, 100, 103.2]
                        line5113_power = [0, 20, 36, 96, 100, 110]

                        # Data for Line 6-2-13
                        line6213_speed = [0, 40, 60, 96, 103.2]
                        line6213_power = [0, 24, 40, 102.3, 110]

                        # Data for Line 4
                        line4_speed = [108, 108]
                        line4_power = [110, 0]

                        # Data for Line 13
                        line13_speed = [103.2, 108]
                        line13_power = [110, 110]

                        # Data for Line 3a
                        line3a_speed = [104, 104]
                        line3a_power = [110, 0]

                        # Data for Line 3
                        line3_speed = [0, 50, 90, 99, 100, 100, 100, 100, 100]
                        line3_power = [100, 100, 100, 100, 100, 99, 90, 50, 0]

                        # Data for Line 9
                        line9_speed = [100, 104, 106, 108]
                        line9_power = [100, 100, 100, 100]
        
                        #Plotting-------------------------------------------------------------------------------------------
                        #create the plot
                        fig = go.Figure()   

                        # Add all lines (similar to the original code)
                        fig.add_trace(go.Scatter(x=line8_speed, y=line8_power, mode='lines', name='LRM(5%)',
                                                line=dict(color='blue', width=2, dash='solid')))
                        fig.add_trace(go.Scatter(x=line7_speed, y=line7_power, mode='lines', name='Nom.Engine Characteristic',
                                                line=dict(color='green', width=2, dash='solid')))
                        fig.add_trace(go.Scatter(x=line5113_speed, y=line5113_power, mode='lines', name='Engine Operating Power Range',
                                                line=dict(color='orange', width=2, dash='solid')))
                        fig.add_trace(go.Scatter(x=line6213_speed, y=line6213_power, mode='lines', name='Overload Power Range-Torque limit',
                                                line=dict(color='red', width=2, dash='solid')))
                        fig.add_trace(go.Scatter(x=line4_speed, y=line4_power, mode='lines', name='Overspeed limit(106-108% CMCR Speed)',
                                                line=dict(color='red', width=2, dash='dot')))
                        fig.add_trace(go.Scatter(x=line13_speed, y=line13_power, mode='lines', name='Emergency Operation(110% of CMCR Power)',
                                                line=dict(color='purple', width=2, dash='dot')))
                        fig.add_trace(go.Scatter(x=line3a_speed, y=line3a_power, mode='lines', name='Max.Speed limit (104% CMCR Speed)',
                                                line=dict(color='brown', width=2, dash='dot')))
                        fig.add_trace(go.Scatter(x=line3_speed, y=line3_power, mode='lines', name='100% CMCR Power-100% CMCR Speed',
                                                line=dict(color='violet', width=2, dash='dot')))
                        fig.add_trace(go.Scatter(x=line9_speed, y=line9_power, mode='lines', name='Max. Power for Continuous Operation',
                                                line=dict(color='green', width=2, dash='dot')))
                        fig.add_trace(go.Scatter(x=df1['speed%'], y=df1['Power%'], mode='markers', name="Performance Data",
                                                marker=dict(color='#1F77B4', size=8, symbol='circle')
                                                ))                                       

                        # Combine the inputs into a single title string
                        title_text = (
                        f"ENGINE POWER LAYOUT DIAGRAM\n"
                        f"Vessel: {vessel}, Date: {start_date} to {end_date}, Condition: {condition}"
                        )
                    
                        # Update layout
                        fig.update_layout(
                        title=title_text,
                        xaxis_title="Speed%",
                        yaxis_title="Power%",
                        legend_title="Lines",
                        template="plotly_white",
                        autosize = True,
                        width = 1200,
                        height = 800
                            )

                        # Render the Plotly chart in Streamlit with full container width
                        st.plotly_chart(fig, use_container_width=True)                
                    
                        if st.button('Export DataFrame to CSV'):
                            # Get the Downloads folder path
                            downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

                            # Define the filename
                            file_name = "MAIN ENGINE PERFORMANCE.csv"

                            # Combine Downloads folder path and filename
                            file_path = os.path.join(downloads_folder, file_name)

                            # Save or export the file to the Downloads folder
                            df1.to_csv(file_path, index=False)

                            # Display a success message
                            st.success(f'DataFrame exported to CSV: {file_path}')
                        
                        #gauge plots---------------------------------------------------------------
                        # Combine the inputs into a single title string
                        st.write ("### AVERAGE KPIs")
                    
                        # Create columns to display multiple gauges with adjusted widths
                        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])  # Adjust the width proportions as needed   
                        
                        # Filter the DataFrame for the selected date range 
                        #df1 = df1[(df1.index.date >= start_date) & (df1.index.date <= end_date)]    
                        
                        if not df1.empty:
                            mean_windforce = df1['Windforce_BF'].mean()                     
                            mean_power = df1['Power%'].mean() 
                            mean_rpm = df1['speed%'].mean()  
                            mean_sog = df1['SOG'].mean()
                    
                            # Define a function to determine bar color based on the value
                            def get_gauge_properties_bf(mean_windforce):
                                if mean_windforce <= 3.0:
                                    return "green"  # In range
                                elif 3.0 < mean_windforce <=5.0:
                                    return "orange"        
                                else:
                                    return "red"    # Out of range   
        
                            color = get_gauge_properties_bf(mean_windforce)     

                            with col1:
                                BF = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=round(mean_windforce,1),
                                    title={'text': "Average Wind Force BF", 'font': {'size': 14}},  # Adjust title font size
                                    gauge={
                                        'axis': {'range': [0.0, 12.0], 'tickwidth': 1, 'tickcolor': "black"},  # Ensure tick marks are visible
                                        'bar': {'color': color}, 
                                        'borderwidth': 2, 
                                        'bordercolor': "gray", 
                                        'bgcolor': "white"  # Add a white background for better clarity
                                        }
                                    ))
                                BF.update_layout(
                                    width=300,  # Increase width for better visibility
                                    height=250,  # Increase height for better visibility
                                    margin=dict(t=50, b=30, l=30, r=30)  # Adjust margins for proper spacing
                                    )
                                st.plotly_chart(BF) 
                        
                            #----------------------
                            # Define a function to determine bar color based on the value
                            def get_gauge_properties_power(mean_power):
                                if mean_power <= 85.0:
                                    return "green"  # In range        
                                else:
                                    return "red"    # Out of range   
        
                            color = get_gauge_properties_power(mean_power)     

                            # Create a dial gauge for the mean actual value
                            with col2:
                                POWER = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=round(mean_power,2),
                                    title={'text': "Average Power% of CMCR", 'font': {'size': 14}},  # Adjust title font size for consistency
                                    gauge={
                                        'axis': {'range': [0, round(mean_power*1.2,2)], 'tickwidth': 1, 'tickcolor': "black"},  # Visible tick marks
                                        'bar': {'color': color},
                                        'borderwidth': 2,
                                        'bordercolor': "gray",
                                        'bgcolor': "white"  # White background for clarity
                                        }
                                    ))
                                POWER.update_layout(
                                    width=300,  # Increased width for better scale visibility
                                    height=250,  # Increased height for consistent layout
                                    margin=dict(t=50, b=30, l=30, r=30)  # Adjusted margins for spacing
                                    )
                                st.plotly_chart(POWER)
                        
                            #---------------------
                            # Define a function to determine bar color based on the value
                            def get_gauge_properties_rpm(mean_rpm):
                                if mean_rpm <= 85.0:
                                    return "green"  # In range        
                                else:
                                    return "red"    # Out of range   
        
                            color = get_gauge_properties_rpm(mean_rpm)     

                            # Create a dial gauge for the mean actual value
                            with col3:
                                RPM = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=round(mean_rpm,2),
                                    title={'text': "Average RPM% of CMCR", 'font': {'size': 14}},
                                    gauge={
                                        'axis': {'range': [0, round(mean_rpm * 1.2, 2)], 'tickwidth': 1, 'tickcolor': "black"},
                                        'bar': {'color': color},
                                        'borderwidth': 2,
                                        'bordercolor': "gray",
                                        'bgcolor': "white"
                                        }
                                    ))
                                RPM.update_layout(
                                    width=300,  # Adjust width
                                    height=250,  # Adjust height
                                    margin=dict(t=50, b=30, l=30, r=30),  # Add more margin space
                                    )
                                st.plotly_chart(RPM) 
                            #------------------------------
                            # Define a function to determine bar color based on the value
                            def get_gauge_properties_sog(mean_sog):
                                if mean_sog >= 12.0:
                                    return "green"  # In range        
                                else:
                                    return "red"    # Out of range   
        
                            color = get_gauge_properties_sog(mean_sog)     

                            # Create a dial gauge for the mean actual value
                            with col4:                    
                                SOG = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=round(mean_sog,2),
                                    title={'text': "Speed Over Ground(knots)", 'font': {'size': 14}},
                                    gauge={
                                        'axis': {'range': [0, round(mean_sog * 1.2, 2)], 'tickwidth': 1, 'tickcolor': "black"},
                                        'bar': {'color': color},
                                        'borderwidth': 2,
                                        'bordercolor': "gray",
                                        'bgcolor': "white"
                                        }
                                    ))
                                SOG.update_layout(
                                    width=300,  # Adjust width
                                    height=250,  # Adjust height
                                    margin=dict(t=50, b=30, l=30, r=30),  # Add more margin space
                                    )
                                st.plotly_chart(SOG)   
    #--------------------------------------------------------------------------------------------------------------------                            
    elif mode == "Manual Inputs": #Manual Inputs
        # Design Data Collection-------------------
        # Data for Line 8
        line8_speed = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 103.2, 108]
        line8_power = [0, 0.08638376, 0.691070079, 2.332361516, 5.528560631, 10.79796998, 18.65889213, 29.62962963,
                    44.22848504, 62.97376093, 86.38375985, 94.94480233, 108.8186589]

        # Data for Line 7
        line7_speed = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        line7_power = [0, 0.1, 0.8, 2.7, 6.4, 12.5, 21.6, 34.3, 51.2, 72.9, 100]

        # Data for Line 5-1-13
        line5113_speed = [0, 40, 60, 96, 100, 103.2]
        line5113_power = [0, 20, 36, 96, 100, 110]

        # Data for Line 6-2-13
        line6213_speed = [0, 40, 60, 96, 103.2]
        line6213_power = [0, 24, 40, 102.3, 110]

        # Data for Line 4
        line4_speed = [108, 108]
        line4_power = [110, 0]

        # Data for Line 13
        line13_speed = [103.2, 108]
        line13_power = [110, 110]

        # Data for Line 3a
        line3a_speed = [104, 104]
        line3a_power = [110, 0]

        # Data for Line 3
        line3_speed = [0, 50, 90, 99, 100, 100, 100, 100, 100]
        line3_power = [100, 100, 100, 100, 100, 99, 90, 50, 0]

        # Data for Line 9
        line9_speed = [100, 104, 106, 108]
        line9_power = [100, 100, 100, 100]

        #Test Data Collection--------------------------------------------------------------------------------------------
        #voyage inputs----------------
        perf_date = st.date_input("Performance analysis Date")
        vessel = st.text_input("Enter name of Vessel", value="VESSEL")
        voy_from = st.text_input("Voyage from port", value="SINGAPORE")
        voy_to = st.text_input("Voyage to port", value="DALIAN")
        #Weather and motion inputs--------------
        awd = st.number_input("Enter the Apparent Wind Direction(degrees): ", min_value=0.01, value= 120.2, 
                            max_value= 359.99, step=1.0)
        aws = st.number_input("Enter the Apparent Wind Speed(knots): ", min_value=1.0, value=26.7, step=5.0)
        heading = st.number_input("Enter the Heading(degrees): ", min_value=0.01, value=321.3, max_value=359.99, step=1.0)
        sog = st.number_input("Enter the Vessel Speed Over Ground(knots): ", min_value=1.0, value=12.41, step=0.5)
        stw = st.number_input("Enter the Vessel Speed Thru' Water(knots): ", min_value=1.0, value= 12.83, step=0.5)
        #Vessel Conditon Inputs------------------
        condition = st.selectbox("Select the Vessel Condition:", ["Ballast", "Laden", "Partly-Laden"])
        draft_f = st.number_input("Enter the Draft Forward(metres): ", min_value=1.0, value=11.2, step=1.0)
        draft_a = st.number_input("Enter the Draft Aft(metres): ", min_value=1.0, value=11.7, step=1.0)
        draft_mp = st.number_input("Enter the Draft Midship Port(metres): ", min_value=1.0, value= 11.5, step=1.0)
        draft_ms =st.number_input("Enter the Draft Midshaft Starboard(metres): ",min_value=1.0, value=11.5, step=1.0 )
        #Shop Test Data inputs(ship specific)----------------------------------------------
        engine = st.text_input("Enter Engine Type and Specs.", value="MAN B&W 6S60ME-C")
        cmcr_power = st.number_input("Enter the Engine CMCR Power Value(KW): ", min_value=1.0, value=8700.0, step=100.0)
        cmcr_rpm = st.number_input("Enter the Engine CMCR RPM Value: ", min_value=1.0, value=85.4, step=5.0)
        #Operating Test Data inputs----------------------------------------------------------
        manual_y = st.number_input("Enter the Current Engine Power Value(KW): ", min_value=1.0, step=50.0)
        manual_x = st.number_input("Enter the Current Engine RPM Value: ", min_value=1.0, step=5.0)
        #Calculations---------------------------------------------------------------------------------------------------
        manual_x = round(manual_x / cmcr_rpm*100,2)    #converting to % rpm
        manual_y = round(manual_y / cmcr_power*100,2)  #converting to % power

        #Current Calculations---------------------------
        current = stw - sog  # Example calculation

        #Draft Calculations----------------------------
        trim = draft_a - draft_f
        
        #Wind force BF calculations-----------------------
        # Convert to radians
        awd_in_radians = math.radians(awd)

        # Calculate True Wind Speed (TWS)
        tws = math.sqrt(sog**2 + aws**2 - 2 * sog * aws * math.cos(awd_in_radians))  #(Calculate True Wind Speed)

        # 1. Calculate RWA (Relative Wind Angle)
        if (aws != 0) or (sog != 0) or (tws != 0):
            numerator = aws**2 - tws**2 - sog**2
            denominator = 2 * tws * sog    
        
            if denominator !=0:
                ratio = numerator / denominator       
        
                # Ensure the ratio is within a valid range for acos
                if -1 <= ratio <= 1:
                    rwa = math.acos(ratio) * 180 / math.pi            
                else:
                    rwa = None  # Invalid input for acos
            else:
                rwa = None  # Avoid division by zero            
        else:
            rwa = None  # AWS, SOG and TWS are 0    

        # 2. Adjust RWA based on heading and AWS
        if rwa is not None:
            if heading > 180 and awd > 180:
                rwa = heading - rwa
            elif heading < 180 and awd > 180:
                rwa = heading - rwa + 360
            elif heading > 180 and awd < 180:
                rwa = heading + rwa - 360
            else:
                rwa = heading + rwa

        # 3. Calculate TWD (True Wind Direction)
        if rwa is not None:
            if rwa < 0:
                twd = 360 + rwa
            elif rwa >= 360:
                twd = rwa - 360
            else:
                twd = rwa
        else:
            twd = None

        # 4. Calculate TWA (True Wind Angle)
        if twd is not None:
            twa = twd - heading
            if twa > 180:
                twa = twa - 360
            elif twa < -180:
                twa = twa + 360
            twa = abs(twa)  # Ensure TWA is absolute
        else:
            twa = None

        # 5. Calculate Wind Force (Beaufort Scale)
        if tws is not None:
            if tws < 1:
                windforce_bf = 0
            elif tws <= 3:
                windforce_bf = 1
            elif tws <= 6:
                windforce_bf = 2
            elif tws <= 10:
                windforce_bf = 3
            elif tws <= 16:
                windforce_bf = 4
            elif tws <= 21:
                windforce_bf = 5
            elif tws <= 27:
                windforce_bf = 6
            elif tws <= 33:
                windforce_bf = 7
            elif tws <= 40:
                windforce_bf = 8
            elif tws <= 47:
                windforce_bf = 9
            elif tws <= 55:
                windforce_bf = 10
            elif tws < 63:
                windforce_bf = 11
            else:
                windforce_bf = 12
        else:
            windforce_bf = None
        
    #---------------------------------------------    
        # Evaluate True Wind Angle (TWA)----------------------------
        if twd is not None and heading is not None:
            twa = twd - heading
            # Normalize TWA to the range -180 to 180
            if twa > 180:
                twa = twa -360
            elif twa <= -180:
                twa = twa + 360
            else:
                twa = twa
        else:
            twa = None

        # Evaluate Wind Angle
        if twa is not None:
            if 0 >= twa >= -60:
                wind_angle = "HEAD PORT - OPPOSING"
            elif 0 <= twa <= 60:
                wind_angle = "HEAD STARBOARD - OPPOSING"
            elif -180 <= twa <= -120:
                wind_angle = "TAIL PORT - ASSISTING"
            elif 120 <= twa <= 180:
                wind_angle = "TAIL STARBOARD - ASSISTING"
            elif -120 <= twa <= -60:
                wind_angle = "BEAM PORT - DRIFTING"
            elif 60 <= twa <= 120:
                wind_angle = "BEAM STARBOARD - DRIFTING"
            else:
                wind_angle = "UNKNOWN"
        else:
            wind_angle = None    
        
        # Print Results-------------------------------------------
        st.write("### KPIs:")
        #--------
        if current > 0.0:
            st.write(f"<span style='color:red;'><strong>Current is Opposing Vessel Motion: {current:.2f} knots</strong></span>", 
                    unsafe_allow_html=True)
        
        elif current < 0.0:
            st.write(f"<span style='color:green;'><strong>Current is Assisting Vessel Motion: {current:.2f} knots</strong></span>", 
                    unsafe_allow_html=True)
        
        elif current == 0.0:
            st.write(f"<span style='color:blue;'><strong>No Currents are affecting Vessel Motion: {current:.2f}</strong></span>", 
                    unsafe_allow_html=True)
        #---------    
        if draft_a == 0.0 or draft_f == 0.0:
            st.markdown(f"<span style='color:red;'><strong>Error in Input data</strong></span>", unsafe_allow_html=True)
        elif trim > 0.0:
            st.markdown(f"<span style='color:green;'><strong>Vessel is down by Stern: {trim:.1f} metres</strong></span>", 
                        unsafe_allow_html=True)  
        elif trim < 0.0:
            st.markdown(f"<span style='color:red;'><strong>Vessel is down by Head: {trim:.1f} metres</strong></span>", 
                        unsafe_allow_html=True)
        elif trim == 0.0:
            st.markdown(f"<span style='color:green;'><strong>Vessel is on Even Keel: {trim:.1f} metres</strong></span>", 
                        unsafe_allow_html=True)  
        #------------    
        st.markdown(
            f"<span style='color:crimson;'><strong>Wind Angle: {wind_angle}</strong></span>" 
            if wind_angle is not None 
            else "<span style='color:red;'><strong>Wind Angle: Not Considered</strong></span>",
            unsafe_allow_html=True
        )  

        #------------------------------------------------------------------------------------------------------------
        # Create columns to display multiple gauges with adjusted widths
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])  # Adjust the width proportions as needed

        # Define a function to determine bar color based on the value
        def get_gauge_properties_bf(windforce_bf):
            if windforce_bf <= 3:
                return "green"  # In range
            elif 3 < windforce_bf <=5:
                return "orange"        
            else:
                return "red"    # Out of range   
        
        color = get_gauge_properties_bf(windforce_bf)     

        with col1:
            BF = go.Figure(go.Indicator(
                mode="gauge+number",
                value=windforce_bf,
                title={'text': "Wind Force BF", 'font': {'size': 14}},  # Adjust title font size
                gauge={
                    'axis': {'range': [0, 12], 'tickwidth': 1, 'tickcolor': "black"},  # Ensure tick marks are visible
                    'bar': {'color': color}, 
                    'borderwidth': 2, 
                    'bordercolor': "gray", 
                    'bgcolor': "white"  # Add a white background for better clarity
                }
            ))
            BF.update_layout(
                width=300,  # Increase width for better visibility
                height=250,  # Increase height for better visibility
                margin=dict(t=50, b=30, l=30, r=30)  # Adjust margins for proper spacing
            )
            st.plotly_chart(BF)
        #-------------------        
        # Define a function to determine bar color based on the value
        def get_gauge_properties_tws(tws):
            if tws <= 16.0:
                return "green"  # In range
            elif 16 <tws <= 21:
                return "orange"        
            else:
                return "red"    # Out of range   
        
        color = get_gauge_properties_tws(tws)     

        with col2:
            TWS = go.Figure(go.Indicator(
                mode="gauge+number",
                value=round(tws,2),
                title={'text': "True Wind Speed(knots)", 'font': {'size': 14}},  # Adjusted title font size
                gauge={
                    'axis': {'range': [0, round(tws * 1.2, 2)], 'tickwidth': 1, 'tickcolor': "black"},  # Ensure tick marks are visible
                    'bar': {'color': color},
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'bgcolor': "white"  # Add white background for better clarity
                }
            ))
            TWS.update_layout(
                width=300,  # Increased width for better visibility
                height=250,  # Increased height for better visibility
                margin=dict(t=50, b=30, l=30, r=30)  # Adjusted margins for proper spacing
            )
            st.plotly_chart(TWS)      
        #--------------------------
        # Define a function to determine bar color based on the value
        def get_gauge_properties_twd(twd):
            if twd <= 180.0:
                return "green"  # In range        
            else:
                return "teal"    # Out of range   
        
        color = get_gauge_properties_twd(twd)     

        # Create a dial gauge for the mean actual value
        with col3:
            TWD = go.Figure(go.Indicator(
                mode="gauge+number",
                value=round(twd,2),
                title={'text': "True Wind Direction(°)", 'font': {'size': 14}},  # Adjust title font size for consistency
                gauge={
                    'axis': {'range': [0, min(twd*1.2, 360)], 'tickwidth': 1, 'tickcolor': "black"},  # Visible tick marks
                    'bar': {'color': color},
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'bgcolor': "white"  # White background for clarity
                }
            ))
            TWD.update_layout(
                width=300,  # Increased width for better scale visibility
                height=250,  # Increased height for consistent layout
                margin=dict(t=50, b=30, l=30, r=30)  # Adjusted margins for spacing
            )
            st.plotly_chart(TWD)
        #--------------------------------------    
        # Define a function to determine bar color based on the value
        def get_gauge_properties_sog(sog):
            if sog >= 12.0:
                return "green"  # In range
            
            else:
                return "red"    # Out of range   
        
        color = get_gauge_properties_sog(sog)     

        # Create a dial gauge for the mean actual value
        with col4:
            SOG = go.Figure(go.Indicator(
                mode="gauge+number",
                value=round(sog,2),
                title={'text': "Speed Over Ground(knots)", 'font': {'size': 14}},
                gauge={
                    'axis': {'range': [0, round(sog * 1.2, 2)], 'tickwidth': 1, 'tickcolor': "black"},
                    'bar': {'color': color},
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'bgcolor': "white"
                }
            ))
            SOG.update_layout(
                width=300,  # Adjust width
                height=250,  # Adjust height
                margin=dict(t=50, b=30, l=30, r=30),  # Add more margin space
            )
            st.plotly_chart(SOG)  
        #Plotting--------------------------------------------------------------------------------------------------------------
        #create the plot
        fig = go.Figure()   

        # Add all lines (similar to the original code)
        fig.add_trace(go.Scatter(x=line8_speed, y=line8_power, mode='lines', name='LRM(5%)',
                                line=dict(color='blue', width=2, dash='solid')))
        fig.add_trace(go.Scatter(x=line7_speed, y=line7_power, mode='lines', name='Nom.Engine Characteristic',
                                line=dict(color='green', width=2, dash='solid')))
        fig.add_trace(go.Scatter(x=line5113_speed, y=line5113_power, mode='lines', name='Engine Operating Power Range',
                                line=dict(color='orange', width=2, dash='solid')))
        fig.add_trace(go.Scatter(x=line6213_speed, y=line6213_power, mode='lines', name='Overload Power Range-Torque limit',
                                line=dict(color='red', width=2, dash='solid')))
        fig.add_trace(go.Scatter(x=line4_speed, y=line4_power, mode='lines', name='Overspeed limit(106-108% CMCR Speed)',
                                line=dict(color='red', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=line13_speed, y=line13_power, mode='lines', name='Emergency Operation(110% of CMCR Power)',
                                line=dict(color='purple', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=line3a_speed, y=line3a_power, mode='lines', name='Max.Speed limit (104% CMCR Speed)',
                                line=dict(color='brown', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=line3_speed, y=line3_power, mode='lines', name='100% CMCR Power-100% CMCR Speed',
                                line=dict(color='violet', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=line9_speed, y=line9_power, mode='lines', name='Max. Power for Continuous Operation',
                                line=dict(color='green', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=[manual_x], y=[manual_y], mode='markers+text', name="Current Value", 
                                marker=dict(color='#28A745',size=12, symbol='circle'), text=["Current Point"],
                                textposition="top center"))

        # Combine the inputs into a single title string
        title_text = (
            f"ENGINE POWER LAYOUT DIAGRAM\n"
            f"Date: {perf_date}, Vessel: {vessel}, Voyage: {voy_from} to {voy_to}, Condition: {condition}"
        )

        # Update layout
        fig.update_layout(
            title=title_text,
            xaxis_title="Speed%",
            yaxis_title="Power%",
            legend_title="Lines",
            template="plotly_white",
            autosize = True,
            width = 1200,
            height = 800
        )

        # Render the Plotly chart in Streamlit with full container width
        st.plotly_chart(fig, use_container_width=True)

        # ---- Download Inputs, Results and Plot as Image ---------------------------------------------------------------
        # Prepare the data for download (manual inputs + calculated results)
        data = {
            'Performance Date': [perf_date],
            'Voyage From': [voy_from],
            'Voyage To': [voy_to],    
            'App.Wind Direction': [awd],
            'App.Wind Speed': [aws],
            'heading': [heading],    
            'SOG (Speed Over Ground)': [sog],
            'STW (Speed Through Water)': [stw],     
            'Draft F': [draft_f],
            'Draft A': [draft_a],
            'Draft Mid-Port': [draft_mp],
            "Draft Mid-Starboard": [draft_ms],
            "CMCR Power(KW)": [cmcr_power],
            "CMCR RPM": [cmcr_rpm],
            "Test Power(KW)%": [manual_y],
            "Test RPM%": [manual_x],
            'Current knots': [current],
            'Windforce (Beaufort Scale)': [windforce_bf],
            'Trim (Head or Stern)': [trim],
        }

        # Create a DataFrame
        df_results = pd.DataFrame(data)

        # Convert DataFrame to CSV for download
        csv_results = df_results.to_csv(index=False)

        # Provide a download button for the CSV
        st.download_button(
            label="Download Manual Inputs and Results as CSV",
            data=csv_results,
            file_name="Manual_Inputs_Results.csv",
            mime="text/csv"
        )    

        # Save the plot image
        fig.write_image("engine_power_layout_diagram.png")  # Save the plot as a PNG file

        # Provide the download button for the plot image
        with open("engine_power_layout_diagram.png", "rb") as file:
            st.download_button(
                label="Download Plot as Image",
                data=file,
                file_name="engine_power_layout_diagram.png",
                mime="image/png"
            )

elif auth_status == False:
    st.error("Username/password is incorrect ❌")

elif auth_status == None:
    st.warning("Please enter your username and password 🔐")

    # In[ ]:





    # In[ ]:





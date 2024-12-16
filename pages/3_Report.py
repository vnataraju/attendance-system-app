import streamlit as st 
from Home import face_rec
import pandas as pd

st.set_page_config(page_title='Reporting',layout='wide')
st.subheader('Reporting')


# Retrive logs data and show in Report.py
# extract data from redis list
name = 'attendance:logs'
def load_logs(name,end=-1):
    logs_list = face_rec.r.lrange(name,start=0,end=end) # extract all data from the redis database
    return logs_list

# tabs to show the info
tab1, tab2, tab3 = st.tabs(['Registered Data','Logs', 'Attendance Report'])

with tab1:
    if st.button('Refresh Data'):
        # Retrive the data from Redis Database
        with st.spinner('Retriving Data from Redis DB ...'):    
            redis_face_db = face_rec.retrive_data(name='academy:register')
            st.dataframe(redis_face_db[['Name','Role']])

with tab2:
    if st.button('Refresh Logs'):
        st.write(load_logs(name=name))

with tab3:
    st.subheader('Attendance Reprot')

    # Load logs in to attribute list
    logs_list = load_logs(name=name)

    # step-1:  Convert the logs from list of bytes to list of strings
    convert_byte_to_string = lambda x: x.decode('utf-8')
    logs_list_string = list(map(convert_byte_to_string, logs_list))

    #st.write(logs_list_string)

    split_string = lambda x: x.split('@')
    logs_nested_list = list(map(split_string, logs_list_string))
    #st.write(logs_nested_list)

    #convert nested list into dataframe
    logs_df = pd.DataFrame(logs_nested_list, columns=['Name', 'Role', 'Timestamp'])
    #st.write(logs_df)

    # Step-3: Timestamp analysis or report
    logs_df['Timestamp'] = pd.to_datetime(logs_df['Timestamp'])
    logs_df['Date'] = logs_df['Timestamp'].dt.date

    #st.dataframe(logs_df)

    # Step- 3.1: Calculate In-time and outtime
    # In time: At which person is first detected in that day (min time stamp of the date)
    # Out time: At which person is last detected in that day (Max timestamp of the date)

    report_df = logs_df.groupby(by=['Date','Name','Role']).agg(
        In_time = pd.NamedAgg('Timestamp', 'min'),  # in time
        Out_time = pd.NamedAgg('Timestamp', 'max'),  # out time
    ).reset_index()

    report_df['In_time'] = pd.to_datetime(report_df['In_time'])
    report_df['Out_time'] = pd.to_datetime(report_df['Out_time'])

    report_df['Duration'] = report_df['Out_time'] - report_df['In_time']

    # st.dataframe(report_df)

    # Step-4: Marking person is present or absent
    all_dates = report_df['Date'].unique()
    name_role = report_df[['Name','Role']]. drop_duplicates().values.tolist()

    date_name_rol_zip = []
    for dt in all_dates:
        for name, role in name_role:
            date_name_rol_zip.append([dt, name, role])

    date_name_rol_zip_df = pd.DataFrame(date_name_rol_zip, columns=['Date', 'Name', 'Role'])
    # left join with report_df

    date_name_rol_zip_df = pd.merge(date_name_rol_zip_df, report_df, how='left', on=['Date', 'Name', 'Role'])

    # Duration
    # Hours
    date_name_rol_zip_df['Duration_seconds'] = date_name_rol_zip_df['Duration'].dt.seconds
    date_name_rol_zip_df['Duration_hours'] = date_name_rol_zip_df['Duration_seconds'] / (60*60)

    #st.write(date_name_rol_zip_df)

    def status_marker(x):

        if pd.Series(x).isnull().all():
            return 'Absent'
        elif x >0 and x < 1:
            return 'Absent(Less than 1 hr)'
        elif x >= 0 and x < 4:
            return 'Half Day (less than 4 hours)'
        elif x >=4 and x < 6:
            return 'Half Day'
        elif x >= 6:
            return 'Present'
        
    date_name_rol_zip_df['Status'] = date_name_rol_zip_df['Duration_hours'].apply(status_marker)

    st.dataframe(date_name_rol_zip_df)
        
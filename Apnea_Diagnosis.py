import base64
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
import pickle
import plotly.graph_objs as go
import streamlit as st

from scripts import plot
from scripts.util import extract_features

def load_model():
    with open('resources/model_logreg.pkl', 'rb') as f:
        res = pickle.load(f)
    with open('features/feature_selection.pkl', 'rb') as f:
        feature_col = pickle.load(f)
    return res['mdl'], res['scaler'], feature_col


def load_sample_features(test_file):
    test_df = pd.read_csv('features/' + test_file + '.csv')
    test_df.drop(['apn', 'group', 'file'], axis=1, inplace=True)
    return test_df


def apnea_diagnose(y_pred):
    # Total minute
    apnea_total = sum(y_pred)

    # Hourly AI 
    total_hour = int(len(y_pred) / 60)
    y_pred_hourly = np.reshape(y_pred[ : total_hour * 60], (total_hour, 60))
    AI_hourly = y_pred_hourly.sum(axis=1)
    y_pred_left = y_pred[420 : ]
    if len(y_pred_left) >= 30:
        AI_hourly = np.append(AI_hourly, sum(y_pred_left) * 60 / len(y_pred_left))
        total_hour += 1
    AI_max = AI_hourly.max()
    return AI_max, apnea_total


def check_data(data):
    duration = (data[-1] - data[0]) / 60
    if duration > 12 or duration < 4:
        st.warning(
            'A typical recording of heart rate should be around 8 hours. ' +\
            'Please make sure the heart rate data is in minutes.')
        return False
    return True


mdl, scaler, feature_col = load_model()
show_result = False

st.title('Sleep Apnea Evaluation')
st.markdown(
    '''
    <font size="4">[Sleep Apnea](https://en.wikipedia.org/wiki/Sleep_apnea)
    affects more than 18 million Americans. It causes hypertension, heart disease and 
    memory problems in the long term. <br /><br />Before spending $2,000 and a whole night 
    for a sleep study, you can try this app, which detects Sleep Apnea with over 80% 
    accuracy just based on your heart rate during the sleep! <br /><br />
    Curious about how the machine learning model works? Check out [here]
    (https://docs.google.com/presentation/d/1WwZyvJ4VLjRcUPeKftsnVOTlXbZ1NYcIuLxvsKsN9ew/edit?usp=sharing)!<br />
    _(Self-evaluation only. Please confirm with your health care provider)_</font>
    ''',
    unsafe_allow_html=True)

st.header('Upload your heart rate data')
from_sample = st.checkbox('Just show me some samples')
a = st.empty() # Place holder to be either file uploader or selectbox

if from_sample:
    options = ('Select one', 'Sample 1', 'Sample 2', 'Sample 3')
    option = a.selectbox('', options)
    if option != 'Select one':
        dict_data = {'Sample 1': 'c18', 'Sample 2': 'b09', 'Sample 3': 'a12'}
        # Load features
        features_df = load_sample_features(dict_data[option])
        # Load heart rate data
        with open(f'HR_data/{dict_data[option]}.pkl', 'rb') as f:
            hr_data = pickle.load(f)
        show_result = True

else:
    uploaded_file = a.file_uploader(
        'format requirement: time of each heart beat in minutes, ' +\
        'starting from 0, single column csv file', type='csv')
    if uploaded_file is not None:
        t_hr = np.loadtxt(uploaded_file)
        show_result = check_data(t_hr)
        if show_result:
            with st.spinner('Extracting features...'):
                hr = 1 / (np.diff(t_hr * 60))
                t_hr = t_hr[1: ]
                hr_data = {'t': t_hr, 'hr': hr}
                features_df = extract_features(hr_data)

if show_result:
    # Make prediction
    y_pred = mdl.predict(scaler.transform(features_df[feature_col]))
    AI_max, apnea_total = apnea_diagnose(y_pred)

    st.header('')
    st.header('Minute-wise evaluation')
    st.markdown('''
        <font size="4">Apnea is first evluated for each minute based on the heart rate.</font>
        ''', unsafe_allow_html=True)
    st.plotly_chart(plot.plot_hr(hr_data['t'], hr_data['hr'], y_pred))

    st.header('')
    st.header('Severity diagnosis')
    st.markdown('''
        <font size="4">The severity is determined by: <br />1) the highest Apnea Index (apnea minutes per hour), and 
        <br />2) total minutes of apnea during the sleep.</font>
        ''', unsafe_allow_html=True)
    st.plotly_chart(plot.plot_apnea_diagnosis(AI_max, apnea_total, y_pred), config={'displayModeBar': False})
    st.plotly_chart(plot.plot_diagnosis_result(AI_max, apnea_total), config={'displayModeBar': False})

    st.markdown('<font size="4"></font>',
         unsafe_allow_html=True)
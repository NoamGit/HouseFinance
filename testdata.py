from datetime import datetime

from currency_converter import CurrencyConverter
from numpy import argwhere
from sqlalchemy.sql.functions import user

from app import db
from app.models import User,Purchase
import pandas as pd
import os
from os.path import join as pjoin
import currency

basedir = os.path.abspath(os.path.dirname(__file__))
datadir = pjoin(os.path.dirname(basedir),'sample_data')
files = os.listdir(datadir,)
c = CurrencyConverter()
USD2ILS = c.convert(1, 'USD', 'ILS')

Purchase.query.delete()
db.session.commit()

for filename in files:
    df = pd.read_excel(pjoin(datadir,filename))
    user_name = 'noam' if df.loc[0].values[0] == 'כהן נעם' else 'eden'
    charge_date = df.iloc[1,2]

    df = df.iloc[2:,:-1]
    israel_placeholder = argwhere(df.iloc[:,0] == 'עסקאות בארץ')[0][0]
    abroad_placeholder = argwhere(df.iloc[:,0] == 'עסקאות בחו˝ל')[0][0]
    df_isr_colname = df.iloc[israel_placeholder+1].values
    df_abroad_colname = df.iloc[abroad_placeholder+1].values
    old_colname = df.columns.values
    translate_dict = {'תאריך רכישה' : 'purchase_date'
        , 'תאריך חיוב': 'billing_date'
        , 'סכום עסקה': 'price'
        , 'מספר שובר': 'purchase_id'
        , 'פירוט נוסף': 'other_details'
        , 'שם בית עסק': 'business_name'
        , 'סכום מקורי': 'price'
        , 'מטבע מקור': 'currency'
        , 'סכום חיוב': 'payment_price'
        , 'מטבע לחיוב': 'payment_currency'}
    new_abroad_colname = dict(zip(old_colname, [translate_dict[x] for x in list(df_abroad_colname)]))
    new_isr_colname = dict(zip(old_colname, [translate_dict[x] for x in list(df_isr_colname)]))

    df_israel_purchase = df.iloc[israel_placeholder+2:abroad_placeholder-1,:]
    df_abroad_purchase = df.iloc[abroad_placeholder+2:-2,:]
    df_israel_purchase.rename(columns=new_isr_colname,inplace=True)
    df_abroad_purchase.rename(columns=new_abroad_colname, inplace=True)

    existing_users = db.session.query(User.username).all()
    sqlalchemy_to_str = lambda x: str(list(x)[0])
    if user_name not in [sqlalchemy_to_str(x) for x in existing_users]:
        u = User(username=user_name)
        db.session.add(u)
        db.session.commit()
    else:
        u = User.query.filter_by(username=user_name).all()[0]

    # for Israeli purchases
    for k, row in df_israel_purchase.iterrows():
        p = Purchase(business_name=row['business_name']
                     , date= datetime.strptime(row['purchase_date'],"%d/%m/%Y").date()
                     , price = float(row['price'])
                     , payment_price = float(row['payment_price'])
                     , buyer=u)
        db.session.merge(p)
        db.session.commit()

    # for purchases from the US
    for k, row in df_abroad_purchase.iterrows():
        p = Purchase(business_name=row['business_name']
                     , date=datetime.strptime(row['purchase_date'], "%d/%m/%Y").date()
                     , price=float(row['price']) * USD2ILS
                     , payment_price=float(row['payment_price']) * USD2ILS
                     , buyer=u)
        db.session.merge(p)
        db.session.commit()
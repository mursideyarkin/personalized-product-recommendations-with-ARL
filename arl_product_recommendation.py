######################################################################
# PERSONALIZED PRODUCT RECOMMENDATIONS WITH ASSOCIATION RULE LEARNING
######################################################################

# PROJEDE ELE ALINAN KONULAR:

# RFM metriklerini hesaplama
# CLTV hesaplama
# Müşteri segmentasyonu
# ARL yöntemi ile ürün önerme

# PROJE ADIMLARI:

# 1. Veri setinin yüklenmesi
# 2. CRM_DATA_PREP fonksiyonu ile veri ön işleme yapılması
# 3. CREATE_CLTV_P fonksiyonu ile predictive CLTV dğerlerine göre (6 aylık) segmentlerinin oluşturulması (A/B/C)
# 4. Her bir segmente ait kullanıcı id'lerine göre veri setini oluşturma
# 5. Her bir segment için birliktelik kurallarının üretilmesi
# 6. Alman müşterilere (segmentlerine göre) ürün önerilmesi

#########################################################
# STEP 1: IMPORT DATA SETS AND LIBRARIES
#########################################################

#
import datetime as dt
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from lifetimes import BetaGeoFitter
from lifetimes import GammaGammaFitter
from mlxtend.frequent_patterns import apriori, association_rules

pd.set_option('display.float_format', lambda x: '%.3f' % x)
pd.set_option('display.max_columns', None)

# Veriyi external dosyadan okuma
df_ = pd.read_excel("4th_week/homeworks/online_retail_II.xlsx",
                    sheet_name="Year 2010-2011")
df = df_.copy()

from helpers.helpers import check_df
check_df(df)

######################################
# STEP 2: DATA PREPROSSING WITH PREDEFINED FUNCTIONS
######################################

from helpers.helpers import crm_data_prep
df_prep = crm_data_prep(df)
df_prep.head()

from helpers.helpers import check_df
check_df(df_prep)

######################################
# Görev 3: create_cltv_p Fonksiyonu ile Predictive CLTV Segmentlerini Oluşturunuz
######################################

# from helpers.helpers import create_cltv_p
# cltv_p_deneme = create_cltv_p(df_prep)

def create_cltv_p(dataframe):
    today_date = dt.datetime(2011, 12, 11)

    ## recency kullanıcıya özel dinamik.
    rfm = dataframe.groupby('Customer ID').agg({'InvoiceDate': [lambda date: (date.max()-date.min()).days,
                                                                lambda date: (today_date - date.min()).days],
                                                'Invoice': lambda num: num.nunique(),
                                                'TotalPrice': lambda TotalPrice: TotalPrice.sum()})

    rfm.columns = rfm.columns.droplevel(0)

    ## recency_cltv_p
    rfm.columns = ['recency_cltv_p', 'T', 'frequency', 'monetary']

    ## basitleştirilmiş monetary_avg
    rfm["monetary"] = rfm["monetary"] / rfm["frequency"]

    rfm.rename(columns={"monetary": "monetary_avg"}, inplace=True)


    # BGNBD için WEEKLY RECENCY VE WEEKLY T'nin HESAPLANMASI
    ## recency_weekly_cltv_p
    rfm["recency_weekly_cltv_p"] = rfm["recency_cltv_p"] / 7
    rfm["T_weekly"] = rfm["T"] / 7



    # KONTROL
    rfm = rfm[rfm["monetary_avg"] > 0]

    ## recency filtre (daha saglıklı cltvp hesabı için)
    rfm = rfm[(rfm['frequency'] > 1)]

    rfm["frequency"] = rfm["frequency"].astype(int)

    # BGNBD
    bgf = BetaGeoFitter(penalizer_coef=0.01)
    bgf.fit(rfm['frequency'],
            rfm['recency_weekly_cltv_p'],
            rfm['T_weekly'])

    # exp_sales_1_month
    rfm["exp_sales_1_month"] = bgf.predict(4,
                                           rfm['frequency'],
                                           rfm['recency_weekly_cltv_p'],
                                           rfm['T_weekly'])
    # exp_sales_3_month
    rfm["exp_sales_3_month"] = bgf.predict(12,
                                           rfm['frequency'],
                                           rfm['recency_weekly_cltv_p'],
                                           rfm['T_weekly'])

    # expected_average_profit
    ggf = GammaGammaFitter(penalizer_coef=0.01)
    ggf.fit(rfm['frequency'], rfm['monetary_avg'])
    rfm["expected_average_profit"] = ggf.conditional_expected_average_profit(rfm['frequency'],
                                                                             rfm['monetary_avg'])
    # 6 aylık cltv_p
    cltv = ggf.customer_lifetime_value(bgf,
                                       rfm['frequency'],
                                       rfm['recency_weekly_cltv_p'],
                                       rfm['T_weekly'],
                                       rfm['monetary_avg'],
                                       time=6,
                                       freq="W",
                                       discount_rate=0.01)

    rfm["cltv_p"] = cltv

    # minmaxscaler
    scaler = MinMaxScaler(feature_range=(1, 100))
    scaler.fit(rfm[["cltv_p"]])
    rfm["cltv_p"] = scaler.transform(rfm[["cltv_p"]])

    # rfm.fillna(0, inplace=True)

    # cltv_p_segment
    rfm["cltv_p_segment"] = pd.qcut(rfm["cltv_p"], 3, labels=["C", "B", "A"])

    ## recency_cltv_p, recency_weekly_cltv_p
    rfm = rfm[["recency_cltv_p", "T", "monetary_avg", "recency_weekly_cltv_p", "T_weekly",
               "exp_sales_1_month", "exp_sales_3_month", "expected_average_profit",
               "cltv_p", "cltv_p_segment"]]


    return rfm

cltv_p = create_cltv_p(df_prep)
check_df(cltv_p)
cltv_p.head()

######################################
# Görev 4: İstenilen segmentlere ait kullanıcı id'lerine göre veri setini indirgeyiniz.
######################################

# id'lerin alınması
a_segment_ids = cltv_p[cltv_p["cltv_p_segment"] == "A"].index
b_segment_ids = cltv_p[cltv_p["cltv_p_segment"] == "B"].index
c_segment_ids = cltv_p[cltv_p["cltv_p_segment"] == "C"].index

# bu id'lere göre df'lerin indirgenmesi
a_segment_df = df_prep[df_prep["Customer ID"].isin(a_segment_ids)]
b_segment_df = df_prep[df_prep["Customer ID"].isin(b_segment_ids)]
c_segment_df = df_prep[df_prep["Customer ID"].isin(c_segment_ids)]
a_segment_df.head()

######################################
# Görev 5: Her bir segment için birliktelik kurallarının üretilmesi
######################################

from helpers.helpers import create_invoice_product_df

def create_rules(dataframe, country=False, head=5):
    if country:
        dataframe = dataframe[dataframe['Country'] == country]
        dataframe = create_invoice_product_df(dataframe)
        frequent_itemsets = apriori(dataframe, min_support=0.02, use_colnames=True)
        rules = association_rules(frequent_itemsets, metric="support", min_threshold=0.02)
        print(rules.sort_values("lift", ascending=False).head(head))
    else:
        dataframe = create_invoice_product_df(dataframe)
        frequent_itemsets = apriori(dataframe, min_support=0.02, use_colnames=True)
        rules = association_rules(frequent_itemsets, metric="support", min_threshold=0.02)
        print(rules.sort_values("lift", ascending=False).head(head))

    return rules

rules_a = create_rules(a_segment_df)
product_a = (rules_a["consequents"].apply(lambda x: list(x)[0]).astype("unicode")[0])

rules_b = create_rules(b_segment_df)
product_b = int(rules_b["consequents"].apply(lambda x: list(x)[0]).astype("unicode")[0])

rules_c = create_rules(c_segment_df)
product_c = int(rules_c["consequents"].apply(lambda x: list(x)[0]).astype("unicode")[0])

def check_id(stock_code):
    product_name = df_prep[df_prep["StockCode"] == stock_code][["Description"]].values[0].tolist()
    return print(product_name)

check_id(product_a)
check_id(product_b)
check_id(product_c)

######################################
# Görev 6: Alman Müşterilere Segmentlerine Göre Öneriler Yapınız
######################################

# cltv_p'nin çıktısı olan dataframe'e recommended_product adında bir değişken ekleyiniz.
cltv_p["recommended_product"] = " "

# her bir segment için 1 tane ürün ekleyiniz.
# Yani müşteri hangi segmentte ise onun için yukarıdan gelen kurallardan birisini ekleyiniz.

germany_ids = df_prep[df_prep["Country"] == "Germany"]["Customer ID"].drop_duplicates()

cltv_p.loc[(cltv_p.index.isin(germany_ids)) & (cltv_p["cltv_p_segment"] == "A"), "recommended_product"] = product_a
cltv_p.loc[(cltv_p.index.isin(germany_ids)) & (cltv_p["cltv_p_segment"] == "A")]

cltv_p.loc[(cltv_p.index.isin(germany_ids)) & (cltv_p["cltv_p_segment"] == "B"), "recommended_product"] = product_b
cltv_p.loc[(cltv_p.index.isin(germany_ids)) & (cltv_p["cltv_p_segment"] == "B")]

cltv_p.loc[(cltv_p.index.isin(germany_ids)) & (cltv_p["cltv_p_segment"] == "C"), "recommended_product"] = product_c
cltv_p.loc[(cltv_p.index.isin(germany_ids)) & (cltv_p["cltv_p_segment"] == "C")]

# kontrol
cltv_p[cltv_p.index.isin(germany_ids)]["recommended_product"].value_counts()
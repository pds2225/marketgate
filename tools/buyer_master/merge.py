import pandas as pd,re,json
d=pd.read_csv('buyer_candidate.csv',dtype=str,keep_default_na=False)
k=pd.read_csv('kotra_sns_full.csv',dtype=str,keep_default_na=False)
n=pd.read_csv('nipa_full.csv',dtype=str,keep_default_na=False)
S={}
S['before']=len(d)
KS='대한무역투자진흥공사_SNS 마케팅 수집 바이어 정보'; NS='정보통신산업진흥원_글로벌ICT포털해외바이어'
def nm(s): return re.sub(r'[^A-Z0-9가-힣]','',str(s).upper())
d['change_note']=''
# --- KOTRA compare
iso2=d[d.source_dataset==KS].groupby('country_raw')[['country_norm','country_iso3']].first()
ex=d[d.source_dataset==KS]; exkey=set(zip(ex.normalized_name.map(nm),ex.country_raw))
k['key']=list(zip(k['영어기업명'].map(nm),k['인솔바이어국가명']))
ku=k[k['영어기업명'].str.strip()!=''].drop_duplicates('key')
S['kotra_api_rows']=len(k); S['kotra_api_unique_name_country']=len(ku)
new=ku[~ku.key.isin(exkey)]; S['kotra_existing_matched']=int(ku.key.isin(exkey).sum()); S['kotra_new']=len(new)
def hs(h):
    h=re.sub(r'\.0$','',h.strip())
    if not h.isdigit(): return h
    if len(h)==5: h='0'+h
    if len(h)==10: h=h[:6]
    return h
nk=pd.DataFrame({'record_type':'buyer_candidate','source_dataset':KS,'source_file':'KOTRA SNS API 15155497 (2026-10-12)',
 'source_row_no':'','title':new['영어기업명'].str.strip(),'normalized_name':new['영어기업명'].map(nm),'country_raw':new['인솔바이어국가명'],
 'country_norm':new['인솔바이어국가명'].map(iso2.country_norm).fillna(''),'country_iso3':new['인솔바이어국가명'].map(iso2.country_iso3).fillna(''),
 'hs_code_raw':new['HS코드'],'hs_code_norm':new['HS코드'],'keywords_raw':new['관심상품내용']+' | '+new['한글HS코드명']+' | '+new['인솔바이어도시명'],
 'keywords_norm':'','has_contact':'0','contact_name':'','contact_email':'','contact_phone':'','contact_website':'','valid_until':'',
 'source_snapshot_date':'2026-10-12','distance_from_kr_km':'','contact_email_estimated':'False','change_note':'new_from_kotra_api'})
nk['keywords_norm']=nk.keywords_raw.str.lower()
# --- NIPA
n['buyNo']=n.buyNo.str.strip(); n['phone']=n.phone.str.strip()
isN=d.source_dataset==NS
d.loc[isN,'_buyno']=d.loc[isN,'contact_website'].str.extract(r'buyNo=(\d+)')[0]
m=n.set_index('buyNo')
S['nipa_api_rows']=len(n); S['nipa_existing_matched']=int(d.loc[isN,'_buyno'].isin(m.index).sum())
chg=0;fill=0
for i in d.index[isN]:
    b=d.at[i,'_buyno']
    if b in m.index:
        p=m.at[b,'phone']
        if p and p!=d.at[i,'contact_phone']:
            if d.at[i,'contact_phone'] in ('','-','(-)'): fill+=1
            else: chg+=1
            d.at[i,'contact_phone']=p; d.at[i,'change_note']='phone_updated_from_nipa_api'
S['nipa_phone_filled_blank']=fill; S['nipa_phone_changed']=chg
nn=n[~n.buyNo.isin(set(d._buyno.dropna()))]; S['nipa_new']=len(nn)
nnd=pd.DataFrame({'record_type':'buyer_candidate','source_dataset':NS,'source_file':'NIPA API B552551 (2026-10-12)','source_row_no':nn.buyNo,
 'title':nn.buyName.str.strip(),'normalized_name':nn.buyName.str.strip(),'country_raw':nn.nationName,'country_norm':nn.nationName,'country_iso3':'',
 'hs_code_raw':'','hs_code_norm':'','keywords_raw':'','keywords_norm':'','has_contact':'1','contact_name':'','contact_email':'','contact_phone':nn.phone,
 'contact_website':nn.detailLink,'valid_until':'','source_snapshot_date':'2026-10-12','distance_from_kr_km':'','contact_email_estimated':'False','change_note':'new_from_nipa_api'})
d=d.drop(columns='_buyno')
# --- drop TradeMap
S['trademap_removed']=int((d.source_dataset=='ITC_TradeMap_ImportingCompanies').sum())
d=d[d.source_dataset!='ITC_TradeMap_ImportingCompanies']
# also drop KOTRA new rows that duplicate TradeMap? n/a
a=pd.concat([d,nk,nnd],ignore_index=True)
# --- cleanup
pe=a.contact_email.str.lower().str.strip()=='info@globalict.kr'; S['portal_email_blanked']=int(pe.sum())
a.loc[pe,'contact_email']=''; a.loc[pe,'contact_email_estimated']='False'
a.loc[pe,'change_note']=(a.loc[pe,'change_note']+';portal_email_removed').str.strip(';')
fp=a.contact_phone.str.strip().ne('') & (a.contact_phone.str.replace(r'\D','',regex=True).str.len()<6); S['fake_phone_blanked']=int(fp.sum())
a.loc[fp,'contact_phone']=''; a.loc[fp,'change_note']=(a.loc[fp,'change_note']+';fake_phone_removed').str.strip(';')
a['email_guessed']=(a.contact_email_estimated=='True')&(a.contact_email!=''); S['email_guessed']=int(a.email_guessed.sum())
a['hs6']=a.hs_code_norm.map(hs)
ksure=a.source_dataset.str.startswith('한국무역보험공사_화장품')
a['hs_flag']=''
a.loc[a.hs6=='', 'hs_flag']='missing'
a.loc[(a.hs6!='')&(a.hs6.str.len()==4),'hs_flag']='hs4_only'
a.loc[(a.hs6!='')&~a.hs6.str.fullmatch(r'\d{4}|\d{6}'),'hs_flag']='invalid'
a.loc[ksure&(a.hs6!=''),'hs_flag']='invalid_industry_code(KSIC)'
a.loc[ksure,'hs6']=''
# Dasom approved 2026-10-12: K-SURE cosmetics buyers -> HS heading 3304 (inferred from industry, 4-digit only)
a.loc[ksure,'hs6']='3304'; a.loc[ksure,'hs_flag']='hs_inferred_from_industry'
a.loc[ksure,'change_note']=(a.loc[ksure,'change_note']+';hs_inferred_from_industry').str.strip(';')
S['hs_inferred_from_industry']=int(ksure.sum())
a['hs_code_norm']=a.hs6; a=a.drop(columns='hs6')
S['hs_invalid']=int(a.hs_flag.str.startswith('invalid').sum())
addr=a.country_raw.str.len().gt(25)|a.country_raw.str.contains(r'\d|,'); S['country_address_fixed']=int(addr.sum())
a['address']=''; a.loc[addr,'address']=a.loc[addr,'country_raw']; a.loc[addr,'country_raw']=a.loc[addr,'country_norm']
a['buyer_name']=a.normalized_name.where(a.normalized_name!='',a.title)
real_email=(a.contact_email.str.contains('@'))&~a.email_guessed
real_phone=a.contact_phone.str.replace(r'\D','',regex=True).str.len()>=6
a['has_contact']=(real_email|real_phone).map({True:'1',False:'0'})
base=(a.buyer_name.str.strip()!='')&(a.country_norm!='')&(real_email|real_phone)
a['contact_ready']=(base&(a.hs_code_norm.str.len()>=4)).astype(int)
a['contact_ready_without_hs']=base.astype(int)
a['contact_type']=(real_email.map({True:'email',False:''})+'+'+real_phone.map({True:'phone',False:''})).str.strip('+')
S['after']=len(a); S['contact_ready']=int(a.contact_ready.sum()); S['contact_ready_without_hs']=int(a.contact_ready_without_hs.sum())
S['ready_by_source']=a[a.contact_ready==1].source_dataset.value_counts().to_dict()
S['ready_nohs_by_source']=a[a.contact_ready_without_hs==1].source_dataset.value_counts().to_dict()
S['after_by_source']=a.source_dataset.value_counts().to_dict()
S['old_has_contact']=int((d.has_contact=='1').sum())
a.to_csv('buyer_master_draft.csv',index=False,encoding='utf-8-sig')
json.dump(S,open('stats.json','w'),ensure_ascii=False,indent=1); print(json.dumps(S,ensure_ascii=False,indent=1))

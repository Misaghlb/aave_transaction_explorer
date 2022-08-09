from datetime import datetime, timezone
from enum import Enum

import pandas as pd
import pytz
import requests
import streamlit as st

st.set_page_config(page_title='Aave Explorer', layout='wide', page_icon=':explorer:')
st.title("Aave v2 and v3 Transaction Explorer - All chains in one")


class Chain(Enum):
    Ethereum = 'Ethereum'
    Optimism = 'Optimism'
    Arbitrum = 'Arbitrum'
    Polygon_v3 = 'Polygon v3'
    Polygon_V2 = 'Polygon v2'
    Avalanche_v2 = 'Avalanche v2'
    Avalanche_v3 = 'Avalanche v3'
    Harmony = 'Harmony'
    Fantom = 'Fantom'


def get_chain_addresses(chain_name: Chain):
    if chain_name == Chain.Avalanche_v2:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v2-avalanche-extended'

    if chain_name == Chain.Avalanche_v3:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v3-avalanche'

    if chain_name == Chain.Ethereum:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v2-ethereum-extended'

    if chain_name == Chain.Optimism:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v3-optimism-extended'

    if chain_name == Chain.Polygon_v3:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v3-polygon-extended'

    if chain_name == Chain.Polygon_V2:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v2-polygon-extended'

    if chain_name == Chain.Harmony:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v3-harmony-extended'

    if chain_name == Chain.Fantom:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v3-fantom-extended'

    if chain_name == Chain.Arbitrum:
        return 'https://api.thegraph.com/subgraphs/name/messari/aave-v3-arbitrum-extended'


def humanized_time(ts_start):
    ts_end = datetime.utcnow().replace(tzinfo=timezone.utc)
    ts_diff = ts_end - ts_start
    secs = ts_diff.total_seconds()
    days, secs = divmod(secs, secs_per_day := 60 * 60 * 24)
    hrs, secs = divmod(secs, secs_per_hr := 60 * 60)
    mins, secs = divmod(secs, secs_per_min := 60)
    answer2 = ''
    if days != 0:
        answer2 += f'{int(days)} days '
    if hrs != 0:
        answer2 += f'{int(hrs)} hrs '

    if mins != 0:
        answer2 += f'{int(mins)} mins '
    else:
        answer2 += f'{int(secs)} secs '
    return answer2 + ' ago'


# @st.cache(ttl=6 * 60 * 60)  # 6 hours
def fetch_data(chain: Chain, tr_hash):
    payload = {
        "query": "{ withdraws(first: 1, where: { hash: \"%s\" }){ id hash timestamp amount amountUSD asset {symbol decimals id} account { id } }  deposits(first: 1, where: { hash: \"%s\" }){ id hash timestamp amount amountUSD asset {symbol decimals id} account { id } } borrows(first: 1, where: { hash: \"%s\" }){ id hash timestamp amount amountUSD asset {symbol decimals id} account { id } } repays(first: 1, where: { hash: \"%s\" }){ id hash timestamp amount amountUSD asset {symbol decimals id} account { id } } liquidates(first: 1, where: { hash: \"%s\" }){ id hash timestamp amount amountUSD asset {symbol decimals id} } }" % (
            tr_hash, tr_hash, tr_hash, tr_hash, tr_hash),
    }
    res = requests.post(url=get_chain_addresses(chain),
                        json=payload).json()['data']

    if res:
        actions = clean_data(res)
    else:
        return False

    return actions


def clean_data(res):
    actions = []
    for item in ['withdraws', 'deposits', 'borrows', 'repays', 'liquidates']:
        if not res[item]:
            continue
        action_content_list = res[item]
        for action in action_content_list:
            clean_action = {}
            clean_action['Time'] = datetime.fromtimestamp(int(action['timestamp'])).strftime("%m/%d/%Y, %H:%M:%S")
            clean_action['py_date'] = datetime.fromtimestamp(int(action['timestamp']), pytz.timezone("UTC"))
            clean_action['Type'] = item
            clean_action['Asset Symbol'] = action['asset']['symbol']
            clean_action['transaction_hash'] = action['hash']
            clean_action['Asset ID'] = action['asset']['id']
            clean_action['Asset Amount'] = int(int(action['amount']) / pow(10, int(action['asset']['decimals'])))
            clean_action['Amount USD'] = action['amountUSD']
            clean_action['user'] = action['account']['id']
            # clean_action['chain'] = action['chain']
            actions.append(clean_action)
    return actions


st.markdown('---')
c1, c2, c3 = st.columns((1, 2, 1))

input_hash = c2.text_input('Enter Transaction Hash:',
                           '0x0784ff9cf55478cc6b389b0028f9d4da9556a8ca36b4ccbce4f21b2ecf756e72',
                           placeholder='Input the Transaction Hash')

data = ''
selected_chain = ''
for chain in Chain:
    data = fetch_data(chain, input_hash)
    # find the right data so exit and don't search in next chains
    if data:
        selected_chain = chain
        break

df = pd.DataFrame(
    data,
    columns=["Time", "Type", "Asset Symbol", "Asset Amount", "Amount USD", "Asset ID"])
st.markdown('---')

c1, c2 = st.columns(2)
c1.write('#### User: ')
c1.markdown(
    f"<a style='text-decoration: none;' href='https://etherscan.io/address/{data[0]['user']}'>{data[0]['user']}</a>",
    unsafe_allow_html=True)
c2.markdown('#### Transaction Hash: ')
c2.markdown(
    f"<a style='text-decoration: none;' href='https://etherscan.io/tx/{data[0]['transaction_hash']}'>{data[0]['transaction_hash']}</a>",
    unsafe_allow_html=True)
c1.markdown(
    f'<span style="font-family:sans-serif; color:grey; font-size: 18px;">Timestamp (UTC): </span><span style="font-family:sans-serif; color:purple; font-size: 16px;">{humanized_time(data[0]["py_date"])}</span>',
    unsafe_allow_html=True)
c2.markdown(
    f'<span style="font-family:sans-serif; color:grey; font-size: 22px;">Chain: </span><span style="font-family:sans-serif; color:purple; font-size: 20px;">{selected_chain.value}</span>',
    unsafe_allow_html=True)
st.markdown('#### Actions: ')
st.table(df)

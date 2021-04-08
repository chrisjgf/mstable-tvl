from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import requests

basset_transport = RequestsHTTPTransport(
    url='https://api.thegraph.com/subgraphs/name/mstable/mstable-protocol-staging',
    verify=True,
    retries=3,
)
fasset_transport = RequestsHTTPTransport(
    url='https://api.thegraph.com/subgraphs/name/mstable/mstable-feeder-pools',
    verify=True,
    retries=3,
)
governance_transport = RequestsHTTPTransport(
    url='https://api.thegraph.com/subgraphs/name/mstable/mstable-governance-staging',
    verify=True,
    retries=3,
)

masset_client = Client(transport=basset_transport)
fasset_client = Client(transport=fasset_transport)
governance_client = Client(transport=governance_transport)

governance_query = gql(
    '''
    query {
        incentivisedVotingLockups {
            totalValue
        }
    }
    '''
)

fasset_query = gql(
    '''
    query {
        feederPools {
            basket {
                bassets {
                    token{
                        symbol
                    }
                     vaultBalance {
                        simple
                    }
                }
            }
            masset {
                symbol
            }
        }
    }
    '''
)

basset_query = gql(
    '''
    query {
        massets {
            token {
                symbol
            }
            totalSupply {
                exact
                decimals
                simple
            }
            basket {
                bassets {
                    ratio
                    vaultBalance {
                        exact
                        decimals
                        simple
                    }
                    token {
                        symbol
                    }
                }
            }
        }
    }
    '''
)

basset_response = masset_client.execute(basset_query)
fasset_response = fasset_client.execute(fasset_query)
governance_response = governance_client.execute(governance_query)

massets = basset_response['massets']
feeder_pools = fasset_response['feederPools']
user_lockups = governance_response['incentivisedVotingLockups']

btc_price_response = requests.get(
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd").json()
btc_price = btc_price_response['bitcoin']['usd']

mta_price_response = requests.get(
    "https://api.coingecko.com/api/v3/simple/price?ids=meta&vs_currencies=usd").json()
mta_price = mta_price_response['meta']['usd']

mta_balance = int(user_lockups[0]['totalValue']) / 1e18

tvl_usd = 0

non_feeder_tvl = 0
mbtc_tvl = 0
musd_tvl = 0

print('------------------')
for masset in massets:
    masset_symbol = masset['token']['symbol']
    masset_supply = float(masset['totalSupply']['simple'])
    multiplier = btc_price if (masset_symbol == "mBTC") else 1
    bassets = masset['basket']['bassets']

    for basset in bassets:
        basset_symbol = basset['token']['symbol']
        basset_balance = float(basset['vaultBalance']['simple'])
        basset_decimals = float(basset['vaultBalance']['decimals'])
        basset_ratio = float(basset['ratio'])
        basset_tvl = basset_balance * multiplier

        if (masset_symbol == 'mBTC'):
            mbtc_tvl += basset_tvl
        else:
            musd_tvl += basset_tvl

        tvl_usd += basset_tvl
        non_feeder_tvl += basset_tvl

        print(basset_symbol + ":\t",
              f"${basset_tvl:,.2f}", f"({basset_balance:,.2f})", )
    print('------')

print(f'mBTC (exc. Feeder) TVL:\t', f"${mbtc_tvl:,.2f}")
print(f'mUSD (exc. Feeder) TVL:\t', f"${musd_tvl:,.2f}")
print('------')

feeder_tvl = 0
mbtc_feeder_tvl = 0
musd_feeder_tvl = 0

for pool in feeder_pools:
    masset_symbol = pool['masset']['symbol']
    multiplier = btc_price if (masset_symbol == "mBTC") else 1
    pool_fassets = pool['basket']['bassets']

    for fasset in pool_fassets:
        fasset_symbol = fasset['token']['symbol']
        if fasset_symbol not in ['mUSD', 'mBTC']:
            fasset_balance = float(fasset['vaultBalance']['simple'])
            fasset_tvl = fasset_balance * multiplier
            tvl_usd += fasset_tvl
            feeder_tvl += fasset_tvl
            if masset_symbol == "mBTC":
                mbtc_feeder_tvl += fasset_tvl
            else:
                musd_feeder_tvl += fasset_tvl
            print(fasset_symbol + ":\t",
                  f"${fasset_tvl:,.2f}", f"({fasset_balance:,.2f})")

print('------')
print(f'mBTC Feeder TVL:\t', f"${mbtc_feeder_tvl:,.2f}")
print(f'mUSD Feeder TVL:\t', f"${musd_feeder_tvl:,.2f}")
print(f'mBTC + mUSD Feeder TVL:\t', f"${feeder_tvl:,.2f}")
print('------')

print(f'Feeder TVL:\t', f"${feeder_tvl:,.2f}")
print('Total TVL: \t', f"${tvl_usd:,.2f}")
print('MTA in Governance: \t' + f"${mta_balance * mta_price:,.2f}",
      f'({mta_balance:,.2f})')

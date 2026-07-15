import requests

from config import require_secret

headers = {
    "X-API-Key": require_secret("METABASE_API_KEY")
}

urls = [
    ("1_offerta_cantonal", "https://cc-alloggio.ddns.net/api/public/dashboard/6a6f8320-4b2b-4e3d-8130-1ccfae2de8f1/dashcard/206/card/77/csv", False),
    ("1_offerta_regional", "https://cc-alloggio.ddns.net/api/card/77/query/csv", True),
    ("1_offerta_tabellina", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/218/card/145/query/csv", True),
    # ("2_praticato_bar_ec", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/180/card/139/query/csv", True),
    # ("2_praticato_stack1", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/60/card/60/query/csv", True),
    # ("2_praticato_stack2", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/62/card/62/query/csv", True),
    # ("3_reddito_regional", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/84/card/77/query/csv", True),
    # ("3_reddito_cantonal", "https://cc-alloggio.ddns.net/api/card/78/query/csv", True),
    # ("3_reddito_stack", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/81/card/75/query/csv", True),
    # ("4_scompenso_line", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/97/card/87/query/csv", True),
    # ("4_scompenso_bar1", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/161/card/136/query/csv", True),
    # ("5_sostenibile_bar1", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/169/card/137/query/csv", True),
    # ("5_sostenibile_bar2", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/136/card/118/query/csv", True),
    # ("5_sostenibile_bar3", "https://cc-alloggio.ddns.net/api/dashboard/2/dashcard/118/card/102/query/csv", True)
]

for name, url, use_header in urls:
    print(f"--- {name} ---")
    try:
        h = headers if use_header else {}
        r = requests.post(url, headers=h)
        lines = r.text.split('\n')
        print('\n'.join(lines[:3]))
    except Exception as e:
        print("ERROR:", e)
    print()

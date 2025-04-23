import requests

headers = {
    'authority': 'sfcctumi.sfcc-sc.tumi.com',
    'method': 'POST',
    'path': '/api/search-rec/3',
    'scheme': 'https',
    'accept': 'application/json',
    'accept-encoding': 'gzip, deflate, br, zstd',
    'accept-language': 'en-US,en;q=0.9',
    'authorization': '01-9c6aeef5-eae24a8bf7b30c0253e66933653a164eefbcebe4',
    'content-length': '473',
    'content-type': 'application/json',
    'origin': 'https://www.tumi.com',
    'priority': 'u=1, i',
    'referer': 'https://www.tumi.com/',
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
}

response = requests.post('https://sfcctumi.sfcc-sc.tumi.com/api/search-rec/3', headers=headers)
print(response)
print(response.text)
print(response.status_code)
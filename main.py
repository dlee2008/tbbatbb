#!python3.9
# -*- encoding: utf-8 -*-

import requests, re, yaml, time, base64
from re import Pattern
from typing import Any, Dict, List

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

rss_url:str = 'https://www.cfmem.com/feeds/posts/default?alt=rss'
clash_reg:Pattern = re.compile(r'clash订阅链接：(?:&lt;/span&gt;&lt;span style=&quot;background-color: white; color: #111111; font-size: 15px;&quot;&gt;)?(https?.+?)(?:&lt;|<)/span(?:&gt;|>)')
v2ray_reg:Pattern = re.compile(r'v2ray订阅链接：(?:&lt;/span &gt;&lt;/span &gt;&lt;/span &gt;&lt;span style=&quot;color: #111111;&quot;&gt;&lt;span style=&quot;font-size: 15px;&quot;&gt;)?(https?.+?)(?:&lt;|<)/span(?:&gt;|>)')

clash_output_file:str = './dist/clash.config.yaml'
clash_output_tpl:str = './clash.config.template.yaml'
v2ray_output_file:str = './dist/v2ray.config.txt'
    
clash_extra:List[str] = []

blacklist:List[str] = list(map(lambda l:l.replace('\r', '').replace('\n', '').split(':'), open('blacklists.txt').readlines()))

def clash_urls(html:str) -> List[str]:
    '''
    Fetch URLs For Clash
    '''
    return clash_reg.findall(html) + clash_extra

def v2ray_urls(html:str) -> List[str]:
    '''
    Fetch URLs For V2Ray
    '''
    return v2ray_reg.findall(html)

def fetch_html(url:str) -> str:
    '''
    Fetch The Content Of url
    '''
    try:
        resp:requests.Response = requests.get(url, verify=False, timeout=10)
        if resp.status_code != 200:
            print(f'[!] Got HTTP Status Code {resp.status_code} When Requesting {url}')
            return '' 
        return resp.text
    except Exception as e:
        print(f'[-] Error Occurs When Fetching Content Of {url}: {e}')
        return ''

def merge_clash(configs:List[str]) -> str:
    '''
    Merge Multiple Clash Configurations
    '''
    config_template:Dict[str, Any] = yaml.safe_load(open(clash_output_tpl).read())
    proxies:List[Dict[str, Any]] = []
    for i in range(len(configs)):
        tmp_config:Dict[str, Any] = yaml.safe_load(configs[i])
        if 'proxies' not in tmp_config: continue
        for j in range(len(tmp_config['proxies'])):
            proxy:Dict[str, Any] = tmp_config['proxies'][j]
            if any(filter(lambda p:p[0] == proxy['server'] and str(p[1]) == str(proxy['port']), blacklist)): continue
            if any(filter(lambda p:p['server'] == proxy['server'] and p['port'] == proxy['port'], proxies)): continue
            proxy['name'] = proxy['name'] + f'_{i}@{j}'
            proxies.append(proxy)
    node_names:List[str] = list(map(lambda n: n['name'], proxies))
    config_template['proxies'] = proxies
    for grp in config_template['proxy-groups']:
        if 'xxx' in grp['proxies']:
            grp['proxies'].remove('xxx')
            grp['proxies'].extend(node_names)

    return yaml.safe_dump(config_template, indent=1, allow_unicode=True)

def merge_v2ray(configs:List[str]) -> str:
    '''
    Merge Multiple V2Ray Configurations
    '''
    linesep:str = '\r\n'
    decoded_configs:List[str] = list(map(lambda c: base64.b64decode(c).decode('utf-8'), configs))
    if len(decoded_configs) > 0:
        if linesep not in decoded_configs[0]:
            linesep = '\n'
    merged_configs:List[str] = []
    for dc in decoded_configs:
        merged_configs.extend(dc.split(linesep))
    return base64.b64encode(linesep.join(merged_configs).encode('utf-8')).decode('utf-8')

def main():
    rss_text:str = fetch_html(rss_url)
    if rss_text is None or len(rss_text) <= 0: 
        print('[-] Failed To Fetch Content Of RSS')
        return
    clash_url_list:List[str] = clash_urls(rss_text)
    v2ray_url_list:List[str] = v2ray_urls(rss_text)
    print(f'[+] Got {len(clash_url_list)} Clash URLs, {len(v2ray_url_list)} V2Ray URLs')

    clash_configs:List[str] = [] 
    for u in clash_url_list:
        html:str = fetch_html(u)
        if html is not None and len(html) > 0: 
            clash_configs.append(html)
            print(f'[+] Configuration {u} Downloaded')
        else: 
            print(f'[-] Failed To Download Clash Configuration {u}')
        time.sleep(0.5)
    v2ray_configs:List[str] = []
    for u in v2ray_url_list:
        html:str = fetch_html(u)
        if html is not None and len(html) > 0: 
            v2ray_configs.append(html)
            print(f'[+] Configuration {u} Downloaded')
        else: 
            print(f'[-] Failed To Download V2Ray Configuration {u}')
        time.sleep(0.5)

    clash_merged:str = merge_clash(clash_configs)
    v2ray_merged:str = merge_v2ray(v2ray_configs)

    with open(clash_output_file, 'w') as f: f.write(clash_merged)
    with open(v2ray_output_file, 'w') as f: f.write(v2ray_merged)

if __name__ == '__main__':
    main()

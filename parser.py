import json, os,re
import pandas as pd
import  matplotlib.pyplot as plt

import sys

if not  (len(sys.argv) > 1):
    print ('Number of arguments:', len(sys.argv), 'arguments.')
    print ('Argument List:', str(sys.argv))
    exit (1)



def findHeader(req,headertype,headername,op = None):
    my_temp_values = []
    value = "None"
    if headertype == 'response':
        for h in req['response']['headers']:
            if op == 'in':
                if headername in h['name']:
                    value = h['value']
                    break
            else:
                # respons headeren Content-Length har store bokstaver i prod, små i preprod (!)
                if headername == h['name'].lower():
                    value = h['value']
                    break
    if headertype == 'cdn-timing':
        value = 0
        for h in req['response']['headers']:
            if op == 'eq':
                if 'server-timing' in h['name']:
                    if headername in h['value']:

                        value = int(h['value'].split(';')[1].split('=')[1])
                        break
        if value is None:
            return 0
    return value

colmms = ['url','host','host-type','method','status','ext','cpcode','ttl','server','cdn-cache','cdn-cache-parent','cdn-cache-key','cdn-req-id','vary','appOrigin','content-length','content-length-origin','blocked','dns','ssl','connect','send','ttfb','receive','edgeTime','originTime'
]

har_file = str(sys.argv[1])
h = open(har_file, 'r+')
har = json.load(h)


dat_clean = pd.DataFrame(columns=colmms)
for r in har['log']['entries']:
    u = str(r['request']['url']).split('?')[0]
    host = re.search('://(.+?)/', u, re.IGNORECASE).group(0).replace(':','').replace('/','')
    
    cachekey = str(findHeader(r,'response','x-cache-key','eq'))
    if not cachekey == 'None':
        cachekey = cachekey.split('/')
        cpcode = int(cachekey[3])
        ttl = cachekey[4]
        cdnCache = str(findHeader(r,'response','x-cache','eq')).split(' ')[0]
        cdnCacheParent = str(findHeader(r,'response','x-cache-remote','eq')).split(' ')[0]
        origin = str(findHeader(r,'response','x-cache-key','eq')).split('/')[5]
    else:
        cachekey = "None"
        cpcode = "None"
        ttl = "None"
        cdnCache = "None"
        cdnCacheParent = "None"
        origin = "None"

    ext = re.search(r'(\.[A-Za-z0-9]+$)', u, re.IGNORECASE)
    #if any(tld in host for tld in FirstParty):
    #    hostType = 'First Party'
    #else:
    #    hostType = 'Third Party'
    
    if ext is None:
        ext = "None"
    else:
        ext = ext.group(0).replace('.','') 
    ct = findHeader(r,'response','content-length','eq')
    if ct == "None":
        ct = 0
    else:
        ct = int(ct)
    if ext in ['jpeg','png','jpg']:
        ct_origin = findHeader(r,'response','x-im-original-size','eq')
    else:
        ct_origin = findHeader(r,'response','x-akamai-ro-origin-size','eq')
    if ct_origin == "None":
        ct_origin = 0
    else:
        ct_origin = int(ct_origin)
    new_row = {
        'url':u,
        'host':host,
        #'host-type':hostType,
        'method':r['request']['method'],
        'status':r['response']['status'],
        'ext':ext,
        'cpcode':cpcode,
        'ttl':ttl,
        'server':str(findHeader(r,'response','server','eq')),
        'cdn-cache':cdnCache,
        'cdn-cache-parent':cdnCacheParent,
        'cdn-cache-key':str(findHeader(r,'response','x-true-cache-key','eq')),
        'cdn-req-id':str(findHeader(r,'response','x-akamai-request-id','eq')),
        'vary':str(findHeader(r,'response','vary','eq')),
        'appOrigin':origin,
        'content-length':ct,
        'content-length-origin':ct_origin,
        'blocked':r['timings']['blocked'],
        'dns':r['timings']['dns'],
        'ssl':r['timings']['ssl'],
        'connect':r['timings']['connect'],
        'send':r['timings']['send'],
        'ttfb':r['timings']['wait'],
        'receive':r['timings']['receive'],
        'edgeTime':findHeader(r,'cdn-timing','edge','eq'),
        'originTime':findHeader(r,'cdn-timing','origin','eq') 
        }

    # filter away everything but the jpeg images
    if ('jpeg' in new_row['url']):
        dat_clean = dat_clean.append(new_row,ignore_index=True)
        

    #print ('length of dat_clean: ', dat_clean.size)
    #print (type(dat_clean))
directory = 'out'
# dat_clean = dat_clean.groupby(colmms).size().reset_index(name='Count')   
dat_clean.to_csv(directory+'/output.csv',index=False)

tmp = dat_clean

print (tmp.info())

# extract and explore a couple interesting values:
# print (tmp['url'].count())
count = tmp['url'].count()
receive =  tmp['receive'].mean()
content_length =  tmp['content-length'].mean()
ttfb =  tmp['ttfb'].mean()
print ('mean:')
print (ttfb)
print (tmp['content-length'])

tmp = tmp.groupby('ext')["ttfb", "receive"].mean().reset_index()
tmp[["ext", "ttfb", "receive"]].plot(x="ext", kind="bar", stacked=True,label='Series')
plt.title('Thumbnail download timings, n={}\nttfb={:4.2f}ms, receive={:4.2f}ms, mean thumb size:{:.0f}'.format(count, ttfb, receive, content_length))
plt.xlabel('Extensions')
plt.ylabel('Milliseconds')
plt.show()
del tmp  

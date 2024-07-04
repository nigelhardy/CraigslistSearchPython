import math

def haversine(lat1, lon1, lat2, lon2):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers (use 3956 for miles)
    r = 6371
    
    # Calculate the result and convert to miles
    return c * r * 0.62137273665

def calculate_scores(results, search_type):
    if search_type == "SC":
        return calc_sc_scores(results)
    elif search_type == "LG":
        return calc_lg_scores(results)


def calc_sc_scores(results):
    for res in results:
        price = res['price']
        
        score = 0
        if price != -1:
            score += (2400 - price) / 1000
        attribute_points = {'2BR / 1Ba', '2BR / 1.5Ba', '2BR / 2Ba'}
        res['sqr_foot'] = -1
        for attr in res['attributes']:
            attr_lc = attr.lower()

            if 'off-street parking' in attr_lc:
                score += 1
            if 'attached garage' in attr_lc:
                score += 3
            if '2br' in attr_lc:
                score += 4
            if '1.5ba' in attr_lc:
                score += 1
            if '0br' in attr_lc:
                score -= 4
            if '1br' in attr_lc:
                pass
            if 'ft2' in attr_lc:
                sqr_foot = int(attr_lc.split("ft2")[0])
                score += (sqr_foot - 600) / 500
                res['sqr_foot'] = sqr_foot
        res['score'] = score

    sorted_data = sorted(results, key=lambda x: x['score'], reverse=True)
    return sorted_data

def calc_lg_scores(results):
    addrs = {}
    rem_idxs = []
    # 37.2609611,-121.9611325
    center_lat = 37.2609611
    center_long = -121.9611325
    for idx, res in enumerate(results):

        price = res['price']
        
        score = 0
        if price != -1:
            score += (3200 - price) / 800
        res['sqr_foot'] = -1
        for attr in res['attributes']:
            attr_lc = attr.lower()
            if 'off-street parking' in attr_lc:
                score += 1
            if 'attached garage' in attr_lc:
                score += 3
            if 'carport' in attr_lc:
                score -= 1
            if '3br' in attr_lc:
                score += 4
            if '2ba' in attr_lc:
                score += 1
            if '0br' in attr_lc:
                score -= 6
            if '1br' in attr_lc:
                score -= 5
            if 'ft2' in attr_lc:
                sqr_foot = int(attr_lc.split("ft2")[0])
                score += (sqr_foot - 800) / 500
                res['sqr_foot'] = sqr_foot
        latitude, longitude = map(float, res['coord'].split(';'))
        distance = haversine(center_lat, center_long, latitude, longitude)
        score += 3 - distance
        res['distance'] = distance
        res['score'] = score
        if res['address'] != '':
            if res['address'] in addrs:
                if score > results[addrs[res['address']]]['score']:
                    rem_idxs.append(addrs[res['address']])
                    addrs[res['address']] = idx
                else:
                    rem_idxs.append(idx)
            else:
                addrs[res['address']] = idx
    filtered_list = [results[i] for i in range(len(results)) if i not in rem_idxs]
    sorted_data = sorted(filtered_list, key=lambda x: x['score'], reverse=True)
    return sorted_data

# bad stuff
## garage space used as an extra room
## Underground parking garage
## Garage lot
## coin-operated laundry, Coin-Op Laundry


## laundry on-site

# good stuff
## All utilities are included, Water & Garbage Service Included
## A/C, Air Conditioning, Air Conditioner
## Dual Pane Windows
## in-unit washer/dryer, In-Home Washer/Dryer, w/d in unit  
## Pet-Friendly, dogs are ok
## One-Car Garage


## Group together: Shadowcreek (2474 South Bascom Avenue)
# fake ads
#   https://sfbay.craigslist.org/sby/apa/d/san-jose-great-location-easy-access-to/7762730613.html
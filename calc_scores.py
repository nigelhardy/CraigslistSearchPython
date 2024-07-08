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

def calc_price_score_sc(price):
    if price < 2000:
        return -2
    score_change = (3200 - price) / 800
    return score_change

def calc_sqr_foot_score_sc(sqr_foot):
    score_change = (sqr_foot - 800) / 500
    if sqr_foot < 500 or sqr_foot > 3000:
        score_change = -5
    score_change = min(score_change, 4)
    return score_change

def calc_distance_sc(distance):
    score_change = (8 - distance) * .25
    return score_change

def get_sc_scoring_info():
    score_info = {}
    ## basically the location of the boardwalk
    score_info['location'] = [36.964967039128446, -122.01459377274979]
    ## These need to be full matches, not partial
    attr_scores = {"off-street parking": 1,
                   'street parking': -2,
                   "attached garage": 3,
                   "carport": -1,
                   "3br":4,
                   "2br":3,
                   "1br": -1,
                   "0br": -6,
                   "w/d in unit": 2,
                   "apartment": -1,
                   "house": 2,
                   "townhouse": 1,
                   "air conditioning":2,
                   "CENTURY 21 VERDESCHI AND WALSH REALTY.;".lower(): -10, # spam
                   "CENTURY 21 VERDESCHI AND WALSH REALTY".lower(): -10, # spam
                   "ft2": calc_sqr_foot_score_sc, # todo, make function?
                   }
    
    # TODO there will be some where they are a subset of another
    # like garage, no garage, 1-car garage, etc, need to handle those!
    # parking garage

    # Single Car Garage
    desc_scores = {"🆃🅴🆇🆃 ME NUMBER!!!!":-10, # spam
                   "converted garage": -10,
                   "no garage": -10,
                   "parking garage": -6,
                   "garage": 5,
                   "TEXT ME NUMBER!!!!": -10, # spam
                   "TEXT YOUR CONTACT NOW": -10, # spam
                   "Luxury lobby and reception area fully attended": -10,
                   "Occupancy Limit: 1 People": -5,
                   "💫Pre-installed intrusion alarm": -10}
    score_info['desc'] = desc_scores
    title_scores = {"":2,}
    score_info['title'] = title_scores
    score_info['price_func'] = calc_price_score_sc
    score_info['attrs'] = attr_scores
    score_info['distance'] = calc_distance_sc
    return score_info

def calc_sc_scores(results):
    score_info = get_sc_scoring_info()
    sorted_data = calc_scores(results, score_info)
    return sorted_data

## Convert this to the more generic style
def calc_lg_scores(results):
    addrs = {}
    rem_idxs = []
    # 37.2609611,-121.9611325
    center_lat = 37.2609611
    center_long = -121.9611325
    for idx, res in enumerate(results):

        price = res['price']

        score = 0
        if price != -1 and price > 2000:
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


## TODO, create a score report card that shows the pros and cons of a listing
# good for debugging and quickly understanding a score/listing
def calc_scores(results, score_info):
    addrs = {}
    rem_idxs = []
    center_lat = score_info["location"][0]
    center_long = score_info["location"][1]
    # basically at the boardwalk
    # 36.964967039128446, -122.01459377274979
    for idx, res in enumerate(results):
        price = res['price']
        score = 0
        if price != -1 and price > 2000:
            score += (3200 - price) / 800
        res['sqr_foot'] = -1
        for attr in res['attributes']:
            attr_lc = attr.lower()
            if "ft2" in attr_lc:
                sqr_foot = int(attr_lc.split("ft2")[0])
                score += score_info['attrs']['ft2'](sqr_foot)
                res['sqr_foot'] = sqr_foot
            elif attr_lc in score_info['attrs']:
                if not callable(score_info['attrs'][attr_lc]):
                    score += score_info['attrs'][attr_lc]
        for item in score_info['title']:
            if item.lower() in res['title']:
                score += score_info['title'][item]
        for item in score_info['desc']:
            ## TODO make this be either more specific or less, for spam more specific
            ## allowing both right now for no good reason, maybe separate spam and scoring
            if item.lower() in res['description'].lower() or item in res['description']:
                score += score_info['desc'][item]
        latitude, longitude = map(float, res['coord'].split(';'))
        distance = haversine(center_lat, center_long, latitude, longitude)
        score += score_info['distance'](distance)
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
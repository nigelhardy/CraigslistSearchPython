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
    if price < 2200 and price > 2000:
        return -2
    elif price <= 2000 and price > 1800:
        return -4
    elif price <= 1800:
        return -10
    score_change = 0
    if price > 3199:
        score_change = -3
    elif price > 3000:
        score_change = -1
    elif price > 2900:
        score_change = 0
    elif price > 2700:
        score_change = 2
    elif price > 2500:
        score_change = 4
    return score_change

def calc_sqr_foot_score_sc(sqr_foot):
    if sqr_foot == -1:
        return 0
    score_change = (sqr_foot - 800) / 100
    if sqr_foot < 500 or sqr_foot > 3000:
        score_change = -5
    score_change = min(score_change, 4)
    return score_change

def calc_distance_sc(distance):
    if distance == -1:
        return 0
    score_change = ((8 - distance) * .25) - 2
    return score_change

def calc_price_score_lg(price):
    if price < 2000:
        return -2
    score_change = (3200 - price) / 200
    return score_change

def calc_sqr_foot_score_lg(sqr_foot):
    if sqr_foot == -1:
        return 0
    score_change = (sqr_foot - 800) / 100
    if sqr_foot < 500 or sqr_foot > 3000:
        score_change = -5
    score_change = min(score_change, 4)
    return score_change

def calc_distance_lg(distance):
    if distance == -1:
        return 0
    score_change = ((4 - distance) * .25) - 1
    return score_change

def get_lg_scoring_info():
    score_info = {}
    ## Emmo's work (SA Photonics)
    score_info['location'] = [37.2609611, -121.9611325]
    ## These need to be full matches, not partial
    attr_scores = {"off-street parking": 1,
                   'street parking': -2,
                   "attached garage": 3,
                   "carport": -1,
                   "3br":10,
                   "2br":-4,
                   "1br": -8,
                   "0br": -12,
                   "furnished": -2,
                   "w/d in unit": 2,
                   "apartment": -1,
                   "house": 2,
                   'cottage/cabin': 1,
                   "townhouse": 1,
                   "air conditioning":2,
                   "laundry on site": 1,
                   'laundry in bldg': 2,
                   "ft2": calc_sqr_foot_score_lg,
                   }
    remove_spam_bad = { "desc": ["🆃🅴🆇🆃 ME NUMBER!!!!",
                                 "TEXT YOUR CONTACT NOW",
                                 "TEXT ME NUMBER!!!!",
                                 "Luxury lobby and reception area fully attended",
                                  "💫Pre-installed intrusion alarm"] ,
                        "attrs": ["CENTURY 21 VERDESCHI AND WALSH REALTY.;".lower(),
                                 "CENTURY 21 VERDESCHI AND WALSH REALTY".lower(),
                                 ],
                        "title": ['Rooms for rent']
    }
    score_info['remove'] = remove_spam_bad
    
    # TODO there will be some where they are a subset of another
    # like garage, no garage, 1-car garage, etc, need to handle those!
    # parking garage
    # could have them be part of a group, and group can only be added once
    # would be nice for AC and stuff that would get double counted

    desc_scores = {"converted garage": -10,
                   "no garage": -10,
                   "garage space is not included": -10,
                   "parking garage": -6,
                   "garage": 5,
                   'lots of light ': 2,
                   "Occupancy Limit: 1 People": -5,
                   "Utilities are not included": -2,
                   'All utilities are included': 2,
                   'All utilities included': 2,
                   'Water and Garbage Included': 1,
                   'Coin-op laundry': -1,
                   'street parking only ': -3,
                   'In-Home Washer/Dryer':2,
                   'in-unit washer/dryer': 2,
                   'Dual Pane Windows': 1,
                   'A/C': 1,
                   'Air Conditioning': 1,
                   'Air Conditioner': 1,
                   'Central HVAC': 1,
                   '1 car garage': 3,
                   '1-car garage': 3,
                   'one-car garage': 3,
                   'one car garage': 3,
                   'two-car garage': 5,
                   'two car garage': 5,
                   '2 car garage':5,
                   '2-car garage':5,
                   'One-Car Carport': -2,
                   'garage space used as an extra room': -2,
                   'underground parking garage': -2,
                   'garage log': -2,
                   'coin operated laundry': -1,
                   'coin-operated laundry': -1,
                   '1 person max': -5,
                   '1-person max': -5
                   }
    score_info['desc'] = desc_scores
    title_scores = {"":2,}
    score_info['title'] = title_scores
    score_info['price_func'] = calc_price_score_lg
    score_info['attrs'] = attr_scores
    score_info['distance'] = calc_distance_lg
    return score_info

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
                   "1br": -5,
                   "0br": -6,
                   "furnished": -2,
                   "w/d in unit": 2,
                   "apartment": -1,
                   "house": 2,
                   'cottage/cabin': 1,
                   "townhouse": 1,
                   "air conditioning":2,
                   "laundry on site": 1,
                   'laundry in bldg': 2,
                   "ft2": calc_sqr_foot_score_sc,
                   }
    remove_spam_bad = { "desc": ["🆃🅴🆇🆃 ME NUMBER!!!!",
                                 "TEXT YOUR CONTACT NOW",
                                 "TEXT ME NUMBER!!!!",
                                 "Luxury lobby and reception area fully attended",
                                  "💫Pre-installed intrusion alarm"] ,
                                  # below use the .lower(), it checks against a lower case version
                        "attrs": ["CENTURY 21 VERDESCHI AND WALSH REALTY.;".lower(),
                                 "CENTURY 21 VERDESCHI AND WALSH REALTY".lower(),
                                 "Golden Gate Sotheby's International Realty".lower()],
                        "title": ['Rooms for rent']
    }
    score_info['remove'] = remove_spam_bad
    
    # TODO there will be some where they are a subset of another
    # like garage, no garage, 1-car garage, etc, need to handle those!
    # parking garage
    # could have them be part of a group, and group can only be added once
    # would be nice for AC and stuff that would get double counted

    desc_scores = {"converted garage": -10,
                   "no garage": -10,
                   "garage space is not included": -10,
                   "parking garage": -6,
                   "garage": 5,
                   'lots of light ': 2,
                   "Occupancy Limit: 1 People": -5,
                   "Utilities are not included": -2,
                   'All utilities are included': 2,
                   'All utilities included': 2,
                   'Water and Garbage Included': 1,
                   'Coin-op laundry': -1,
                   'street parking only ': -3,
                   'In-Home Washer/Dryer':2,
                   'in-unit washer/dryer': 2,
                   'Dual Pane Windows': 1,
                   'A/C': 1,
                   'Air Conditioning': 1,
                   'Air Conditioner': 1,
                   'Central HVAC': 1,
                   '1 car garage': 3,
                   '1-car garage': 3,
                   'one-car garage': 3,
                   'one car garage': 3,
                   'two-car garage': 5,
                   'two car garage': 5,
                   '2 car garage':5,
                   '2-car garage':5,
                   'One-Car Carport': -2,
                   'garage space used as an extra room': -2,
                   'underground parking garage': -2,
                   'garage log': -2,
                   'coin operated laundry': -1,
                   'coin-operated laundry': -1,
                   '1 person max': -5,
                   '1-person max': -5
                   }
    score_info['desc'] = desc_scores
    title_scores = {"":2,}
    score_info['title'] = title_scores
    score_info['price_func'] = calc_price_score_sc
    score_info['attrs'] = attr_scores
    score_info['distance'] = calc_distance_sc
    return score_info

def calc_sc_scores(results):
    score_info = get_sc_scoring_info()
    return calc_scores(results, score_info)

## Convert this to the more generic style
def calc_lg_scores(results):
    score_info = get_lg_scoring_info()
    return calc_scores(results, score_info)

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
        score += score_info['price_func'](price)
        res['sqr_foot'] = -1
        for attr in res['attributes']:
            attr_lc = attr.lower()
            if "ft2" in attr_lc:
                sqr_foot = int(attr_lc.split("ft2")[0])
                score += score_info['attrs']['ft2'](sqr_foot)
                res['sqr_foot'] = sqr_foot
            for attr_key in score_info['attrs'].keys():
                if attr_key in attr_lc:
                    if not callable(score_info['attrs'][attr_key]):
                        score += score_info['attrs'][attr_key]
            # spam/remove/bad
            if attr_lc in score_info['remove']['attrs']:
                score = -1000 # remove
        for item in score_info['title']:
            if item.lower() in res['title']:
                score += score_info['title'][item]
        description_lower = res['description'].lower()

        for item in score_info['desc']:
            if item.lower() in description_lower:
                score += score_info['desc'][item]
        ## Handle remove/spam/bad in description
        for item in score_info['remove']['desc']:
            if item.lower() in description_lower:
                score = -1000
        ## Handle remove/spam/bad in description
        for item in score_info['remove']['title']:
            if item.lower() in res['title'].lower():
                score = -1000
        distance = -1
        if 'coord' in res:
            latitude, longitude = map(float, res['coord'].split(';'))
            distance = haversine(center_lat, center_long, latitude, longitude)
            score += score_info['distance'](distance)
        res['distance'] = distance
        res['score'] = score
        if 'address' in res:
            if res['address'] != '':
                if res['address'] in addrs:
                    if score > results[addrs[res['address']]]['score']:
                        rem_idxs.append(addrs[res['address']])
                        addrs[res['address']] = idx
                    else:
                        rem_idxs.append(idx)
                else:
                    addrs[res['address']] = idx
    filtered_list = [results[i] for i in range(len(results)) if i not in rem_idxs and results[i]['score'] > 0]
    unwanted_list = [results[i] for i in range(len(results)) if i in rem_idxs or results[i]['score'] <= 0]

    sorted_data = sorted(filtered_list, key=lambda x: x['score'], reverse=True)
    return sorted_data, unwanted_list
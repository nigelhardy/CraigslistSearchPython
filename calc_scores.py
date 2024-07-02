

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
            if 'off-street parking' in attr:
                score += 1
            if 'attached garage' in attr:
                score += 3
            if '2Br' in attr:
                score += 4
            if '1.5Ba' in attr:
                score += 1
            if '0Br' in attr:
                score -= 4
            if '1Br' in attr:
                pass
            if 'ft2' in attr:
                sqr_foot = int(attr.split("ft2")[0])
                score += (sqr_foot - 600) / 500
                res['sqr_foot'] = sqr_foot
        res['score'] = score

    sorted_data = sorted(results, key=lambda x: x['score'], reverse=True)
    return sorted_data

def calc_lg_scores(results):
    for res in results:
        price = res['price']
        
        score = 0
        if price != -1:
            score += (3300 - price) / 1000
        res['sqr_foot'] = -1
        for attr in res['attributes']:
            if 'off-street parking' in attr:
                score += 1
            if 'attached garage' in attr:
                score += 3
            if '3Br' in attr:
                score += 4
            if '2Ba' in attr:
                score += 1
            if '0Br' in attr:
                score -= 4
            if '1Br' in attr:
                score -= 2.5
            if 'ft2' in attr:
                sqr_foot = int(attr.split("ft2")[0])
                score += (sqr_foot - 600) / 500
                res['sqr_foot'] = sqr_foot
        res['score'] = score

    sorted_data = sorted(results, key=lambda x: x['score'], reverse=True)
    return sorted_data
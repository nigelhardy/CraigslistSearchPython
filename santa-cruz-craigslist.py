import craigslistscraper as cs
import json
import time
import os
import webbrowser
import argparse
import pickle
import smtplib
from Levenshtein import ratio

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from calc_scores import calculate_scores
from results_to_html import results_to_html
## TODO
# send email
# setup to run daily or periodically somehow, remember that we had to fix the library slighty
# - maybe we put up a PR to avoid problems and fix their library
# we have changed the library a bit, so we should fork it and keep our changes, attr for houses wasn't working
# also I want to add getting the location more, so we can see distance

# if we get the location, we can probably use AI to give biking score, grocery, etc
	# <meta name="geo.position" content="36.951950;-121.850095">
	# <meta name="ICBM" content="36.951950, -121.850095">

# NEXT STEP
# keep record of the listings we've already seen and don't send them twice
# might want to have the similarity text feature at somepoint so we dont' see the same ones renewed over and over

# Define the search. Everything is done lazily, and so the html is not
# fetched at this step.
def fetch_new_data(search_type, max_fetches, prev_results):
    results = []
    search = None
    filters = None

    if search_type == "SC":
        search = cs.Search(
            query = "",
            city = "sfbay",
            category = "apa"
        )
        filters = {
            "max_price" : 3300,
            "postal": 95010,
            "search_distance": 10,
        }
    elif search_type == "LG":
        search = cs.Search(
            query = "",
            city = "sfbay",
            category = "apa"
        )
        filters = {
            "max_price": 4000,
            "postal": 95030,
            "search_distance": 5
        }
    old_urls = []
    for res in prev_results:
        old_urls.append(res['url'])

    # Fetch the html from the server. Don't forget to check the status.
    status = search.fetch(params=filters)


    if status != 200:
        raise Exception(f"Unable to fetch search with status <{status}>.")
    print("Number of listings from search: " + str(len(search.ads)))

    count = 0
    for ad in search.ads:
        if max_fetches != -1 and count > max_fetches:
            print("MAX Fetches Reached")
            break
        if ad.url in old_urls:
            print("OLD URL")
            continue
        else:
            print("NEW URL: " + ad.url)
            count += 1
            
        # Fetch additional information about each ad. Check the status again.
        try:
            status = ad.fetch()
            if status != 200:
                print(f"Unable to fetch ad '{ad.title}' with status <{status}>.")
                print(ad.url)
                continue
        except Exception as e:
            print(ad)
            print(e)
            print("Failed to fetch")
            continue

        # There is a to_dict() method for convenience.
        data = ad.to_dict()
        results.append(data)

    return results

def main():
    parser = argparse.ArgumentParser(description='Property List Generator')
    parser.add_argument('--fetch', action='store_true', help='Fetch new data')
    parser.add_argument('--email', action='store_true', help='Send email')
    parser.add_argument('--display', action='store_true', help='Display HTML in browser')
    parser.add_argument('--type', type=str, choices=['SC', 'LG'], default='SC', help='Type of property (SC or LG)')
    parser.add_argument('--max_fetches', type=int, default=-1, help='Max number of listings to parse')

    parser.add_argument('--test-url', type=str, help='URL to test ranking/scoring')
    
    args = parser.parse_args()

    if args.test_url:
        ## for testing the library
        # example url: https://sfbay.craigslist.org/scz/apa/d/santa-cruz-sunny-seabright-studio-by/7762308713.html
        ad = cs.fetch_ad(args.test_url)
        print(ad.attributes)
        return

    results = []
    prev_results = []
    # use old data
    file_path = 'my_dict' + args.type + '.pkl'
    if os.path.isfile(file_path):
        with open(file_path, 'rb') as file:
            prev_results = pickle.load(file)
    if args.fetch:
        results = fetch_new_data(args.type, args.max_fetches, prev_results)
    else: # use old results and show all
        results = prev_results
    sorted_results = calculate_scores(results, args.type)

    no_dups = []
    urls = []
    titles = []
    descs = []
    for res in sorted_results:
        if res['url'] in urls:
            continue
        skip = False
        for good in no_dups:
            if len(res['title']) > 25 and ratio(res['title'], good['title']) > 0.9:
                r = ratio(res['title'], good['title'])
                print("Ratio: " + str(r) + " ",)
                print(res['title'] + " vs " + good['title'])
                skip = True
                break
            if len(res['description']) > 25 and ratio(res['description'], good['description']) > 0.8:
                r = ratio(res['description'], good['description'])
                print("Desc Ratio: " + str(r))
                skip = True
                break
        if not skip:
            no_dups.append(res)
            descs.append(res['description'])
            titles.append(res['title'])
            urls.append(res['url'])
        else:
            print("SKIPPING " + res['title'])
    
    ## TODO add no_dups
    html_content = results_to_html(no_dups)
    no_dups.extend(prev_results)
    if args.fetch:
        with open('my_dict' + args.type + '.pkl', 'wb') as file:
            pickle.dump(no_dups, file)


    if args.email:
        # Set up the email
        message = MIMEMultipart()
        message['From'] = 'your_email@example.com'
        message['To'] = 'recipient@example.com'
        message['Subject'] = 'Item List'

        # Attach the HTML content
        message.attach(MIMEText(html_content, 'html'))

        # Send the email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('your_email@example.com', 'your_password')
            server.send_message(message)

    if args.display:
        # Write the HTML content to a file
        with open('email_preview.html', 'w', encoding='utf-8') as file:
            file.write(html_content)

        # Open the HTML file in the default web browser
        webbrowser.open('email_preview.html')

if __name__ == "__main__":
    main()
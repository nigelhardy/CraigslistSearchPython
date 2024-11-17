import craigslistscraper as cs
import json
import time
import os
from dotenv import load_dotenv
import webbrowser
import argparse
import pickle
import smtplib
from Levenshtein import ratio

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from calc_scores import calculate_scores
from results_to_html import results_to_html

import smtplib
from email.mime.text import MIMEText

# Load environment variables from .env file (optional)
load_dotenv()

# Get credentials from environment variables
sender_email = os.getenv("EMAIL_SENDER_ADDRESS")
receiver_email = os.getenv("EMAIL_RECEIVER_ADDRESS")
app_pass = os.getenv("EMAIL_PASSWORD")

# Ensure the variables are loaded
if not sender_email or not receiver_email or not app_pass:
    raise EnvironmentError("Missing email credentials in environment variables!")

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
def fetch_new_data(search_type, max_fetches, old_urls, wait_ms):
    results = []
    search = None
    filters = None

    if search_type == "SC":
        # lat=36.9677&lon=-121.985&search_distance=9.26
        search = cs.Search(
            query = "",
            city = "sfbay",
            category = "apa"
        )
        filters = {
            "max_price" : 3300,
            "lat": 36.9677,
            "lon": -121.985,
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

    # Fetch the html from the server. Don't forget to check the status.
    status = search.fetch(params=filters)


    if status != 200:
        raise Exception(f"Unable to fetch search with status <{status}>.")
    print("Number of listings from search: " + str(len(search.ads)))
    fails = 0
    count = 0
    for ad in search.ads:
        if max_fetches != -1 and count >= max_fetches or fails > 5:
            print("MAX Fetches or Fails Reached")
            break
        if ad.url in old_urls:
            # print("OLD URL: " + ad.url)
            continue
        else:
            print("NEW URL: " + ad.url)
            count += 1
        if wait_ms > 0:
            time.sleep(wait_ms / 1000.0) 
        # Fetch additional information about each ad. Check the status again.
        try:
            status = ad.fetch()
            if status != 200:
                print(f"Unable to fetch ad '{ad.title}' with status <{status}>.")
                print(ad.url)
                fails += 1
                continue
        except Exception as e:
            print(ad)
            print(e)
            print("Failed to fetch")
            fails += 1
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
    parser.add_argument('--wait_ms', type=int, default=-1, help='Milliseconds to wait between fetches')
    
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
    file_path_unwanted = 'my_unwanted' + args.type + '.pkl'
    old_results_to_skip = []
    if os.path.isfile(file_path_unwanted):
        with open(file_path_unwanted, 'rb') as file:
            old_results_to_skip = pickle.load(file)
    old_urls = []
    for res in prev_results:
        old_urls.append(res['url'])
    for url in old_results_to_skip:
        old_urls.append(url)
    if args.fetch:
        results = fetch_new_data(args.type, args.max_fetches, old_urls, args.wait_ms)
    else: # use old results and show all
        results = prev_results
    sorted_results, unwanted_results = calculate_scores(results, args.type)
    for res in unwanted_results: # avoid any low scoring ones in the future
        old_results_to_skip.append(res['url'])
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
            old_results_to_skip.append(res['url'])
    
    ## TODO add no_dups
    html_content = results_to_html(no_dups)
    num_new_listings = len(no_dups)
    no_dups.extend(prev_results)
    if args.fetch:
        with open('my_dict' + args.type + '.pkl', 'wb') as file:
            pickle.dump(no_dups, file)
        with open('my_unwanted' + args.type + '.pkl', 'wb') as file:
            pickle.dump(old_results_to_skip, file)

    if args.email and num_new_listings > 0:
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "New Apartment Listings!"
        msg.attach(MIMEText(html_content, 'html'))

        # Send the email
        try:
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()  # Secure the connection
                server.login(sender_email, app_pass)
                server.sendmail(sender_email, receiver_email, msg.as_string())
            print("Email sent successfully!")
        except Exception as e:
            print(f"Failed to send email: {e}")
    if args.display:
        # Write the HTML content to a file
        with open('email_preview.html', 'w', encoding='utf-8') as file:
            file.write(html_content)

        # Open the HTML file in the default web browser
        webbrowser.open('email_preview.html')

if __name__ == "__main__":
    main()
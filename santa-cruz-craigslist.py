import craigslistscraper as cs
import json
import time
import webbrowser
import argparse
import pickle
import smtplib
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

# keep record of the listings we've already seen and don't send them twice
# might want to have the similarity text feature at somepoint so we dont' see the same ones renewed over and over

# Define the search. Everything is done lazily, and so the html is not
# fetched at this step.
def fetch_new_data(search_type):
    results = []
    search = None
    filters = None

    if search_type == "SC":
        search = cs.Search(
            query = "garage",
            city = "sfbay",
            category = "apa"
        )
        filters = {
            "max_price" : 3200,
            "postal": 95010,
            "search_distance": 8,
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
    print(len(search.ads))
    count = 0
    for ad in search.ads:
        # if count > 3:
        #     break
        # count += 1
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
    
        # json.dumps is merely for pretty printing.
        # print(json.dumps(data, indent = 4))
    with open('my_dict' + search_type + '.pkl', 'wb') as file:
        pickle.dump(results, file)
    return results

def main():
    parser = argparse.ArgumentParser(description='Property List Generator')
    parser.add_argument('--fetch', action='store_true', help='Fetch new data')
    parser.add_argument('--email', action='store_true', help='Send email')
    parser.add_argument('--display', action='store_true', help='Display HTML in browser')
    parser.add_argument('--type', type=str, choices=['SC', 'LG'], default='SC', help='Type of property (SC or LG)')

    parser.add_argument('--test-url', type=str, help='URL to test ranking/scoring')
    
    args = parser.parse_args()
    results = []
    if args.fetch:
        results = fetch_new_data(args.type)
    else:
        # use old data
        with open('my_dict' + args.type + '.pkl', 'rb') as file:
            results = pickle.load(file)
    sorted_results = calculate_scores(results, args.type)
    html_content = results_to_html(sorted_results)

    if args.test_url:
        ## for testing the library
        # example url: https://sfbay.craigslist.org/scz/apa/d/santa-cruz-sunny-seabright-studio-by/7762308713.html
        ad = cs.fetch_ad(args.test_url)
        print(ad.attributes)
        return  


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
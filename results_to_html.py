

def results_to_html(sorted_results):
    # Create the HTML for the table
    table_html = """
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
    <tr style="background-color: #f2f2f2;">
        <th>Title(link)</th>
        <th>Description</th>
        <th>Score</th>
        <th>Price</th>
        <th>Distance</th>
        <th>Square Footage</th>
    </tr>
    """

    for item in sorted_results:
        table_html += f"""
    <tr>
        <td><strong><a href="{item['url']}" target="_blank">{item['title']}</a></strong></td>
        <td>{item['description']}</td>
        <td align="center">{round(item['score'],1)}</td>
        <td align="right">${item['price']:,}</td>
        <td align="right">{round(item['distance'],1)} mi.</td>
        <td align="right">{item['sqr_foot']:,} sq ft</td>
    </tr>
    """

    table_html += "</table>"

    # Create the full HTML content
    html_content = f"""
    <html>
    <body>
        <h2>Property List</h2>
        <p>Here's a list of properties:</p>
        {table_html}
    </body>
    </html>
    """

    return html_content